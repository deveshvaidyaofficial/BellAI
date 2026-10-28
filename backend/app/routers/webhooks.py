"""Bolna posts call results here. Owner: Utkarsh.

Set this URL as the agent's webhook in the Bolna dashboard. For local dev, expose it
with `ngrok http 8000` and use https://<id>.ngrok.app/api/webhook/call-outcome.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import CallLog, Task, TaskStatus, utcnow
from app.schemas import BolnaWebhook
from app.services.outcomes import apply_outcome, classify

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# Bolna sends intermediate updates too; only act once the call is over.
TERMINAL_STATUSES = {"completed", "no-answer", "busy", "failed", "canceled", "call-disconnected"}


@router.post("/call-outcome")
def call_outcome(body: BolnaWebhook, session: Session = Depends(get_session)):
    call = session.exec(select(CallLog).where(CallLog.bolna_call_id == body.id)).first()
    if not call:
        return {"ok": False, "reason": "unknown call id"}

    call.status = body.status or call.status
    call.transcript = body.transcript or call.transcript
    call.summary = body.summary or call.summary
    call.updated_at = utcnow()

    task = session.get(Task, call.task_id)
    # Guard against duplicate deliveries: only the first terminal update moves the task.
    if body.status in TERMINAL_STATUSES and call.outcome is None and task.status == TaskStatus.calling:
        extracted = body.extracted_data or {}
        call.outcome = classify(body.status, extracted.get("outcome"))
        apply_outcome(session, task, call.outcome, extracted.get("snooze_minutes"))

    session.add(call)
    session.commit()
    return {"ok": True, "outcome": call.outcome, "task_status": task.status}
