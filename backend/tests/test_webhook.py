"""Bolna callback hardening. Owner: Utkarsh."""

import logging
import os
from datetime import datetime, timedelta
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["BOLNA_MOCK"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.config import Settings  # noqa: E402
from app.db import get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _start_call(client):
    elder = client.post("/api/elders", json={"name": "Asha", "phone": "+919800000000"}).json()
    task = client.post(
        "/api/tasks",
        json={
            "elder_id": elder["id"],
            "type": "medication",
            "title": "Take BP tablet",
            "scheduled_at": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
        },
    ).json()
    call = client.post(f"/api/tasks/{task['id']}/call-now").json()
    return task, call["bolna_call_id"]


def _saved_status(client, task_id):
    rows = client.get(f"/api/calls?task_id={task_id}").json()
    assert len(rows) == 1
    return rows[0]["status"]


def test_unknown_call_id_is_acknowledged_and_not_retried(client):
    res = client.post("/api/webhook/call-outcome", json={"id": "does-not-exist", "status": "completed"})
    assert res.status_code == 200
    assert res.json() == {"ok": False, "reason": "unknown call id"}


def test_missing_call_id_returns_controlled_response(client):
    res = client.post("/api/webhook/call-outcome", json={"status": "completed"})
    assert res.status_code == 200
    assert res.json() == {"ok": False, "reason": "missing call id"}


def test_intermediate_status_does_not_move_the_task(client):
    task, call_id = _start_call(client)
    res = client.post(
        "/api/webhook/call-outcome",
        json={"id": call_id, "status": "in-progress", "transcript": "ringing"},
    )
    body = res.json()
    assert body["ok"] is True
    assert body["applied"] is False
    assert body["outcome"] is None
    assert body["task_status"] == "calling"
    assert client.get(f"/api/tasks/{task['id']}").json()["status"] == "calling"
    assert _saved_status(client, task["id"]) == "in-progress"


def test_duplicate_terminal_callback_does_not_apply_again(client):
    task, call_id = _start_call(client)
    first = client.post(
        "/api/webhook/call-outcome",
        json={"id": call_id, "status": "completed", "extracted_data": {"outcome": "completed"}},
    ).json()
    assert first["applied"] is True
    assert first["task_status"] == "completed"

    second = client.post(
        "/api/webhook/call-outcome",
        json={
            "id": call_id,
            "status": "completed",
            "extracted_data": {"outcome": "needs_help"},
            "transcript": "late copy",
        },
    ).json()
    assert second["duplicate"] is True
    assert second["applied"] is False
    assert second["outcome"] == "completed"
    saved = client.get(f"/api/tasks/{task['id']}").json()
    assert saved["status"] == "completed"
    assert saved["attempts"] == 0
    log = client.get(f"/api/calls?task_id={task['id']}").json()[0]
    assert log["outcome"] == "completed"
    assert log["transcript"] is None


def test_late_intermediate_update_does_not_overwrite_a_terminal_status(client):
    task, call_id = _start_call(client)
    client.post(
        "/api/webhook/call-outcome",
        json={"id": call_id, "status": " Completed ", "extracted_data": {"outcome": "completed"}},
    )
    late = client.post(
        "/api/webhook/call-outcome",
        json={"id": call_id, "status": "in-progress", "summary": "should not stick"},
    ).json()
    assert late["duplicate"] is True
    assert client.get(f"/api/tasks/{task['id']}").json()["status"] == "completed"
    log = client.get(f"/api/calls?task_id={task['id']}").json()[0]
    assert log["status"] == "completed"
    assert log["summary"] is None


def test_callback_for_a_deleted_task_logs_and_returns_200(client, caplog):
    task, call_id = _start_call(client)
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204

    with caplog.at_level(logging.WARNING, logger="app.routers.webhooks"):
        res = client.post(
            "/api/webhook/call-outcome",
            json={"id": call_id, "status": "completed", "extracted_data": {"outcome": "completed"}},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["applied"] is False
    assert body["task_status"] is None
    assert call_id in caplog.text
    assert str(task["id"]) in caplog.text


def test_finished_status_is_saved_when_the_task_is_not_calling(client):
    task, call_id = _start_call(client)
    moved = client.patch(f"/api/tasks/{task['id']}", json={"status": "pending"}).json()
    assert moved["status"] == "pending"

    first = client.post(
        "/api/webhook/call-outcome",
        json={"id": call_id, "status": "no-answer"},
    ).json()
    assert first["applied"] is False
    assert first["outcome"] == "no_answer"
    assert first["task_status"] == "pending"
    saved = client.get(f"/api/tasks/{task['id']}").json()
    assert saved["status"] == "pending"
    assert saved["attempts"] == 1
    log = client.get(f"/api/calls?task_id={task['id']}").json()[0]
    assert log["status"] == "no-answer"
    assert log["outcome"] == "no_answer"

    second = client.post(
        "/api/webhook/call-outcome",
        json={
            "id": call_id,
            "status": "completed",
            "extracted_data": {"outcome": "needs_help"},
            "transcript": "late copy",
        },
    ).json()
    assert second["duplicate"] is True
    assert second["applied"] is False
    assert second["outcome"] == "no_answer"
    assert client.get(f"/api/tasks/{task['id']}").json()["status"] == "pending"
    log = client.get(f"/api/calls?task_id={task['id']}").json()[0]
    assert log["outcome"] == "no_answer"
    assert log["status"] == "no-answer"
    assert log["transcript"] is None


def test_valid_terminal_callback_completed(client):
    task, call_id = _start_call(client)
    res = client.post(
        "/api/webhook/call-outcome",
        json={
            "id": call_id,
            "status": "completed",
            "transcript": "I have already taken the pill.",
            "summary": "Elder confirmed taking medicine.",
            "extracted_data": {
                "outcome": "completed",
                "note": "Elder took pill with water after breakfast",
            },
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["applied"] is True
    assert body["outcome"] == "completed"
    assert body["task_status"] == "completed"

    task_data = client.get(f"/api/tasks/{task['id']}").json()
    assert task_data["status"] == "completed"

    logs = client.get(f"/api/calls?task_id={task['id']}").json()
    assert len(logs) == 1
    assert logs[0]["outcome"] == "completed"
    assert logs[0]["extracted_note"] == "Elder took pill with water after breakfast"
    assert logs[0]["summary"] == "Elder confirmed taking medicine."


def test_valid_terminal_callback_later_with_snooze(client):
    task, call_id = _start_call(client)
    res = client.post(
        "/api/webhook/call-outcome",
        json={
            "id": call_id,
            "status": "completed",
            "extracted_data": {
                "outcome": "later",
                "snooze_minutes": 45,
                "note": "Finishing lunch now, asked to call back in 45 mins",
            },
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["applied"] is True
    assert body["outcome"] == "later"
    assert body["task_status"] == "snoozed"

    task_data = client.get(f"/api/tasks/{task['id']}").json()
    assert task_data["status"] == "snoozed"

    log_data = client.get(f"/api/calls?task_id={task['id']}").json()[0]
    assert log_data["extracted_note"] == "Finishing lunch now, asked to call back in 45 mins"


def test_valid_terminal_callback_needs_help(client):
    task, call_id = _start_call(client)
    res = client.post(
        "/api/webhook/call-outcome",
        json={
            "id": call_id,
            "status": "completed",
            "extracted_data": {
                "outcome": "needs_help",
                "note": "Elder felt dizzy and requested family assistance",
            },
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["applied"] is True
    assert body["outcome"] == "needs_help"
    assert body["task_status"] == "needs_help"

    task_data = client.get(f"/api/tasks/{task['id']}").json()
    assert task_data["status"] == "needs_help"

    log_data = client.get(f"/api/calls?task_id={task['id']}").json()[0]
    assert log_data["extracted_note"] == "Elder felt dizzy and requested family assistance"


def test_support_for_execution_id_field_in_payload(client):
    task, call_id = _start_call(client)
    # Bolna uses execution_id in API executions payload
    res = client.post(
        "/api/webhook/call-outcome",
        json={
            "execution_id": call_id,
            "status": "completed",
            "extracted_data": {"outcome": "completed"},
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["applied"] is True
    assert body["outcome"] == "completed"


def test_call_disconnected_without_outcome_is_intermediate_and_completed_finalizes(client):
    task, call_id = _start_call(client)

    # 1. Bolna sends call-disconnected immediately upon audio hangup (extracted_data not yet ready)
    disc_res = client.post(
        "/api/webhook/call-outcome",
        json={"id": call_id, "status": "call-disconnected", "transcript": "Call ended."},
    ).json()
    assert disc_res["ok"] is True
    assert disc_res["applied"] is False
    assert disc_res["outcome"] is None
    assert client.get(f"/api/tasks/{task['id']}").json()["status"] == "calling"

    # 2. Seconds later, Bolna sends completed with full extractions
    comp_res = client.post(
        "/api/webhook/call-outcome",
        json={
            "id": call_id,
            "status": "completed",
            "extracted_data": {
                "outcome": "completed",
                "note": "Confirmed by elder.",
            },
        },
    ).json()
    assert comp_res["ok"] is True
    assert comp_res["applied"] is True
    assert comp_res["outcome"] == "completed"
    assert comp_res["task_status"] == "completed"
    assert client.get(f"/api/tasks/{task['id']}").json()["status"] == "completed"

    log_data = client.get(f"/api/calls?task_id={task['id']}").json()[0]
    assert log_data["extracted_note"] == "Confirmed by elder."


def test_malformed_extraction_fields_handled_safely(client):
    task, call_id = _start_call(client)
    # Note is not a string, snooze_minutes is negative or invalid string, outcome unknown
    res = client.post(
        "/api/webhook/call-outcome",
        json={
            "id": call_id,
            "status": "completed",
            "extracted_data": {
                "outcome": "gibberish-not-an-outcome",
                "snooze_minutes": "not-a-number",
                "note": {"unexpected": "object"},
            },
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    # Unknown outcome on connected call falls back safely to needs_help
    assert body["outcome"] == "needs_help"
    log_data = client.get(f"/api/calls?task_id={task['id']}").json()[0]
    # Non-string note was safely ignored instead of crashing
    assert log_data["extracted_note"] is None


def test_webhook_auth_enforced_when_secret_configured(client):
    task, call_id = _start_call(client)
    secret_settings = Settings(
        bolna_mock=True,
        bolna_webhook_secret="super-secret-token",
    )

    with patch("app.routers.webhooks.get_settings", return_value=secret_settings):
        # 1. Missing secret header -> 401
        res_no_auth = client.post(
            "/api/webhook/call-outcome",
            json={"id": call_id, "status": "completed", "extracted_data": {"outcome": "completed"}},
        )
        assert res_no_auth.status_code == 401

        # 2. Invalid secret header -> 401
        res_bad_auth = client.post(
            "/api/webhook/call-outcome",
            json={"id": call_id, "status": "completed", "extracted_data": {"outcome": "completed"}},
            headers={"X-Bolna-Webhook-Secret": "wrong-secret"},
        )
        assert res_bad_auth.status_code == 401

        # 3. Valid X-Bolna-Webhook-Secret -> 200
        res_valid_custom = client.post(
            "/api/webhook/call-outcome",
            json={"id": call_id, "status": "completed", "extracted_data": {"outcome": "completed"}},
            headers={"X-Bolna-Webhook-Secret": "super-secret-token"},
        )
        assert res_valid_custom.status_code == 200
        assert res_valid_custom.json()["ok"] is True

    # 4. Valid Authorization: Bearer <secret> on fresh call
    task2, call_id2 = _start_call(client)
    with patch("app.routers.webhooks.get_settings", return_value=secret_settings):
        res_valid_bearer = client.post(
            "/api/webhook/call-outcome",
            json={"id": call_id2, "status": "completed", "extracted_data": {"outcome": "completed"}},
            headers={"Authorization": "Bearer super-secret-token"},
        )
        assert res_valid_bearer.status_code == 200
        assert res_valid_bearer.json()["ok"] is True
