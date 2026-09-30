from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rate_limit import limit
from app.core.security import check_password, current_user, decode, hash_password, token
from app.models import User, Role, RefreshToken, AuditLog
from app.schemas.api import Register, Login, Refresh

router = APIRouter(prefix="/auth", tags=["auth"])


def out(user: User):
    return {"id": user.id, "email": user.email, "role": user.role.name}


def issue(db: Session, user: User):
    access, _, _ = token(user.id, "access", 30)
    refresh, jti, expires = token(user.id, "refresh", 60 * 24 * 14)
    db.add(RefreshToken(id=jti, user_id=user.id, expires_at=expires))
    db.commit()
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer", "user": out(user)}


@router.post("/register", dependencies=[Depends(limit("register", 6))], status_code=201)
def register(body: Register, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    role = db.scalar(select(Role).where(Role.name == "user"))
    user = User(email=email, password_hash=hash_password(body.password), role_id=role.id)
    db.add(user); db.flush(); db.add(AuditLog(actor_id=user.id, event="register")); db.commit(); db.refresh(user)
    return issue(db, user)


@router.post("/login", dependencies=[Depends(limit("login", 10))])
def login(body: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not user or not check_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return issue(db, user)


@router.post("/refresh", dependencies=[Depends(limit("refresh", 30))])
def refresh(body: Refresh, db: Session = Depends(get_db)):
    payload = decode(body.refresh_token, "refresh")
    saved = db.get(RefreshToken, payload["jti"])
    user = db.get(User, payload["sub"])
    if not user or not saved or saved.user_id != user.id or saved.revoked or saved.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(401, "Refresh token revoked")
    saved.revoked = True
    db.flush()
    return issue(db, user)


@router.post("/logout")
def logout(body: Refresh, user: User = Depends(current_user), db: Session = Depends(get_db)):
    payload = decode(body.refresh_token, "refresh")
    saved = db.get(RefreshToken, payload["jti"])
    if saved and saved.user_id == user.id:
        saved.revoked = True; db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return out(user)
