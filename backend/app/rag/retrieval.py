"""Hybrid candidate generation, optional cross-encoder, and explicit source citations."""
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from rank_bm25 import BM25Okapi
from app.core.config import get_settings
from app.models import Chunk, File
from app.rag.embeddings import embedder, clip_vectors
from app.rag.vector import index
from app.schemas.api import Citation, SearchHit


def retrieve(db: Session, owner_id: str, question: str, k: int = 6, file_ids: list[str] | None = None, kind: str | None = None) -> list[SearchHit]:
    stmt = select(Chunk, File).join(File, Chunk.file_id == File.id).where(Chunk.owner_id == owner_id, File.status == "ready")
    if file_ids: stmt = stmt.where(File.id.in_(file_ids))
    if kind: stmt = stmt.where(Chunk.modality == kind)
    rows = db.execute(stmt).all()
    if not rows: return []
    tokens = lambda x: re.findall(r"\w+", x.lower())
    bm = BM25Okapi([tokens(chunk.text) or [""] for chunk, _ in rows])
    lexical = bm.get_scores(tokens(question))
    bm_rank = sorted(range(len(rows)), key=lambda i: lexical[i], reverse=True)[:k*3]
    candidates: dict[str, float] = {rows[i][0].id: 0.35 / (60 + rank + 1) for rank, i in enumerate(bm_rank)}
    dense_scores: dict[str, float] = {}
    vector = embedder().embed([question], query=True)[0]
    for rank, (chunk_id, score) in enumerate(index().search(db, vector, owner_id, "text", k*3, file_ids)):
        candidates[chunk_id] = candidates.get(chunk_id, 0.0) + 0.65 / (60 + rank + 1)
        dense_scores[chunk_id] = score
    if get_settings().enable_clip:
        for rank, (chunk_id, score) in enumerate(index().search(db, clip_vectors(text=question), owner_id, "image", k, file_ids)):
            candidates[chunk_id] = candidates.get(chunk_id, 0.0) + 0.5 / (60 + rank + 1)
            dense_scores[chunk_id] = score
    matches = [(chunk, file, candidates[chunk.id]) for chunk, file in rows if chunk.id in candidates]
    matches.sort(key=lambda x: x[2], reverse=True)
    if get_settings().enable_reranker and matches:
        from sentence_transformers import CrossEncoder
        if not hasattr(retrieve, "reranker"):
            retrieve.reranker = CrossEncoder(get_settings().rerank_model)
        scores = retrieve.reranker.predict([(question, chunk.text[:2000]) for chunk, _, _ in matches[:k*3]])
        matches = sorted([(c, f, float(score)) for (c, f, _), score in zip(matches[:k*3], scores)], key=lambda x: x[2], reverse=True)
    return [SearchHit(number=i+1, file_id=f.id, file_name=f.name, chunk_id=c.id, location=c.location, excerpt=c.text[:1200], score=round(float(dense_scores.get(c.id, score)), 3), modality=c.modality) for i, (c, f, score) in enumerate(matches[:k])]
