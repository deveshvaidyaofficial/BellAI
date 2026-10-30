"""Outbound calls via Bolna. Owner: Devesh.

Ayush calls `trigger_call` when a reminder is authorized. This module returns
Bolna's execution id, or raises `BolnaError` on timeout, auth failure, a
rejected request, or a malformed response. `BOLNA_MOCK=true` returns a fake id.

Docs: https://docs.bolna.ai — POST /call starts an outbound call for an agent.
With BOLNA_MOCK=true no request is sent; a fake call id is returned.
"""

import logging
import uuid
from typing import Any, Dict

import httpx

from app.config import get_settings
from app.models import Elder, Task
from app.services.phones import normalize_phone

log = logging.getLogger(__name__)


class BolnaError(Exception):
    pass


def build_user_data(elder: Elder, task: Task) -> Dict[str, Any]:
    """Variables injected into the agent prompt ({elder_name}, {task_title}, ...)."""
    return {
        "elder_name": elder.name,
        "language": elder.language,
        "task_type": task.type.value,
        "task_title": task.title,
        "task_details": task.details or "",
        "task_id": task.id,
    }


def trigger_call(elder: Elder, task: Task) -> str:
    """Start a call and return Bolna's call/execution id."""
    settings = get_settings()

    if settings.bolna_mock:
        call_id = f"mock-{uuid.uuid4().hex[:12]}"
        log.info("[mock] calling %s for task %s -> %s", elder.phone, task.id, call_id)
        return call_id

    # Validate live configuration
    if not settings.bolna_api_key or not settings.bolna_api_key.strip():
        raise BolnaError("Bolna API key is not configured for live calls")
    if not settings.bolna_agent_id or not settings.bolna_agent_id.strip():
        raise BolnaError("Bolna agent ID is not configured for live calls")

    # Validate recipient phone
    try:
        recipient_phone = normalize_phone(elder.phone)
    except (ValueError, TypeError) as exc:
        raise BolnaError(f"Invalid recipient phone for elder {elder.id}: {exc}") from exc

    payload: Dict[str, Any] = {
        "agent_id": settings.bolna_agent_id.strip(),
        "recipient_phone_number": recipient_phone,
        "user_data": build_user_data(elder, task),
    }
    if settings.bolna_from_phone_number and settings.bolna_from_phone_number.strip():
        payload["from_phone_number"] = settings.bolna_from_phone_number.strip()

    timeout_seconds = max(5, settings.bolna_timeout_seconds)
    endpoint = f"{settings.bolna_base_url.rstrip('/')}/call"

    try:
        resp = httpx.post(
            endpoint,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.bolna_api_key.strip()}",
                "Content-Type": "application/json",
            },
            timeout=timeout_seconds,
        )
        resp.raise_for_status()
    except httpx.TimeoutException as exc:
        log.warning("Bolna outbound call request timed out for task %s", task.id)
        raise BolnaError("Bolna outbound call request timed out") from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        log.error("Bolna call initiation rejected with HTTP status %s for task %s", status_code, task.id)
        raise BolnaError(f"Bolna API rejected call request with status {status_code}") from exc
    except httpx.RequestError as exc:
        log.error("Network error while connecting to Bolna API for task %s", task.id)
        raise BolnaError("Failed to connect to Bolna API") from exc
    except Exception as exc:
        log.exception("Unexpected error while placing Bolna call for task %s", task.id)
        raise BolnaError("Unexpected failure initiating Bolna call") from exc

    try:
        data = resp.json()
    except Exception as exc:
        log.error("Bolna response could not be parsed as JSON for task %s", task.id)
        raise BolnaError("Invalid JSON received from Bolna API") from exc

    if not isinstance(data, dict):
        log.error("Bolna returned non-dictionary JSON response for task %s", task.id)
        raise BolnaError("Unexpected non-dictionary response received from Bolna API")

    raw_id = data.get("execution_id") or data.get("call_id") or data.get("id")
    if raw_id is None or not str(raw_id).strip():
        log.error("No valid call/execution ID returned by Bolna for task %s", task.id)
        raise BolnaError("No valid call/execution ID returned by Bolna")

    call_id = str(raw_id).strip()
    log.info("Bolna call created successfully for task %s: %s", task.id, call_id)
    return call_id
