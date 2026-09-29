from datetime import datetime, timedelta, timezone
from uuid import uuid4
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def token(user_id: str, kind: str, minutes: int) -> tuple[str, str, datetime]:
    t = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    jti = str(uuid4())
    value = jwt.encode({"sub": user_id, "typ": kind, "jti": jti, "exp": t}, get_settings().jwt_secret, algorithm="HS256")
    return value, jti, t


def decode(value: str, kind: str) -> dict:
    try:
        payload = jwt.decode(value, get_settings().jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub", "jti", "typ"]})
        if payload["typ"] != kind:
            raise ValueError("wrong token type")
        return payload
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = db.get(User, decode(credentials.credentials, "access")["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
