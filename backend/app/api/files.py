import hashlib
import json
import mimetypes
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile, BadZipFile
from fastapi import APIRouter, BackgroundTasks, Depends, File as Upload, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import limit
from app.core.security import current_user
from app.models import User, File, FileGrant, Chunk, EmbeddingRef, AuditLog
from app.rag.vector import index
from app.schemas.api import ShareIn
from app.services.access import accessible_file, allowed_ids, redact_source_messages
from app.services.comparison import compare_files
from app.services.processing import process_file
from app.workers.tasks import index_file

router = APIRouter(prefix="/files", tags=["files"])
ALLOWED = {".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav", ".m4a", ".mp4", ".mov", ".txt", ".log", ".json", ".jsonl"}
ZIP_MARKERS = {".docx": "word/document.xml", ".pptx": "ppt/presentation.xml", ".xlsx": "xl/workbook.xml"}
OCR_LANGUAGES = {"eng", "hin", "tel"}


def file_summary(item: File, user_id: str) -> dict:
    return {"id": item.id, "name": item.name, "mime_type": item.mime_type, "size": item.size,
            "status": item.status, "error": item.error, "tags": item.tags, "created_at": item.created_at,
            "owner_id": item.owner_id, "read_only": item.owner_id != user_id,
            "family_id": item.family_id or item.id, "version": item.version, "is_current": item.is_current,
            "supersedes_id": item.supersedes_id, "ocr_languages": item.ocr_languages}


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
async def upload(background: BackgroundTasks, file: UploadFile = Upload(...), chunk_method: str = Form("document"), replace_file_id: str = Form(""), ocr_languages: str = Form(""), user: User = Depends(current_user), db: Session = Depends(get_db)):
    if chunk_method not in {"fixed", "recursive", "semantic", "document"}: raise HTTPException(422, "Invalid chunk method")
    languages = ocr_languages.strip() or get_settings().ocr_lang
    selected = languages.split("+")
    if not selected or len(selected) != len(set(selected)) or any(language not in OCR_LANGUAGES for language in selected):
        raise HTTPException(422, "OCR languages must be eng, hin, or tel joined with +")
    previous = owner_file(db, replace_file_id, user.id) if replace_file_id else None
    if previous:
        previous = db.scalar(select(File).where(File.id == previous.id).with_for_update())
        if not previous.is_current: raise HTTPException(409, "Replace the current version")
        if previous.status != "ready": raise HTTPException(409, "Wait until the current version is indexed")
        pending = db.scalar(select(File.id).where(File.owner_id == user.id, File.family_id == (previous.family_id or previous.id),
                                                  File.version > previous.version, File.status.in_(["pending", "processing"])))
        if pending: raise HTTPException(409, "A newer version is still indexing")
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
        if existing and (not previous or existing.id == previous.id):
            target.unlink(missing_ok=True)
            return {"id": existing.id, "status": existing.status, "duplicate": True}
        version = ((db.scalar(select(func.max(File.version)).where(File.owner_id == user.id,
                             File.family_id == (previous.family_id or previous.id))) or 0) + 1) if previous else 1
        item = File(owner_id=user.id, name=name, mime_type=mimetypes.guess_type(name)[0] or "application/octet-stream", size=total, sha256=digest.hexdigest(), storage_path=str(target.resolve()), tags=ext.lstrip("."),
                    family_id=(previous.family_id or previous.id) if previous else None,
                    version=version, supersedes_id=previous.id if previous else None,
                    is_current=previous is None, ocr_languages=languages)
        db.add(item); db.flush()
        if not previous: item.family_id = item.id
        if previous:
            for grant in db.scalars(select(FileGrant).where(FileGrant.file_id == previous.id)):
                db.add(FileGrant(file_id=item.id, user_id=grant.user_id, granted_by=grant.granted_by))
        db.add(AuditLog(actor_id=user.id, event="new_version" if previous else "upload", target_id=item.id)); db.commit()
        dispatch(background, item.id, chunk_method)
        return {"id": item.id, "status": item.status, "duplicate": False, "version": item.version, "family_id": item.family_id}
    except Exception:
        if not db.scalar(select(File).where(File.storage_path == str(target.resolve()))): target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@router.get("/list")
def list_files(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(File).where(File.id.in_(allowed_ids(db, user.id))).order_by(File.created_at.desc())).all()
    return [file_summary(item, user.id) for item in items]


@router.get("/{file_id}/preview")
def preview(file_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = accessible_file(db, file_id, user.id)
    if not item: raise HTTPException(404, "File not found")
    return FileResponse(item.storage_path, filename=item.name, media_type=item.mime_type, content_disposition_type="attachment")


@router.get("/compare")
def compare(left_id: str, right_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    left, right = accessible_file(db, left_id, user.id), accessible_file(db, right_id, user.id)
    if not left or not right: raise HTTPException(404, "File not found")
    if left.id == right.id: raise HTTPException(422, "Select two different sources")
    if left.status != "ready" or right.status != "ready": raise HTTPException(409, "Both sources must be indexed")
    return compare_files(db, left, right)


def evidence_chunk(db: Session, file_id: str, chunk_id: str, user_id: str) -> tuple[File, Chunk]:
    item = accessible_file(db, file_id, user_id)
    if not item: raise HTTPException(404, "File not found")
    chunk = db.scalar(select(Chunk).where(Chunk.id == chunk_id, Chunk.file_id == item.id))
    if not chunk: raise HTTPException(404, "Evidence not found")
    if not Path(item.storage_path).is_file(): raise HTTPException(404, "Source file unavailable")
    return item, chunk


@router.get("/{file_id}/evidence/{chunk_id}")
def evidence(file_id: str, chunk_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item, chunk = evidence_chunk(db, file_id, chunk_id, user.id)
    locator = json.loads(chunk.locator_json or "{}")
    kind = locator.get("kind", "text")
    precision = ("time" if kind in {"audio", "video"} and not locator.get("ocr_bbox_pixels") else
                 "row_range" if kind == "spreadsheet" else "ocr_region" if locator.get("ocr_bbox_pixels") else
                 "page_with_text_anchor" if locator.get("anchor") else "page_or_section")
    return {"file_id": item.id, "file_name": item.name, "version": item.version,
            "source_sha256": item.sha256, "chunk_id": chunk.id, "text": chunk.text,
            "location": chunk.location, "locator": locator, "quality": json.loads(chunk.quality_json or "{}"),
            "precision": precision, "can_render": kind in {"pdf", "image", "video"}, "media_type": item.mime_type}


@router.get("/{file_id}/evidence/{chunk_id}/image")
def evidence_image(file_id: str, chunk_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item, chunk = evidence_chunk(db, file_id, chunk_id, user.id)
    locator = json.loads(chunk.locator_json or "{}")
    kind = locator.get("kind")
    if kind == "pdf":
        import fitz
        with fitz.open(item.storage_path) as document:
            page_number = int(locator.get("page", 0))
            if not 1 <= page_number <= len(document): raise HTTPException(422, "Invalid page locator")
            page = document[page_number - 1]
            if page.rect.width * page.rect.height * 2.25 > 25_000_000:
                raise HTTPException(413, "Page too large to render")
            if locator.get("anchor"):
                phrase = " ".join(str(locator["anchor"]).split()[:8])
                for box in page.search_for(phrase)[:10]:
                    page.draw_rect(box, color=(0, .75, .5), width=2, overlay=True)
            elif locator.get("ocr_bbox_pixels") and locator.get("render_scale"):
                coords = locator["ocr_bbox_pixels"]
                scale = float(locator["render_scale"])
                page.draw_rect(fitz.Rect(*[value / scale for value in coords]), color=(0, .75, .5), width=2, overlay=True)
            return Response(page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).tobytes("png"), media_type="image/png")
    if kind == "image":
        from PIL import Image, ImageDraw
        with Image.open(item.storage_path) as source:
            if source.width * source.height > 25_000_000: raise HTTPException(413, "Image too large to render")
            image = source.convert("RGB")
            if locator.get("ocr_bbox_pixels"):
                ImageDraw.Draw(image).rectangle(locator["ocr_bbox_pixels"], outline="#00bf86", width=5)
            buffer = BytesIO(); image.save(buffer, format="PNG")
            return Response(buffer.getvalue(), media_type="image/png")
    if kind == "video":
        import cv2
        cap = cv2.VideoCapture(item.storage_path)
        try:
            cap.set(cv2.CAP_PROP_POS_MSEC, float(locator.get("second", locator.get("start_seconds", 0))) * 1000)
            ok, frame = cap.read()
            if not ok: raise HTTPException(422, "Frame unavailable")
            if frame.shape[0] * frame.shape[1] > 25_000_000: raise HTTPException(413, "Frame too large to render")
            if locator.get("ocr_bbox_pixels"):
                x1, y1, x2, y2 = locator["ocr_bbox_pixels"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 191, 134), 5)
            ok, encoded = cv2.imencode(".png", frame)
            if not ok: raise HTTPException(422, "Frame unavailable")
            return Response(encoded.tobytes(), media_type="image/png")
        finally:
            cap.release()
    raise HTTPException(415, "This evidence has no image preview")


@router.get("/{file_id}/versions")
def versions(file_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = accessible_file(db, file_id, user.id)
    if not item: raise HTTPException(404, "File not found")
    ids = allowed_ids(db, user.id)
    members = db.scalars(select(File).where(File.family_id == (item.family_id or item.id), File.id.in_(ids)).order_by(File.version.desc())).all()
    return [file_summary(member, user.id) for member in members]


@router.get("/{file_id}/access")
def list_access(file_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owner_file(db, file_id, user.id)
    grants = db.execute(select(FileGrant, User.email).join(User, FileGrant.user_id == User.id)
                        .where(FileGrant.file_id == file_id).order_by(User.email)).all()
    return [{"user_id": grant.user_id, "email": email, "created_at": grant.created_at} for grant, email in grants]


@router.post("/{file_id}/access", status_code=201)
def grant_access(file_id: str, body: ShareIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owner_file(db, file_id, user.id)
    recipient = db.scalar(select(User).where(User.email == body.email.lower()))
    if not recipient: raise HTTPException(404, "Registered user not found")
    if recipient.id == user.id: raise HTTPException(422, "Owner already has access")
    members = db.scalars(select(File).where(File.owner_id == user.id, File.family_id == (item.family_id or item.id))).all()
    for member in members:
        existing = db.scalar(select(FileGrant.id).where(FileGrant.file_id == member.id, FileGrant.user_id == recipient.id))
        if not existing: db.add(FileGrant(file_id=member.id, user_id=recipient.id, granted_by=user.id))
    db.add(AuditLog(actor_id=user.id, event="grant_read", target_id=item.id)); db.commit()
    return {"file_id": item.id, "user_id": recipient.id, "scope": "read", "versions": len(members)}


@router.delete("/{file_id}/access/{recipient_id}", status_code=204)
def revoke_access(file_id: str, recipient_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owner_file(db, file_id, user.id)
    members = db.scalars(select(File).where(File.owner_id == user.id, File.family_id == (item.family_id or item.id))).all()
    for member in members:
        grants = db.scalars(select(FileGrant).where(FileGrant.file_id == member.id, FileGrant.user_id == recipient_id)).all()
        for grant in grants: db.delete(grant)
        redact_source_messages(db, member.id, recipient_id)
    db.add(AuditLog(actor_id=user.id, event="revoke_read", target_id=item.id)); db.commit()


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
    redact_source_messages(db, item.id)
    for grant in db.scalars(select(FileGrant).where(FileGrant.file_id == item.id)):
        db.delete(grant)
    if item.is_current and item.family_id:
        prior = db.scalar(select(File).where(File.family_id == item.family_id, File.id != item.id, File.status == "ready")
                          .order_by(File.version.desc()))
        if prior: prior.is_current = True
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
