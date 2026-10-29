"""Call-log reads. Owner: Utkarsh."""

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
from app.models import CallLog  # noqa: E402


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
        test_client.engine = engine
        yield test_client
    app.dependency_overrides.clear()


def _elder(client, phone):
    res = client.post("/api/elders", json={"name": "Asha", "phone": phone})
    assert res.status_code == 201, res.text
    return res.json()


def _call(client, elder_id, title):
    task = client.post(
        "/api/tasks",
        json={
            "elder_id": elder_id,
            "title": title,
            "scheduled_at": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
        },
    )
    assert task.status_code == 201, task.text
    call = client.post("/api/tasks/{id}/call-now".format(id=task.json()["id"]))
    assert call.status_code == 200, call.text
    return task.json(), call.json()


def _stamp(client, call_id, when):
    with Session(client.engine) as session:
        row = session.get(CallLog, call_id)
        row.created_at = when
        session.add(row)
        session.commit()


def test_list_filters_pages_and_stays_newest_first(client):
    older = datetime(2026, 10, 1, 8, 0, 0)
    newer = datetime(2026, 10, 2, 8, 0, 0)
    asha = _elder(client, "+919811110000")
    ravi = _elder(client, "+919822220000")
    asha_task, asha_call = _call(client, asha["id"], "Take BP tablet")
    ravi_task, ravi_call = _call(client, ravi["id"], "Drink water")
    finished = client.post(
        "/api/webhook/call-outcome",
        json={
            "id": asha_call["bolna_call_id"],
            "status": "completed",
            "extracted_data": {"outcome": "completed"},
        },
    )
    assert finished.status_code == 200
    _stamp(client, asha_call["id"], older)
    _stamp(client, ravi_call["id"], newer)

    listed = client.get("/api/calls").json()
    assert [row["id"] for row in listed] == [ravi_call["id"], asha_call["id"]]

    by_task = client.get("/api/calls", params={"task_id": asha_task["id"]}).json()
    assert [row["id"] for row in by_task] == [asha_call["id"]]

    by_elder = client.get("/api/calls", params={"elder_id": ravi["id"]}).json()
    assert [row["id"] for row in by_elder] == [ravi_call["id"]]
    assert by_elder[0]["status"] == "queued"
    assert by_elder[0]["outcome"] is None

    by_status = client.get("/api/calls", params={"status": "completed"}).json()
    assert [row["id"] for row in by_status] == [asha_call["id"]]

    by_outcome = client.get("/api/calls", params={"outcome": "completed"}).json()
    assert [row["id"] for row in by_outcome] == [asha_call["id"]]
    assert client.get("/api/calls", params={"outcome": "no_answer"}).json() == []

    page = client.get("/api/calls", params={"limit": 1, "offset": 1}).json()
    assert [row["id"] for row in page] == [asha_call["id"]]

    both = client.get(
        "/api/calls",
        params={"elder_id": asha["id"], "status": "completed", "outcome": "completed"},
    ).json()
    assert [row["id"] for row in both] == [asha_call["id"]]
    assert ravi_task["id"] != asha_task["id"]


def test_get_one_call_or_404(client):
    elder = _elder(client, "+919833330000")
    _, call = _call(client, elder["id"], "Lunch")
    found = client.get("/api/calls/{id}".format(id=call["id"]))
    assert found.status_code == 200
    assert found.json()["bolna_call_id"] == call["bolna_call_id"]
    missing = client.get("/api/calls/9999")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Call not found"


def test_limit_is_capped(client):
    assert client.get("/api/calls", params={"limit": 201}).status_code == 422
    assert client.get("/api/calls", params={"limit": 0}).status_code == 422
    assert client.get("/api/calls", params={"offset": -1}).status_code == 422
