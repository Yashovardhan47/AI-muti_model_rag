"""Repair the search index from committed SQL refs and queue interrupted files.

SQL is authoritative: vector writes may precede a failed SQL transaction, so
query results are always joined back to accessible SQL chunks.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Chunk, EmbeddingRef, File
from app.rag.vector import index


def reconcile(stale_after_minutes: int = 120) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)
    summary = {"vector_refs_replayed": 0, "queued_files": [], "missing_sources": [], "invalid_refs": []}
    with SessionLocal() as db:
        for file in db.scalars(select(File).where(File.status.in_(["ready", "pending", "processing"]))):
            if not Path(file.storage_path).is_file():
                file.status = "failed"
                file.error = "Source file missing; restore it from backup before retrying"
                file.processing_started_at = None
                summary["missing_sources"].append(file.id)
                if file.is_current:
                    prior = db.scalar(select(File).where(File.family_id == file.family_id, File.id != file.id,
                                                         File.status == "ready").order_by(File.version.desc()))
                    if prior:
                        file.is_current = False
                        prior.is_current = True
                continue
            started = file.processing_started_at or file.created_at
            if started and started.tzinfo is None: started = started.replace(tzinfo=timezone.utc)
            if file.status in {"pending", "processing"} and started and started < cutoff:
                file.status = "pending"
                file.processing_started_at = None
                summary["queued_files"].append(file.id)
            elif file.status == "ready":
                refs = db.execute(select(EmbeddingRef, Chunk).join(Chunk, EmbeddingRef.chunk_id == Chunk.id)
                                  .where(Chunk.file_id == file.id)).all()
                if not refs:
                    file.status = "pending"
                    summary["queued_files"].append(file.id)
                else:
                    for ref, chunk in refs:
                        try:
                            index().put(ref, json.loads(ref.vector_json), chunk.owner_id, file.id)
                            summary["vector_refs_replayed"] += 1
                        except (ValueError, TypeError) as exc:
                            summary["invalid_refs"].append({"file_id": file.id, "ref_id": ref.id, "error": str(exc)[:100]})
        db.commit()
    return summary
