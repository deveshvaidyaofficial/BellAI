"""Caregiver alerts. Owner: Utkarsh."""

from datetime import datetime

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models import CallLog, CallOutcome, Elder, Task, TrustedContact
from app.services.notifications import (
    DeliveryResult,
    MockSender,
    default_sender,
    format_delivery_result,
    notify_caregivers,
    send_caregiver_alert,
)


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def _task(session, phones, notify=True):
    elder = Elder(name="Asha", phone="+919800000000")
    session.add(elder)
    session.commit()
    session.refresh(elder)
    task = Task(
        elder_id=elder.id,
        title="Take BP tablet",
        scheduled_at=datetime.utcnow(),
    )
    session.add(task)
    for index, phone in enumerate(phones):
        session.add(
            TrustedContact(
                elder_id=elder.id,
                name="Ravi" if index == 0 else "Meera",
                phone=phone,
                relation="son",
                notify_on_missed=notify if index == 0 else True,
            )
        )
    session.commit()
    session.refresh(task)
    return task


def test_mock_sender_records_and_logs(caplog):
    sender = MockSender()
    with caplog.at_level("WARNING", logger="app.services.notifications"):
        sender.send("+919811110000", "hello")
    assert sender.sent[0].to == "+919811110000"
    assert sender.sent[0].message == "hello"
    assert "+919811110000" in caplog.text
    assert "hello" in caplog.text


def test_needs_help_and_no_answer_name_the_elder_task_and_outcome(session):
    task = _task(session, ["+919811110000"])
    sender = MockSender()

    help_result = send_caregiver_alert(session, task, CallOutcome.needs_help, sender)
    quiet = send_caregiver_alert(session, task, CallOutcome.no_answer, sender)

    assert help_result == [DeliveryResult("sent", "+919811110000", None)]
    assert quiet == [DeliveryResult("sent", "+919811110000", None)]
    assert sender.sent[0].message == "Asha needs help. Reminder: Take BP tablet."
    assert sender.sent[1].message == "Asha did not answer. Reminder: Take BP tablet."


def test_completed_and_later_send_nothing(session):
    task = _task(session, ["+919811110000"])
    sender = MockSender()
    assert send_caregiver_alert(session, task, CallOutcome.completed, sender) == []
    assert send_caregiver_alert(session, task, CallOutcome.later, sender) == []
    assert sender.sent == []


def test_failed_send_returns_why(session):
    task = _task(session, ["+919811110000", "+919822220000"])

    class Boom(object):
        def send(self, to, message):
            if to == "+919811110000":
                raise RuntimeError("gateway down")

    results = send_caregiver_alert(session, task, CallOutcome.needs_help, Boom())
    assert results[0] == DeliveryResult("failed", "+919811110000", "gateway down")
    assert results[1] == DeliveryResult("sent", "+919822220000", None)


def test_nobody_to_notify_is_a_failed_result(session):
    task = _task(session, ["+919811110000"], notify=False)
    sender = MockSender()
    assert send_caregiver_alert(session, task, CallOutcome.no_answer, sender) == [
        DeliveryResult("failed", None, "no caregiver to notify")
    ]
    assert sender.sent == []


def test_missing_phone_fails_that_contact_only(session):
    task = _task(session, ["", "+919822220000"])
    sender = MockSender()
    assert send_caregiver_alert(session, task, CallOutcome.needs_help, sender) == [
        DeliveryResult("failed", "", "missing phone"),
        DeliveryResult("sent", "+919822220000", None),
    ]
    assert len(sender.sent) == 1


def test_default_sender_is_the_mock(session):
    task = _task(session, ["+919811110000"])
    default_sender.sent.clear()
    result = send_caregiver_alert(session, task, CallOutcome.needs_help)
    assert result[0].status == "sent"
    assert default_sender.sent[-1].message.startswith("Asha needs help.")


def test_existing_notify_hook_uses_the_sender(session):
    task = _task(session, ["+919811110000"])
    sender = MockSender()
    notify_caregivers(session, task, "elder asked for help", sender)
    assert sender.sent[0].to == "+919811110000"
    assert "elder asked for help" in sender.sent[0].message
    assert "Take BP tablet" in sender.sent[0].message
    assert "Asha" in sender.sent[0].message


def test_format_delivery_result_for_storage():
    assert format_delivery_result([]) is None
    assert format_delivery_result([
        DeliveryResult("sent", "+919811110000", None),
        DeliveryResult("sent", "+919822220000", None),
    ]) == "sent"
    assert format_delivery_result([
        DeliveryResult("failed", None, "no caregiver to notify"),
    ]) == "failed: no caregiver to notify"
    assert format_delivery_result([
        DeliveryResult("sent", "+919811110000", None),
        DeliveryResult("failed", "+919822220000", "gateway down"),
        DeliveryResult("failed", "", "missing phone"),
    ]) == "failed: gateway down; missing phone"


def test_call_log_can_store_the_formatted_result(session):
    task = _task(session, ["+919811110000"])
    row = CallLog(
        task_id=task.id,
        delivery_result=format_delivery_result([DeliveryResult("sent", "+919811110000", None)]),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    assert row.delivery_result == "sent"
