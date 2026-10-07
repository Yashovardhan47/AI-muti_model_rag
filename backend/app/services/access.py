"""Source-level read grants and revocation of copied evidence in chat history."""
import json
from pathlib import Path
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.models import File, FileGrant, ChatMessage, ChatSession


def allowed_ids(db: Session, user_id: str) -> set[str]:
    own = set(db.scalars(select(File.id).where(File.owner_id == user_id)).all())
    shared = set(db.scalars(select(FileGrant.file_id).where(FileGrant.user_id == user_id)).all())
    return own | shared


def accessible_file(db: Session, file_id: str, user_id: str) -> File | None:
    grant = select(FileGrant.file_id).where(FileGrant.file_id == File.id, FileGrant.user_id == user_id)
    return db.scalar(select(File).where(File.id == file_id, or_(File.owner_id == user_id, grant.exists())))


def current_citation_state(db: Session, user_id: str, file_ids: set[str]) -> dict[str, tuple[str, bool, bool]]:
    if not file_ids:
        return {}
    available = allowed_ids(db, user_id) & file_ids
    return {file.id: (file.sha256, Path(file.storage_path).is_file(), file.is_current)
            for file in db.scalars(select(File).where(File.id.in_(available)))}


def redact_source_messages(db: Session, file_id: str, viewer_id: str | None = None) -> int:
    stmt = select(ChatMessage).join(ChatSession, ChatMessage.session_id == ChatSession.id).where(
        ChatMessage.role == "assistant", ChatMessage.citations_json.like(f"%{file_id}%"))
    if viewer_id:
        stmt = stmt.where(ChatSession.owner_id == viewer_id)
    count = 0
    for message in db.scalars(stmt):
        citations = json.loads(message.citations_json)
        if not any(citation.get("file_id") == file_id for citation in citations):
            continue
        message.content = "Answer removed because access to a cited source ended. Ask again using available files."
        for citation in citations:
            if citation.get("file_id") == file_id:
                citation["excerpt"] = ""
                citation["available"] = False
                citation["source_state"] = "revoked"
        message.citations_json = json.dumps(citations)
        message.audit_json = json.dumps({"status": "insufficient", "abstained": True, "checks": [],
                                         "warnings": ["A cited source was deleted or access was revoked."]})
        count += 1
    return count
