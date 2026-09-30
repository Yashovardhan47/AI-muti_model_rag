"""Qdrant, Chroma, and FAISS indexes. SQL remains the source of truth for ownership."""
import json
from functools import lru_cache
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import Chunk, EmbeddingRef


class VectorIndex:
    def __init__(self):
        self.cfg = get_settings()
        self.backend = self.cfg.vector_backend
        if self.backend == "qdrant":
            from qdrant_client import QdrantClient
            if self.cfg.qdrant_url:
                self.client = QdrantClient(url=self.cfg.qdrant_url)
            else:
                self.cfg.qdrant_path.mkdir(parents=True, exist_ok=True)
                self.client = QdrantClient(path=str(self.cfg.qdrant_path))
        elif self.backend == "chroma":
            import chromadb
            self.cfg.qdrant_path.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(self.cfg.qdrant_path))

    def put(self, ref: EmbeddingRef, vector: list[float], owner_id: str, file_id: str):
        name = f"rag_{ref.index_name}"
        if self.backend == "qdrant":
            from qdrant_client import models
            if not self.client.collection_exists(name):
                self.client.create_collection(name, vectors_config=models.VectorParams(size=len(vector), distance=models.Distance.COSINE))
                self.client.create_payload_index(name, "owner_id", models.PayloadSchemaType.KEYWORD)
                self.client.create_payload_index(name, "file_id", models.PayloadSchemaType.KEYWORD)
            self.client.upsert(name, points=[models.PointStruct(id=ref.vector_id, vector=vector, payload={"owner_id": owner_id, "file_id": file_id, "chunk_id": ref.chunk_id})])
        elif self.backend == "chroma":
            self.client.get_or_create_collection(name).upsert(ids=[ref.vector_id], embeddings=[vector], metadatas=[{"owner_id": owner_id, "file_id": file_id, "chunk_id": ref.chunk_id}])
        # FAISS is rebuilt over SQL vector refs for each tenant at search time.

    def search(self, db: Session, vector: list[float], owner_id: str, kind: str, k: int, file_ids: list[str] | None = None) -> list[tuple[str, float]]:
        name = f"rag_{kind}"
        if self.backend == "qdrant":
            from qdrant_client import models
            if not self.client.collection_exists(name): return []
            must = [models.FieldCondition(key="owner_id", match=models.MatchValue(value=owner_id))]
            if file_ids: must.append(models.FieldCondition(key="file_id", match=models.MatchAny(any=file_ids)))
            points = self.client.query_points(name, query=vector, query_filter=models.Filter(must=must), limit=k).points
            return [(p.payload["chunk_id"], float(p.score)) for p in points]
        if self.backend == "chroma":
            collection = self.client.get_or_create_collection(name)
            where = {"owner_id": owner_id} if not file_ids else {"$and": [{"owner_id": owner_id}, {"file_id": {"$in": file_ids}}]}
            found = collection.query(query_embeddings=[vector], n_results=min(k, max(1, collection.count())), where=where)
            return [(meta["chunk_id"], 1.0 / (1.0 + dist)) for meta, dist in zip(found["metadatas"][0], found["distances"][0])]
        import faiss
        import numpy as np
        rows = db.execute(select(EmbeddingRef, Chunk).join(Chunk, EmbeddingRef.chunk_id == Chunk.id).where(Chunk.owner_id == owner_id, EmbeddingRef.index_name == kind)).all()
        rows = [(ref, chunk) for ref, chunk in rows if not file_ids or chunk.file_id in file_ids]
        if not rows: return []
        matrix = np.asarray([json.loads(ref.vector_json) for ref, _ in rows], dtype="float32")
        if matrix.shape[1] != len(vector): raise ValueError("Embedding dimension changed; reindex files")
        faiss.normalize_L2(matrix)
        index = faiss.IndexFlatIP(len(vector)); index.add(matrix)
        query = np.asarray([vector], dtype="float32"); faiss.normalize_L2(query)
        scores, ids = index.search(query, min(k, len(rows)))
        return [(rows[int(i)][1].id, float(score)) for i, score in zip(ids[0], scores[0]) if i >= 0]

    def remove(self, refs: list[EmbeddingRef]):
        if self.backend == "faiss": return
        by_kind = {}
        for ref in refs: by_kind.setdefault(ref.index_name, []).append(ref.vector_id)
        for kind, ids in by_kind.items():
            name = f"rag_{kind}"
            if self.backend == "qdrant":
                from qdrant_client import models
                if self.client.collection_exists(name): self.client.delete(name, models.PointIdsList(points=ids))
            elif self.backend == "chroma":
                self.client.get_or_create_collection(name).delete(ids=ids)


@lru_cache
def index() -> VectorIndex:
    return VectorIndex()
