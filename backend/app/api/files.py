import hashlib
import mimetypes
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile, BadZipFile
from fastapi import APIRouter, BackgroundTasks, Depends, File as Upload, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import limit
from app.core.security import current_user
from app.models import User, File, Chunk, EmbeddingRef, AuditLog
from app.rag.vector import index
from app.services.processing import process_file
from app.workers.tasks import index_file

router = APIRouter(prefix="/files", tags=["files"])
ALLOWED = {".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav", ".m4a", ".mp4", ".mov", ".txt", ".log", ".json", ".jsonl"}
ZIP_MARKERS = {".docx": "word/document.xml", ".pptx": "ppt/presentation.xml", ".xlsx": "xl/workbook.xml"}


def validate(path: Path, ext: str):
    with path.open("rb") as stream: header = stream.read(24)
    if ext == ".pdf" and not header.startswith(b"%PDF-"): raise HTTPException(415, "Invalid PDF")
    if ext in ZIP_MARKERS:
        try:
            with ZipFile(path) as z:
                if ZIP_MARKERS[ext] not in z.namelist(): raise HTTPException(415, "Invalid Office file")
                if sum(info.file_size for info in z.infolist()) > 200 * 1024 * 1024: raise HTTPException(413, "Archive too large")
        except BadZipFile as exc: raise HTTPException(415, "Invalid Office archive") from exc
    if ext == ".png" and not header.startswith(b"\x89PNG\r\n\x1a\n"): raise HTTPException(415, "Invalid PNG")
    if ext in {".jpg", ".jpeg"} and not header.startswith(b"\xff\xd8"): raise HTTPException(415, "Invalid JPEG")
    if ext == ".webp" and not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"): raise HTTPException(415, "Invalid WebP")
    if ext == ".wav" and not (header.startswith(b"RIFF") and header[8:12] == b"WAVE"): raise HTTPException(415, "Invalid WAV")
    if ext in {".mp4", ".mov", ".m4a"} and header[4:8] != b"ftyp": raise HTTPException(415, "Invalid media file")
    if ext == ".mp3" and not (header.startswith(b"ID3") or header[:1] == b"\xff"): raise HTTPException(415, "Invalid MP3")
    if ext in {".txt", ".log", ".csv", ".json", ".jsonl"} and b"\x00" in header: raise HTTPException(415, "Binary content is not valid text")


def owner_file(db: Session, file_id: str, owner_id: str) -> File:
    item = db.scalar(select(File).where(File.id == file_id, File.owner_id == owner_id))
    if not item: raise HTTPException(404, "File not found")
    return item


def dispatch(background: BackgroundTasks, file_id: str, method: str):
    if get_settings().redis_url:
        try: index_file.delay(file_id, method)
        except Exception as exc: raise HTTPException(503, "Processing queue unavailable") from exc
    else:
        background.add_task(process_file, file_id, method)


@router.post("/upload", dependencies=[Depends(limit("upload", 30))], status_code=201)
async def upload(background: BackgroundTasks, file: UploadFile = Upload(...), chunk_method: str = Form("document"), user: User = Depends(current_user), db: Session = Depends(get_db)):
    if chunk_method not in {"fixed", "recursive", "semantic", "document"}: raise HTTPException(422, "Invalid chunk method")
    name = Path(file.filename or "").name[:255]
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED: raise HTTPException(415, "Unsupported file type")
    directory = get_settings().storage_dir / user.id
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{uuid4()}{ext}"
    total = 0; digest = hashlib.sha256()
    try:
        with target.open("wb") as stream:
            while content := await file.read(1024 * 1024):
                total += len(content)
                if total > get_settings().max_upload_mb * 1024 * 1024: raise HTTPException(413, "File exceeds upload limit")
                digest.update(content); stream.write(content)
        if not total: raise HTTPException(422, "Empty file")
        validate(target, ext)
        existing = db.scalar(select(File).where(File.owner_id == user.id, File.sha256 == digest.hexdigest()))
        if existing:
            target.unlink(missing_ok=True)
            return {"id": existing.id, "status": existing.status, "duplicate": True}
        item = File(owner_id=user.id, name=name, mime_type=mimetypes.guess_type(name)[0] or "application/octet-stream", size=total, sha256=digest.hexdigest(), storage_path=str(target.resolve()), tags=ext.lstrip("."))
        db.add(item); db.flush(); db.add(AuditLog(actor_id=user.id, event="upload", target_id=item.id)); db.commit()
        dispatch(background, item.id, chunk_method)
        return {"id": item.id, "status": item.status, "duplicate": False}
    except Exception:
        if not db.scalar(select(File).where(File.storage_path == str(target.resolve()))): target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@router.get("/list")
def list_files(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(File).where(File.owner_id == user.id).order_by(File.created_at.desc())).all()


@router.get("/{file_id}/preview")
def preview(file_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owner_file(db, file_id, user.id)
    return FileResponse(item.storage_path, filename=item.name, media_type=item.mime_type, content_disposition_type="attachment")


@router.post("/{file_id}/process")
def reprocess(file_id: str, background: BackgroundTasks, chunk_method: str = "document", user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owner_file(db, file_id, user.id)
    if chunk_method not in {"fixed", "recursive", "semantic", "document"}: raise HTTPException(422, "Invalid chunk method")
    if item.status == "processing": raise HTTPException(409, "Already processing")
    item.status = "pending"; db.commit()
    dispatch(background, item.id, chunk_method)
    return {"id": item.id, "status": "pending"}


@router.post("/process")
def process_alias(file_id: str, background: BackgroundTasks, chunk_method: str = "document", user: User = Depends(current_user), db: Session = Depends(get_db)):
    return reprocess(file_id, background, chunk_method, user, db)


@router.delete("/{file_id}", status_code=204)
def delete(file_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owner_file(db, file_id, user.id)
    chunks = db.scalars(select(Chunk).where(Chunk.file_id == item.id)).all()
    refs = db.scalars(select(EmbeddingRef).where(EmbeddingRef.chunk_id.in_([c.id for c in chunks]))).all() if chunks else []
    index().remove(refs)
    for ref in refs: db.delete(ref)
    for chunk in chunks: db.delete(chunk)
    db.flush()
    path = Path(item.storage_path)
    db.add(AuditLog(actor_id=user.id, event="delete", target_id=item.id)); db.delete(item); db.commit()
    path.unlink(missing_ok=True)


@router.patch("/{file_id}/tags")
def set_tags(file_id: str, tags: list[str], user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owner_file(db, file_id, user.id)
    if len(tags) > 10 or any(not tag.strip() or len(tag) > 30 or ',' in tag for tag in tags):
        raise HTTPException(422, "Provide up to ten short tags without commas")
    item.tags = ','.join(dict.fromkeys(t.strip().lower() for t in tags))
    db.add(AuditLog(actor_id=user.id, event="tags", target_id=item.id)); db.commit()
    return {"id": item.id, "tags": item.tags}
