"""Bolna posts call results here. Owner: Utkarsh.

Set this URL as the agent's webhook in the Bolna dashboard. For local dev, expose it
with `ngrok http 8000` and use https://<id>.ngrok.app/api/webhook/call-outcome.

An unknown execution id is acknowledged with HTTP 200 and `ok: false` so the
provider does not retry a call we never placed. A shared-secret check is not
wired yet; see the proposed `BOLNA_WEBHOOK_SECRET` setting.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import CallLog, Task, TaskStatus, utcnow
from app.schemas import BolnaWebhook
from app.services.outcomes import apply_outcome, classify

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# Bolna sends intermediate updates too; only the first terminal update moves the task.
TERMINAL_STATUSES = {"completed", "no-answer", "busy", "failed", "canceled", "call-disconnected"}


def _provider_status(status: Optional[str]) -> Optional[str]:
    if status is None:
        return None
    text = status.strip().lower()
    return text or None


@router.post("/call-outcome")
def call_outcome(body: BolnaWebhook, session: Session = Depends(get_session)):
    call = session.exec(select(CallLog).where(CallLog.bolna_call_id == body.id)).first()
    if not call:
        return {"ok": False, "reason": "unknown call id"}

    task = session.get(Task, call.task_id)
    # Already applied. A repeat, or an earlier update that arrives late, must
    # not move the task again or replace the terminal status.
    if call.outcome is not None:
        return {
            "ok": True,
            "duplicate": True,
            "applied": False,
            "outcome": call.outcome,
            "task_status": task.status if task else None,
        }

    status = _provider_status(body.status)
    if status:
        call.status = status
    if body.transcript:
        call.transcript = body.transcript
    if body.summary:
        call.summary = body.summary
    call.updated_at = utcnow()

    applied = False
    if status in TERMINAL_STATUSES and task is not None and task.status == TaskStatus.calling:
        extracted = body.extracted_data or {}
        call.outcome = classify(status, extracted.get("outcome"))
        apply_outcome(session, task, call.outcome, extracted.get("snooze_minutes"))
        applied = True

    session.add(call)
    session.commit()
    return {
        "ok": True,
        "duplicate": False,
        "applied": applied,
        "outcome": call.outcome,
        "task_status": task.status if task else None,
    }
