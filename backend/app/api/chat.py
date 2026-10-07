import json
import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import limit
from app.core.security import current_user
from app.models import User, ChatSession, ChatMessage, QueryLog, UsageMetric
from app.rag.retrieval import retrieve
from app.rag.llm import generate
from app.rag.evidence import safe_answer
from app.schemas.api import QueryIn, QueryOut
from app.services.access import allowed_ids, current_citation_state

router = APIRouter(prefix="/chat", tags=["chat"])


def save_turn(db: Session, session: ChatSession, user: User, body: QueryIn, hits, answer: str, audit: dict, start: float):
    db.add(ChatMessage(session_id=session.id, role="user", content=body.question))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=answer,
                       citations_json=json.dumps([hit.model_dump() for hit in hits]), audit_json=json.dumps(audit)))
    db.add(QueryLog(owner_id=user.id, query_type=body.query_type, retrieval_count=len(hits), latency_ms=int((time.monotonic()-start)*1000)))
    db.add(UsageMetric(owner_id=user.id, metric="queries", value=1))
    db.add(UsageMetric(owner_id=user.id, metric="estimated_tokens", value=(len(body.question)+len(answer)+sum(len(h.excerpt) for h in hits))//4))
    db.commit()


def response_payload(session: ChatSession, hits, answer: str, audit: dict) -> dict:
    return {"session_id": session.id, "answer": answer, "citations": [hit.model_dump() for hit in hits],
            "grounded": bool(hits) and not audit["abstained"], "confidence": "not_calibrated", "audit": audit}


@router.post("/query", response_model=QueryOut, dependencies=[Depends(limit("chat", 30))])
def query(body: QueryIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    start = time.monotonic()
    if body.file_ids:
        if not set(body.file_ids).issubset(allowed_ids(db, user.id)): raise HTTPException(404, "File not found")
    if body.session_id:
        session = db.scalar(select(ChatSession).where(ChatSession.id == body.session_id, ChatSession.owner_id == user.id))
        if not session: raise HTTPException(404, "Conversation not found")
    else:
        session = ChatSession(owner_id=user.id, title=body.question[:100])
        db.add(session); db.flush()
    previous = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.desc()).limit(6)).all()
    history = [{"role": m.role, "content": m.content} for m in reversed(previous)]
    hits = retrieve(db, user.id, body.question, body.top_k, body.file_ids)
    try: answer = generate(body.question, hits, body.query_type, history, body.response_language)
    except Exception as exc: raise HTTPException(503, f"Answer provider unavailable: {type(exc).__name__}") from exc
    answer, audit = safe_answer(answer, hits, extractive=get_settings().llm_provider == "extractive")
    if get_settings().llm_provider == "extractive" and body.response_language in {"hi", "te"}:
        audit["warnings"].append("Extractive mode quotes the source language; select an LLM to request translation.")
    save_turn(db, session, user, body, hits, answer, audit, start)
    return QueryOut.model_validate(response_payload(session, hits, answer, audit))


@router.get("/history")
def history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    sessions = db.scalars(select(ChatSession).where(ChatSession.owner_id == user.id).order_by(ChatSession.created_at.desc())).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]


@router.get("/history/{session_id}")
def messages(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(ChatSession).where(ChatSession.id == session_id, ChatSession.owner_id == user.id))
    if not session: raise HTTPException(404, "Conversation not found")
    entries = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at)).all()
    citations_by_message = [json.loads(m.citations_json) for m in entries]
    ids = {c["file_id"] for group in citations_by_message for c in group}
    current = current_citation_state(db, user.id, ids)
    result = []
    for message, citations in zip(entries, citations_by_message):
        for citation in citations:
            digest = citation.get("source_sha256")
            record = current.get(citation["file_id"])
            citation["available"] = bool(record and record[1] and (not digest or record[0] == digest))
            citation["source_state"] = ("revoked_or_removed" if not record or not record[1] else
                                        "changed" if digest and record[0] != digest else
                                        "superseded" if not record[2] else "current")
        result.append({"id": message.id, "role": message.role, "content": message.content, "citations": citations,
                       "audit": json.loads(message.audit_json or "{}"), "created_at": message.created_at})
    return result


@router.post("/query/stream", dependencies=[Depends(limit("chat-stream", 30))])
def stream_query(body: QueryIn, user: User = Depends(current_user)):
    """Buffer provider output for audit, then stream only the approved answer."""
    from fastapi.responses import StreamingResponse
    from app.core.database import SessionLocal
    from app.rag.llm import generate_stream

    def event(name: str, payload: dict) -> str:
        return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def produce():
        start = time.monotonic()
        with SessionLocal() as db:
            try:
                if body.file_ids:
                    if not set(body.file_ids).issubset(allowed_ids(db, user.id)): raise ValueError("File not found")
                if body.session_id:
                    session = db.scalar(select(ChatSession).where(ChatSession.id == body.session_id, ChatSession.owner_id == user.id))
                    if not session: raise ValueError("Conversation not found")
                else:
                    session = ChatSession(owner_id=user.id, title=body.question[:100]); db.add(session); db.flush()
                previous = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.desc()).limit(6)).all()
                history = [{"role": m.role, "content": m.content} for m in reversed(previous)]
                hits = retrieve(db, user.id, body.question, body.top_k, body.file_ids)
                yield event("progress", {"stage": "Reviewing retrieved evidence"})
                draft = "".join(generate_stream(body.question, hits, body.query_type, history, body.response_language))
                answer, audit = safe_answer(draft, hits, extractive=get_settings().llm_provider == "extractive")
                if get_settings().llm_provider == "extractive" and body.response_language in {"hi", "te"}:
                    audit["warnings"].append("Extractive mode quotes the source language; select an LLM to request translation.")
                save_turn(db, session, user, body, hits, answer, audit, start)
                yield event("progress", {"stage": "Evidence audit complete"})
                for offset in range(0, len(answer), 120):
                    yield event("delta", {"text": answer[offset:offset+120]})
                yield event("final", response_payload(session, hits, answer, audit))
            except Exception as exc:
                db.rollback()
                yield event("error", {"detail": f"Answer could not be completed: {type(exc).__name__}"})
    return StreamingResponse(produce(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
