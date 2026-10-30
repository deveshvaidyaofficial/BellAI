"""Bolna posts call results here. Owner: Utkarsh.

Set this URL as the agent's webhook in the Bolna dashboard. For local dev, expose it
with `ngrok http 8000` and use https://<id>.ngrok.app/api/webhook/call-outcome.

An unknown execution id is acknowledged with HTTP 200 and `ok: false` so the
provider does not retry a call we never placed. Webhook authenticity is verified
via shared secret (configured in Bolna dashboard under Add headers as X-Bolna-Webhook-Secret,
X-Api-Key, or Authorization header).
"""

import hmac
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.models import CallLog, Task, TaskStatus, utcnow
from app.schemas import BolnaWebhook
from app.services.outcomes import apply_outcome, classify

router = APIRouter(prefix="/api/webhook", tags=["webhook"])
log = logging.getLogger(__name__)

# Terminal provider statuses that finalize the call
TERMINAL_STATUSES = {"completed", "no-answer", "busy", "failed", "canceled"}


def _provider_status(status: Optional[str]) -> Optional[str]:
    if status is None:
        return None
    text = status.strip().lower()
    return text or None


def _verify_webhook_auth(
    x_bolna_webhook_secret: Optional[str] = Header(None, alias="X-Bolna-Webhook-Secret"),
    x_api_key: Optional[str] = Header(None, alias="X-Api-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> None:
    settings = get_settings()
    secret = settings.bolna_webhook_secret.strip() if settings.bolna_webhook_secret else ""
    if not secret:
        return

    # Check custom secret header
    if x_bolna_webhook_secret and hmac.compare_digest(x_bolna_webhook_secret.strip(), secret):
        return

    # Check X-Api-Key header
    if x_api_key and hmac.compare_digest(x_api_key.strip(), secret):
        return

    # Check Authorization header (Bearer <secret> or raw secret)
    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            if hmac.compare_digest(parts[1], secret):
                return
        elif hmac.compare_digest(authorization.strip(), secret):
            return

    log.warning("Unauthorized webhook request rejected: invalid or missing webhook credentials")
    raise HTTPException(status_code=401, detail="Unauthorized: invalid webhook authentication")


def _is_terminal(status: Optional[str], extracted: Dict[str, Any]) -> bool:
    if not status:
        return False
    if status in TERMINAL_STATUSES:
        return True
    # call-disconnected marks active audio drop, but is terminal if extracted outcome is already provided
    if status == "call-disconnected" and bool(extracted.get("outcome")):
        return True
    return False


@router.post("/call-outcome")
def call_outcome(
    body: BolnaWebhook,
    _: None = Depends(_verify_webhook_auth),
    session: Session = Depends(get_session),
):
    call_id = body.call_id
    if not call_id:
        return {"ok": False, "reason": "missing call id"}

    call = session.exec(select(CallLog).where(CallLog.bolna_call_id == call_id)).first()
    if not call:
        return {"ok": False, "reason": "unknown call id"}

    task = session.get(Task, call.task_id)
    if task is None:
        log.warning("webhook for bolna call %s has no task %s", call_id, call.task_id)

    # Already recorded. A repeat, or an earlier update that arrives late, must
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

    extracted = body.extracted_data if isinstance(body.extracted_data, dict) else {}
    raw_note = extracted.get("note")
    if isinstance(raw_note, str):
        cleaned_note = raw_note.strip()
        if cleaned_note:
            call.extracted_note = cleaned_note

    call.updated_at = utcnow()

    applied = False
    if _is_terminal(status, extracted):
        # Store the outcome even when the task is gone or no longer calling, so a
        # later callback cannot overwrite this call. Only a task still `calling`
        # is moved, and that move stays in Ayush's apply_outcome.
        call.outcome = classify(status, extracted.get("outcome"))
        if task is not None and task.status == TaskStatus.calling:
            apply_outcome(session, task, call.outcome, extracted.get("snooze_minutes"), call=call)
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
