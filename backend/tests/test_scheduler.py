"""Scheduler, retries, and reminder routes. Owner: Ayush."""

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["BOLNA_MOCK"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.db import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import CallLog, Elder, Task  # noqa: E402
from app.services import bolna, scheduler  # noqa: E402
from app.services.outcomes import DEFAULT_SNOOZE_MINUTES, MAX_SNOOZE_MINUTES, snooze_minutes_from  # noqa: E402


@pytest.fixture
def engine(monkeypatch):
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(test_engine)
    monkeypatch.setattr(scheduler, "engine", test_engine)
    return test_engine


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _elder(client, **overrides):
    body = {"name": "Asha", "phone": "+919800000000", **overrides}
    return client.post("/api/elders", json=body).json()


def _task(client, elder_id, **overrides):
    body = {
        "elder_id": elder_id,
        "type": "medication",
        "title": "BP tablet",
        "scheduled_at": _iso(datetime.utcnow() - timedelta(minutes=1)),
        **overrides,
    }
    res = client.post("/api/tasks", json=body)
    assert res.status_code == 201, res.text
    return res.json()


def _reply(client, call_id, status="completed", outcome=None, **extracted):
    payload = {"id": call_id, "status": status}
    if outcome:
        payload["extracted_data"] = {"outcome": outcome, **extracted}
    return client.post("/api/webhook/call-outcome", json=payload).json()


def _get(client, task_id):
    return client.get(f"/api/tasks/{task_id}").json()


def _calls(client, task_id):
    return client.get(f"/api/calls?task_id={task_id}").json()


def _always_open():
    return {"call_window_start": "00:00", "call_window_end": "00:00"}


# ---- call window ----

def _elder_obj(start, end, tz="Asia/Kolkata"):
    return Elder(id=1, name="x", phone="+1", timezone=tz, call_window_start=start, call_window_end=end)


def _utc_for_local(hhmm: str, tz="Asia/Kolkata") -> datetime:
    h, m = map(int, hhmm.split(":"))
    local = datetime(2026, 10, 29, h, m, tzinfo=ZoneInfo(tz))
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def test_call_window_uses_elder_timezone():
    elder = _elder_obj("08:00", "21:00")
    assert scheduler.in_call_window(elder, _utc_for_local("09:00"))
    assert not scheduler.in_call_window(elder, _utc_for_local("07:59"))
    assert not scheduler.in_call_window(elder, _utc_for_local("21:00"))


def test_call_window_across_midnight():
    elder = _elder_obj("20:00", "02:00")
    assert scheduler.in_call_window(elder, _utc_for_local("23:30"))
    assert scheduler.in_call_window(elder, _utc_for_local("01:00"))
    assert not scheduler.in_call_window(elder, _utc_for_local("12:00"))


def test_bad_window_or_timezone_does_not_block_calls():
    now = datetime.utcnow()
    assert scheduler.in_call_window(_elder_obj("08:00", "21:00", tz="Not/AZone"), now)
    assert scheduler.in_call_window(_elder_obj("8am", "9pm"), now)


def test_poll_skips_elder_outside_window(client):
    local_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    start = (local_now + timedelta(hours=2)).strftime("%H:%M")
    end = (local_now + timedelta(hours=3)).strftime("%H:%M")
    elder = _elder(client, call_window_start=start, call_window_end=end)
    task = _task(client, elder["id"])

    scheduler.poll_due_tasks()
    assert _get(client, task["id"])["status"] == "pending"
    assert _calls(client, task["id"]) == []


def test_poll_calls_elder_inside_window(client):
    elder = _elder(client, **_always_open())
    task = _task(client, elder["id"])

    scheduler.poll_due_tasks()
    assert _get(client, task["id"])["status"] == "calling"
    assert len(_calls(client, task["id"])) == 1


# ---- no double calls ----

def test_poll_does_not_recall_a_task_already_calling(client):
    elder = _elder(client, **_always_open())
    task = _task(client, elder["id"])
    client.post(f"/api/tasks/{task['id']}/call-now")

    scheduler.poll_due_tasks()
    assert len(_calls(client, task["id"])) == 1
    assert _get(client, task["id"])["attempts"] == 1


def test_call_now_rejects_calling_and_completed(client):
    elder = _elder(client)
    task = _task(client, elder["id"])
    call = client.post(f"/api/tasks/{task['id']}/call-now").json()
    assert client.post(f"/api/tasks/{task['id']}/call-now").status_code == 409

    _reply(client, call["bolna_call_id"], outcome="completed")
    assert client.post(f"/api/tasks/{task['id']}/call-now").status_code == 409


def test_provider_error_counts_as_no_answer(client, monkeypatch):
    def boom(elder, task):
        raise bolna.BolnaError("timeout")

    monkeypatch.setattr(bolna, "trigger_call", boom)
    elder = _elder(client)
    task = _task(client, elder["id"])
    call = client.post(f"/api/tasks/{task['id']}/call-now").json()

    assert call["status"] == "failed" and call["outcome"] == "no_answer"
    after = _get(client, task["id"])
    assert after["status"] == "pending" and after["attempts"] == 1


# ---- stuck calls ----

def test_stale_call_times_out_and_late_webhook_is_ignored(client, engine):
    elder = _elder(client)
    task = _task(client, elder["id"])
    call = client.post(f"/api/tasks/{task['id']}/call-now").json()

    with Session(engine) as s:
        row = s.get(CallLog, call["id"])
        row.created_at = datetime.utcnow() - timedelta(minutes=scheduler.CALL_TIMEOUT_MINUTES + 1)
        s.add(row)
        s.commit()
        assert scheduler.expire_stale_calls(s, datetime.utcnow()) == 1

    assert _get(client, task["id"])["status"] == "pending"
    assert _calls(client, task["id"])[0]["status"] == "timeout"

    late = _reply(client, call["bolna_call_id"], outcome="completed")
    assert late["duplicate"] is True
    assert _get(client, task["id"])["status"] == "pending"


def test_recent_call_is_not_timed_out(client, engine):
    elder = _elder(client)
    task = _task(client, elder["id"])
    client.post(f"/api/tasks/{task['id']}/call-now")
    with Session(engine) as s:
        assert scheduler.expire_stale_calls(s, datetime.utcnow()) == 0
    assert _get(client, task["id"])["status"] == "calling"


# ---- outcomes ----

def test_daily_reminder_does_not_drift_after_snooze(client, engine):
    planned = (datetime.utcnow() - timedelta(minutes=5)).replace(second=0, microsecond=0)
    elder = _elder(client)
    task = _task(client, elder["id"], scheduled_at=_iso(planned), recurrence="daily")

    first = client.post(f"/api/tasks/{task['id']}/call-now").json()
    _reply(client, first["bolna_call_id"], outcome="later", snooze_minutes=30)
    second = client.post(f"/api/tasks/{task['id']}/call-now").json()
    _reply(client, second["bolna_call_id"], outcome="completed")

    after = datetime.fromisoformat(_get(client, task["id"])["scheduled_at"])
    assert after == planned + timedelta(days=1)


def test_snooze_resets_attempts(client):
    elder = _elder(client)
    task = _task(client, elder["id"], max_attempts=2)
    first = client.post(f"/api/tasks/{task['id']}/call-now").json()
    _reply(client, first["bolna_call_id"], status="no-answer")
    second = client.post(f"/api/tasks/{task['id']}/call-now").json()
    res = _reply(client, second["bolna_call_id"], outcome="later")

    assert res["task_status"] == "snoozed"
    assert _get(client, task["id"])["attempts"] == 0


def test_snooze_minutes_are_clamped():
    assert snooze_minutes_from(None) == DEFAULT_SNOOZE_MINUTES
    assert snooze_minutes_from("soon") == DEFAULT_SNOOZE_MINUTES
    assert snooze_minutes_from("15") == 15
    assert snooze_minutes_from(10_000) == MAX_SNOOZE_MINUTES
    assert snooze_minutes_from(0) == 5


def test_recurring_missed_rolls_forward_and_is_called_next_time(client, engine):
    elder = _elder(client, **_always_open())
    task = _task(client, elder["id"], recurrence="daily", max_attempts=1)
    call = client.post(f"/api/tasks/{task['id']}/call-now").json()
    res = _reply(client, call["bolna_call_id"], status="no-answer")

    assert res["task_status"] == "missed"
    after = _get(client, task["id"])
    assert datetime.fromisoformat(after["scheduled_at"]) > datetime.utcnow()

    # Next occurrence arrives.
    with Session(engine) as s:
        row = s.get(Task, task["id"])
        row.scheduled_at = datetime.utcnow() - timedelta(minutes=1)
        s.add(row)
        s.commit()
    scheduler.poll_due_tasks()
    again = _get(client, task["id"])
    assert again["status"] == "calling" and again["attempts"] == 1


def test_one_off_missed_is_not_called_again_by_poller(client):
    elder = _elder(client, **_always_open())
    task = _task(client, elder["id"], max_attempts=1)
    call = client.post(f"/api/tasks/{task['id']}/call-now").json()
    _reply(client, call["bolna_call_id"], status="no-answer")

    scheduler.poll_due_tasks()
    assert _get(client, task["id"])["status"] == "missed"
    assert len(_calls(client, task["id"])) == 1


# ---- routes ----

def test_create_validates_fields(client):
    elder = _elder(client)
    base = {"elder_id": elder["id"], "title": "x", "scheduled_at": _iso(datetime.utcnow())}
    assert client.post("/api/tasks", json={**base, "title": "   "}).status_code == 422
    assert client.post("/api/tasks", json={**base, "max_attempts": 0}).status_code == 422
    assert client.post("/api/tasks", json={**base, "retry_minutes": 999}).status_code == 422


def test_patch_status_only_allows_reopen(client):
    elder = _elder(client)
    task = _task(client, elder["id"], max_attempts=1)
    tid = task["id"]
    assert client.patch(f"/api/tasks/{tid}", json={"status": "completed"}).status_code == 422

    call = client.post(f"/api/tasks/{tid}/call-now").json()
    _reply(client, call["bolna_call_id"], status="no-answer")
    assert _get(client, tid)["status"] == "missed"

    reopened = client.patch(f"/api/tasks/{tid}", json={"status": "pending"}).json()
    assert reopened["status"] == "pending" and reopened["attempts"] == 0


def test_resolve_one_off_and_recurring(client):
    elder = _elder(client)
    one_off = _task(client, elder["id"])
    daily = _task(client, elder["id"], recurrence="daily")

    for t in (one_off, daily):
        call = client.post(f"/api/tasks/{t['id']}/call-now").json()
        assert _reply(client, call["bolna_call_id"], outcome="needs_help")["task_status"] == "needs_help"

    assert client.post(f"/api/tasks/{one_off['id']}/resolve").json()["status"] == "completed"
    resolved = client.post(f"/api/tasks/{daily['id']}/resolve").json()
    assert resolved["status"] == "pending"
    assert datetime.fromisoformat(resolved["scheduled_at"]) > datetime.utcnow()
