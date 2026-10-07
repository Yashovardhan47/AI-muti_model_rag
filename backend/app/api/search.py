from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user
from app.models import User, File
from app.rag.retrieval import retrieve
from app.services.access import allowed_ids

router = APIRouter(tags=["search"])


@router.get("/search")
def search(q: str = Query(min_length=2, max_length=1000), file_type: str | None = None, tag: str | None = None, date_from: date | None = None, owner: str | None = None, include_versions: bool = False, top_k: int = Query(10, ge=1, le=50), user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(File).where(File.id.in_(allowed_ids(db, user.id)), File.status == "ready")
    if not include_versions: stmt = stmt.where(File.is_current.is_(True))
    if owner: stmt = stmt.where(File.owner_id == owner)
    if file_type: stmt = stmt.where(File.name.ilike(f"%.{file_type.lstrip('.').lower()}"))
    if tag: stmt = stmt.where(File.tags.ilike(f"%{tag}%"))
    if date_from: stmt = stmt.where(File.created_at >= datetime.combine(date_from, datetime.min.time(), timezone.utc))
    ids = db.scalars(stmt).all()
    if not ids: return []
    return retrieve(db, user.id, q, top_k, [f.id for f in ids])
