import csv
import io
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user
from app.models import User, File, ChatSession, ChatMessage, QueryLog

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/export")
def export(format: str = "pdf", user: User = Depends(current_user), db: Session = Depends(get_db)):
    files = db.scalars(select(File).where(File.owner_id == user.id)).all()
    queries = db.scalar(select(func.count(QueryLog.id)).where(QueryLog.owner_id == user.id)) or 0
    if format == "csv":
        out = io.StringIO(); writer = csv.writer(out)
        writer.writerow(["file_id", "name", "status", "type", "size_bytes", "uploaded_at"])
        for f in files:
            safe_name = "'" + f.name if f.name.startswith(("=", "+", "-", "@")) else f.name
            writer.writerow([f.id, safe_name, f.status, f.mime_type, f.size, f.created_at.isoformat()])
        return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=files.csv"})
    if format == "json":
        sessions = db.scalars(select(ChatSession).where(ChatSession.owner_id == user.id)).all()
        ids = [s.id for s in sessions]
        messages = db.scalars(select(ChatMessage).where(ChatMessage.session_id.in_(ids)).order_by(ChatMessage.created_at)).all() if ids else []
        body = json.dumps({"sessions": [{"id": s.id, "title": s.title} for s in sessions], "messages": [{"session_id": m.session_id, "role": m.role, "content": m.content, "citations": json.loads(m.citations_json)} for m in messages]}, ensure_ascii=False)
        return Response(body, media_type="application/json", headers={"Content-Disposition": "attachment; filename=chat-history.json"})
    if format == "pdf":
        from reportlab.pdfgen import canvas
        buffer = io.BytesIO(); pdf = canvas.Canvas(buffer)
        pdf.setTitle("Document Intelligence Summary")
        pdf.setFont("Helvetica-Bold", 18); pdf.drawString(50, 790, "Document Intelligence Summary")
        pdf.setFont("Helvetica", 11); pdf.drawString(50, 758, f"Owner: {user.email}")
        pdf.drawString(50, 738, f"Files: {len(files)}  |  Queries: {queries}  |  Indexed: {sum(f.status == 'ready' for f in files)}")
        y = 700
        for f in files[:35]:
            pdf.drawString(50, y, f"{f.name[:65]}  [{f.status}]"); y -= 18
            if y < 55: pdf.showPage(); y = 790
        pdf.save()
        return Response(buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=summary.pdf"})
    raise HTTPException(422, "Choose pdf, csv, or json")
