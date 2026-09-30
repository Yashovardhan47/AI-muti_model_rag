"""Idempotent-ish per-file indexing with SQL and vector cleanup on retries."""
import json
import logging
from pathlib import Path
from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import File, Chunk, EmbeddingRef, UsageMetric
from app.rag.chunking import split
from app.rag.embeddings import embedder, clip_vectors
from app.rag.vector import index
from app.services.extract import extract

log = logging.getLogger(__name__)


def process_file(file_id: str, chunk_method: str = "document") -> None:
    with SessionLocal() as db:
        file = db.get(File, file_id)
        if not file: return
        file.status = "processing"; file.error = None; db.commit()
        try:
            old = db.scalars(select(Chunk).where(Chunk.file_id == file.id)).all()
            refs = db.scalars(select(EmbeddingRef).where(EmbeddingRef.chunk_id.in_([x.id for x in old]))).all() if old else []
            index().remove(refs)
            for ref in refs: db.delete(ref)
            for chunk in old: db.delete(chunk)
            db.commit()
            segments = extract(Path(file.storage_path), Path(file.name).suffix.lower())
            parts = split(segments, method=chunk_method, embedder=embedder() if chunk_method == "semantic" else None)
            if not parts: raise ValueError("No extractable content; check OCR or file format")
            for ordinal, part in enumerate(parts):
                chunk = Chunk(file_id=file.id, owner_id=file.owner_id, ordinal=ordinal, text=part.text[:20000], location=part.location[:120], modality=part.modality)
                db.add(chunk); db.flush()
                vector = embedder().embed([chunk.text])[0]
                ref = EmbeddingRef(chunk_id=chunk.id, provider=get_settings().embedding_provider, index_name="text", vector_id=chunk.id, vector_json=json.dumps(vector))
                db.add(ref)
                index().put(ref, vector, file.owner_id, file.id)
                if part.image and get_settings().enable_clip:
                    image_vec = clip_vectors(image=part.image)
                    image_ref = EmbeddingRef(chunk_id=chunk.id, provider="clip", index_name="image", vector_id=__import__("uuid").uuid4().__str__(), vector_json=json.dumps(image_vec))
                    db.add(image_ref); index().put(image_ref, image_vec, file.owner_id, file.id)
            file.status = "ready"
            db.add(UsageMetric(owner_id=file.owner_id, metric="chunks_indexed", value=len(parts)))
            db.commit()
        except Exception as exc:
            db.rollback()
            file = db.get(File, file_id)
            if file:
                file.status = "failed"; file.error = str(exc)[:500]; db.commit()
            log.exception("index failed for file %s", file_id)
            raise
