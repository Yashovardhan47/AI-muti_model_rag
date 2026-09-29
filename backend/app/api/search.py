from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user
from app.models import User, File
from app.rag.retrieval import retrieve

router = APIRouter(tags=["search"])


@router.get("/search")
def search(q: str = Query(min_length=2, max_length=1000), file_type: str | None = None, tag: str | None = None, date_from: date | None = None, owner: str | None = None, top_k: int = Query(10, ge=1, le=50), user: User = Depends(current_user), db: Session = Depends(get_db)):
    if owner and owner != user.id:
        return []
    target_owner = owner or user.id
    stmt = select(File).where(File.owner_id == target_owner, File.status == "ready")
    if file_type: stmt = stmt.where(File.name.ilike(f"%.{file_type.lstrip('.').lower()}"))
    if tag: stmt = stmt.where(File.tags.ilike(f"%{tag}%"))
    if date_from: stmt = stmt.where(File.created_at >= datetime.combine(date_from, datetime.min.time(), timezone.utc))
    ids = db.scalars(stmt).all()
    if not ids: return []
    return retrieve(db, target_owner, q, top_k, [f.id for f in ids])
