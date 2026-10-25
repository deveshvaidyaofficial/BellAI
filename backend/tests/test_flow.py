import os
from datetime import datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite://"  # in-memory
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
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_task(client, **overrides):
    elder = client.post("/api/elders", json={"name": "Asha", "phone": "+919800000000"}).json()
    body = {
        "elder_id": elder["id"],
        "type": "medication",
        "title": "Take BP tablet",
        "scheduled_at": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
        **overrides,
    }
    return client.post("/api/tasks", json=body).json()


def _call_and_reply(client, task_id, payload):
    call = client.post(f"/api/tasks/{task_id}/call-now").json()
    payload = {"id": call["bolna_call_id"], **payload}
    return client.post("/api/webhook/call-outcome", json=payload).json()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_completed(client):
    task = _make_task(client)
    res = _call_and_reply(client, task["id"], {"status": "completed", "extracted_data": {"outcome": "completed"}})
    assert res["task_status"] == "completed"


def test_daily_task_rolls_forward(client):
    task = _make_task(client, recurrence="daily")
    _call_and_reply(client, task["id"], {"status": "completed", "extracted_data": {"outcome": "completed"}})
    updated = client.get(f"/api/tasks/{task['id']}").json()
    assert updated["status"] == "pending"
    assert datetime.fromisoformat(updated["scheduled_at"]) > datetime.utcnow()


def test_later_snoozes(client):
    task = _make_task(client)
    res = _call_and_reply(
        client, task["id"], {"status": "completed", "extracted_data": {"outcome": "later", "snooze_minutes": 15}}
    )
    assert res["task_status"] == "snoozed"


def test_no_answer_retries_then_missed(client):
    task = _make_task(client, max_attempts=2)
    assert _call_and_reply(client, task["id"], {"status": "no-answer"})["task_status"] == "pending"
    assert _call_and_reply(client, task["id"], {"status": "no-answer"})["task_status"] == "missed"
