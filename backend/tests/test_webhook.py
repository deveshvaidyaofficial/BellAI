"""Bolna callback hardening. Owner: Utkarsh."""

import logging
import os
from datetime import datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["BOLNA_MOCK"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

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
