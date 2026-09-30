from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import admin_user, current_user
from app.models import User, File, QueryLog, UsageMetric, AuditLog, Role

router = APIRouter(tags=["analytics"])


@router.get("/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    files = db.scalars(select(File).where(File.owner_id == user.id)).all()
    queries = db.scalar(select(func.count(QueryLog.id)).where(QueryLog.owner_id == user.id)) or 0
    estimated_tokens = db.scalar(select(func.sum(UsageMetric.value)).where(UsageMetric.owner_id == user.id, UsageMetric.metric == "estimated_tokens")) or 0
    types = {}
    for f in files:
        suffix = f.name.rsplit(".", 1)[-1].lower()
        types[suffix] = types.get(suffix, 0) + 1
    return {"files": len(files), "ready": sum(f.status == "ready" for f in files), "queries": queries, "estimated_tokens": estimated_tokens, "file_types": types, "recent": [{"name": f.name, "status": f.status, "created_at": f.created_at} for f in sorted(files, key=lambda x: x.created_at, reverse=True)[:5]]}


@router.get("/admin/users")
def users(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    entries = db.scalars(select(User).order_by(User.created_at.desc()).limit(200)).all()
    return [{"id": u.id, "email": u.email, "role": u.role.name, "created_at": u.created_at} for u in entries]


@router.patch("/admin/users/{user_id}/role")
def role(user_id: str, role_name: str, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    if role_name not in {"admin", "user"}: raise HTTPException(422, "Invalid role")
    target = db.get(User, user_id)
    if not target: raise HTTPException(404, "User not found")
    if target.id == admin.id and role_name != "admin": raise HTTPException(409, "Cannot demote your own admin account")
    target.role_id = db.scalar(select(Role.id).where(Role.name == role_name))
    db.add(AuditLog(actor_id=admin.id, event=f"role:{role_name}", target_id=user_id)); db.commit()
    return {"id": target.id, "role": role_name}


@router.get("/admin/analytics")
def analytics(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    return {"users": db.scalar(select(func.count(User.id))) or 0,
            "uploads": db.scalar(select(func.count(File.id))) or 0,
            "queries": db.scalar(select(func.count(QueryLog.id))) or 0,
            "indexed_chunks": db.scalar(select(func.sum(UsageMetric.value)).where(UsageMetric.metric == "chunks_indexed")) or 0,
            "estimated_tokens": db.scalar(select(func.sum(UsageMetric.value)).where(UsageMetric.metric == "estimated_tokens")) or 0,
            "recent_errors": [{"file_id": f.id, "error": f.error, "status": f.status} for f in db.scalars(select(File).where(File.status == "failed").limit(20))],
            "audit": [{"event": a.event, "target_id": a.target_id, "created_at": a.created_at} for a in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20))]}
