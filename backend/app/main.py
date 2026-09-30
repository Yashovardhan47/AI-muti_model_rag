from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.logging import configure_logging
from app.models import Role, User
from app.api import auth, files, chat, search, admin, reports

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    if cfg.app_env == "production" and (cfg.jwt_secret == "development-only-change-me-immediately-123" or cfg.jwt_secret.startswith("replace-with-")):
        raise RuntimeError("Set a unique JWT_SECRET in production")
    with SessionLocal() as db:
        for role in ("admin", "user"):
            if not db.scalar(select(Role).where(Role.name == role)):
                db.add(Role(name=role))
        db.commit()
        if cfg.admin_email and cfg.admin_password:
            if len(cfg.admin_password) < 12: raise RuntimeError("ADMIN_PASSWORD must contain at least 12 characters")
            if not db.scalar(select(User).where(User.email == cfg.admin_email.lower())):
                db.add(User(email=cfg.admin_email.lower(), password_hash=hash_password(cfg.admin_password), role_id=db.scalar(select(Role.id).where(Role.name == "admin"))))
                db.commit()
    yield


app = FastAPI(title="Enterprise Multi-Modal Document Intelligence", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in get_settings().cors_origins.split(",") if x.strip()], allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])
for router in (auth.router, files.router, chat.router, search.router, admin.router, reports.router):
    app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    from fastapi import HTTPException
    from app.rag.vector import index
    try:
        with SessionLocal() as db: db.execute(text("SELECT 1"))
        cfg = get_settings()
        if cfg.redis_url:
            import redis
            redis.Redis.from_url(cfg.redis_url, socket_timeout=2).ping()
        if cfg.vector_backend == "qdrant": index().client.get_collections()
        elif cfg.vector_backend == "chroma": index().client.heartbeat()
        return {"status": "ready"}
    except Exception as exc:
        raise HTTPException(503, "Dependency unavailable") from exc
