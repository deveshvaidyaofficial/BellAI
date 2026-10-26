"""Outbound calls via Bolna. Owner: Devesh.

Docs: https://docs.bolna.ai — POST /call starts an outbound call for an agent.
With BOLNA_MOCK=true no request is sent; a fake call id is returned.
"""

import logging
import uuid
from typing import Any, Dict

import httpx

from app.config import get_settings
from app.models import Elder, Task

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

    payload: Dict[str, Any] = {
        "agent_id": settings.bolna_agent_id,
        "recipient_phone_number": elder.phone,
        "user_data": build_user_data(elder, task),
    }
    if settings.bolna_from_phone_number:
        payload["from_phone_number"] = settings.bolna_from_phone_number

    try:
        resp = httpx.post(
            f"{settings.bolna_base_url}/call",
            json=payload,
            headers={"Authorization": f"Bearer {settings.bolna_api_key}"},
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise BolnaError(str(e)) from e

    data = resp.json()
    # TODO(voice): confirm the id field name against a real response.
    call_id = data.get("execution_id") or data.get("call_id") or data.get("id")
    if not call_id:
        raise BolnaError(f"No call id in Bolna response: {data}")
    return str(call_id)
