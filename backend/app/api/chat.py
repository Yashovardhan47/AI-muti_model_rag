import json
import re
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rate_limit import limit
from app.core.security import current_user
from app.models import User, File, ChatSession, ChatMessage, QueryLog, UsageMetric
from app.rag.retrieval import retrieve
from app.rag.llm import generate
from app.schemas.api import QueryIn, QueryOut

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/query", response_model=QueryOut, dependencies=[Depends(limit("chat", 30))])
def query(body: QueryIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    start = time.monotonic()
    if body.file_ids:
        ids = set(db.scalars(select(File.id).where(File.owner_id == user.id, File.id.in_(body.file_ids))).all())
        if ids != set(body.file_ids): raise HTTPException(404, "File not found")
    if body.session_id:
        session = db.scalar(select(ChatSession).where(ChatSession.id == body.session_id, ChatSession.owner_id == user.id))
        if not session: raise HTTPException(404, "Conversation not found")
    else:
        session = ChatSession(owner_id=user.id, title=body.question[:100])
        db.add(session); db.flush()
    previous = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.desc()).limit(6)).all()
    history = [{"role": m.role, "content": m.content} for m in reversed(previous)]
    hits = retrieve(db, user.id, body.question, body.top_k, body.file_ids)
    try: answer = generate(body.question, hits, body.query_type, history)
    except Exception as exc: raise HTTPException(503, f"Answer provider unavailable: {type(exc).__name__}") from exc
    valid = {h.number for h in hits}
    used = {int(x) for x in re.findall(r"\[(\d+)\]", answer)}
    if hits and (not used or not used.issubset(valid)):
        answer = "I cannot verify a grounded answer from the selected sources. Review these passages:\n\n" + "\n\n".join(f"[{h.number}] {h.file_name} ({h.location}): {h.excerpt[:300]}" for h in hits[:3])
    confidence = "none" if not hits else "high" if len(hits) > 2 and hits[0].score > 0.65 else "medium" if hits[0].score > 0.35 else "low"
    db.add(ChatMessage(session_id=session.id, role="user", content=body.question))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=answer, citations_json=json.dumps([h.model_dump() for h in hits])))
    db.add(QueryLog(owner_id=user.id, query_type=body.query_type, retrieval_count=len(hits), latency_ms=int((time.monotonic()-start)*1000)))
    db.add(UsageMetric(owner_id=user.id, metric="queries", value=1))
    db.add(UsageMetric(owner_id=user.id, metric="estimated_tokens", value=(len(body.question) + len(answer) + sum(len(h.excerpt) for h in hits)) // 4)); db.commit()
    return QueryOut(session_id=session.id, answer=answer, citations=hits, confidence=confidence, grounded=bool(hits))


@router.get("/history")
def history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    sessions = db.scalars(select(ChatSession).where(ChatSession.owner_id == user.id).order_by(ChatSession.created_at.desc())).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]


@router.get("/history/{session_id}")
def messages(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(ChatSession).where(ChatSession.id == session_id, ChatSession.owner_id == user.id))
    if not session: raise HTTPException(404, "Conversation not found")
    entries = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at)).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "citations": json.loads(m.citations_json), "created_at": m.created_at} for m in entries]


@router.post("/query/stream", dependencies=[Depends(limit("chat-stream", 30))])
def stream_query(body: QueryIn, user: User = Depends(current_user)):
    """SSE delta events followed by an authoritative final event with citations."""
    from fastapi.responses import StreamingResponse
    from app.core.database import SessionLocal
    from app.rag.llm import generate_stream
    from app.models import File

    def event(name: str, payload: dict) -> str:
        return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def produce():
        start = time.monotonic()
        with SessionLocal() as db:
            try:
                if body.file_ids:
                    ids = set(db.scalars(select(File.id).where(File.owner_id == user.id, File.id.in_(body.file_ids))).all())
                    if ids != set(body.file_ids): raise ValueError("File not found")
                if body.session_id:
                    session = db.scalar(select(ChatSession).where(ChatSession.id == body.session_id, ChatSession.owner_id == user.id))
                    if not session: raise ValueError("Conversation not found")
                else:
                    session = ChatSession(owner_id=user.id, title=body.question[:100]); db.add(session); db.flush()
                previous = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.desc()).limit(6)).all()
                history = [{"role": m.role, "content": m.content} for m in reversed(previous)]
                hits = retrieve(db, user.id, body.question, body.top_k, body.file_ids)
                parts = []
                for delta in generate_stream(body.question, hits, body.query_type, history):
                    parts.append(delta)
                    yield event("delta", {"text": delta})
                answer = "".join(parts)
                used = {int(x) for x in re.findall(r"\[(\d+)\]", answer)}
                if hits and (not used or not used.issubset({h.number for h in hits})):
                    answer = "I cannot verify a grounded answer from these sources. Review the cited passages:\n\n" + "\n\n".join(f"[{h.number}] {h.file_name} ({h.location}): {h.excerpt[:300]}" for h in hits[:3])
                db.add(ChatMessage(session_id=session.id, role="user", content=body.question))
                db.add(ChatMessage(session_id=session.id, role="assistant", content=answer, citations_json=json.dumps([h.model_dump() for h in hits])))
                db.add(QueryLog(owner_id=user.id, query_type=body.query_type, retrieval_count=len(hits), latency_ms=int((time.monotonic()-start)*1000)))
                db.add(UsageMetric(owner_id=user.id, metric="queries", value=1))
                db.add(UsageMetric(owner_id=user.id, metric="estimated_tokens", value=(len(body.question)+len(answer)+sum(len(h.excerpt) for h in hits))//4))
                db.commit()
                yield event("final", {"session_id": session.id, "answer": answer, "citations": [h.model_dump() for h in hits], "grounded": bool(hits), "confidence": "not_calibrated"})
            except Exception as exc:
                db.rollback()
                yield event("error", {"detail": f"Answer could not be completed: {type(exc).__name__}"})
    return StreamingResponse(produce(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
