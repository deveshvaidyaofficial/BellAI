"""Elder and trusted-contact routes. Owner: Utkarsh."""

import os
from datetime import datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["BOLNA_MOCK"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine, select  # noqa: E402

from app.db import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import TrustedContact  # noqa: E402

PHONE_ERROR = "Phone must be 10 to 15 digits, with an optional leading +."


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


def _elder(client, phone=" +919876543210 "):
    res = client.post("/api/elders", json={"name": "Asha", "phone": phone})
    assert res.status_code == 201, res.text
    return res.json()


def _contact(client, elder_id, phone=" +919811110000 "):
    res = client.post(
        "/api/elders/{id}/contacts".format(id=elder_id),
        json={"name": "Ravi", "phone": phone, "relation": "son"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_phone_is_trimmed_and_rejected_when_invalid(client):
    elder = _elder(client)
    assert elder["phone"] == "+919876543210"

    bad = client.post("/api/elders", json={"name": "Asha", "phone": "+91 98765"})
    assert bad.status_code == 422
    assert bad.json()["detail"] == PHONE_ERROR

    updated = client.patch(
        "/api/elders/{id}".format(id=elder["id"]),
        json={"phone": " 919800000000 "},
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "919800000000"

    still = client.patch("/api/elders/{id}".format(id=elder["id"]), json={"phone": "123"})
    assert still.status_code == 422
    assert still.json()["detail"] == PHONE_ERROR
    assert client.get("/api/elders/{id}".format(id=elder["id"])).json()["phone"] == "919800000000"

    contact = _contact(client, elder["id"])
    assert contact["phone"] == "+919811110000"
    rejected = client.post(
        "/api/elders/{id}/contacts".format(id=elder["id"]),
        json={"name": "Meera", "phone": "phone-number"},
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"] == PHONE_ERROR


def test_get_patch_and_delete_one_contact(client):
    elder = _elder(client)
    other = _elder(client, "+919822220000")
    contact = _contact(client, elder["id"])
    path = "/api/elders/{elder}/contacts/{contact}".format(elder=elder["id"], contact=contact["id"])
    other_path = "/api/elders/{elder}/contacts/{contact}".format(
        elder=other["id"], contact=contact["id"]
    )

    assert client.get(path).json()["name"] == "Ravi"
    assert client.get(other_path).status_code == 404
    assert client.get(
        "/api/elders/{elder}/contacts/9999".format(elder=elder["id"])
    ).status_code == 404

    patched = client.patch(path, json={"notify_on_missed": False, "relation": "nephew"})
    assert patched.status_code == 200
    assert patched.json()["notify_on_missed"] is False
    assert patched.json()["relation"] == "nephew"
    assert patched.json()["phone"] == "+919811110000"

    bad_phone = client.patch(path, json={"phone": "12"})
    assert bad_phone.status_code == 422
    assert client.get(path).json()["phone"] == "+919811110000"

    unknown = client.patch(path, json={"nickname": "R"})
    assert unknown.status_code == 422
    assert "nickname" in unknown.json()["detail"]

    assert client.delete(other_path).status_code == 404
    assert client.get(path).status_code == 200
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == 404


def test_delete_elder_removes_contacts_and_refuses_when_tasks_remain(client):
    elder = _elder(client)
    contact = _contact(client, elder["id"])
    task = client.post(
        "/api/tasks",
        json={
            "elder_id": elder["id"],
            "title": "Take BP tablet",
            "scheduled_at": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
        },
    )
    assert task.status_code == 201

    blocked = client.delete("/api/elders/{id}".format(id=elder["id"]))
    assert blocked.status_code == 409
    assert "tasks" in blocked.json()["detail"]
    assert client.get("/api/elders/{id}".format(id=elder["id"])).status_code == 200
    assert client.get("/api/tasks/{id}".format(id=task.json()["id"])).status_code == 200
    assert client.get(
        "/api/elders/{elder}/contacts/{contact}".format(elder=elder["id"], contact=contact["id"])
    ).status_code == 200

    assert client.delete("/api/tasks/{id}".format(id=task.json()["id"])).status_code == 204
    assert client.delete("/api/elders/{id}".format(id=elder["id"])).status_code == 204
    assert client.get("/api/elders/{id}".format(id=elder["id"])).status_code == 404
    with Session(client.engine) as session:
        left = session.exec(select(TrustedContact).where(TrustedContact.id == contact["id"])).first()
    assert left is None
