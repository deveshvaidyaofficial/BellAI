"""Caregiver alerts. Owner: Utkarsh.

Ayush's `apply_outcome` decides when an alert is required. This module sends
it. The result is returned to the caller. It is not stored yet.

`MockSender` is the default. A later SMS or WhatsApp provider can implement
`send(to, message)` without changing the alert text.
"""

import logging
from typing import List, NamedTuple, Optional, Protocol

from sqlmodel import Session, select

from app.models import CallOutcome, Elder, Task, TrustedContact

log = logging.getLogger(__name__)

_ALERT_OUTCOMES = {
    CallOutcome.needs_help: "needs help",
    CallOutcome.no_answer: "did not answer",
}


class Sender(Protocol):
    def send(self, to: str, message: str) -> None:
        """Deliver one message. Raise if it did not go out."""


class SentMessage(NamedTuple):
    to: str
    message: str


class DeliveryResult(NamedTuple):
    """status is 'sent' or 'failed'. detail is why it failed, otherwise None."""

    status: str
    to: Optional[str]
    detail: Optional[str]


class MockSender:
    """Records alerts in memory and logs them. Nothing leaves the machine."""

    def __init__(self) -> None:
        self.sent: List[SentMessage] = []

    def send(self, to: str, message: str) -> None:
        self.sent.append(SentMessage(to, message))
        log.warning("[notify] %s: %s", to, message)


default_sender = MockSender()


def _contacts(session: Session, elder_id: int) -> List[TrustedContact]:
    return list(
        session.exec(
            select(TrustedContact).where(
                TrustedContact.elder_id == elder_id,
                TrustedContact.notify_on_missed == True,  # noqa: E712
            )
        ).all()
    )


def _deliver(sender: Sender, contacts: List[TrustedContact], message: str) -> List[DeliveryResult]:
    if not contacts:
        return [DeliveryResult("failed", None, "no caregiver to notify")]
    results: List[DeliveryResult] = []
    for contact in contacts:
        phone = (contact.phone or "").strip()
        if not phone:
            results.append(DeliveryResult("failed", contact.phone, "missing phone"))
            continue
        try:
            sender.send(phone, message)
        except Exception as exc:
            results.append(DeliveryResult("failed", phone, str(exc)))
        else:
            results.append(DeliveryResult("sent", phone, None))
    return results


def send_caregiver_alert(
    session: Session,
    task: Task,
    outcome: CallOutcome,
    sender: Optional[Sender] = None,
) -> List[DeliveryResult]:
    """Alert caregivers for needs_help or no_answer. completed and later send nothing.

    Not called from the webhook or the scheduler. `apply_outcome` is the place
    that knows a no_answer has used up its retries.
    """
    words = _ALERT_OUTCOMES.get(outcome)
    if words is None:
        return []
    elder = session.get(Elder, task.elder_id)
    elder_name = elder.name if elder and elder.name else "the elder"
    message = "{name} {words}. Reminder: {title}.".format(
        name=elder_name, words=words, title=task.title
    )
    active = sender if sender is not None else default_sender
    return _deliver(active, _contacts(session, task.elder_id), message)


def notify_caregivers(
    session: Session,
    task: Task,
    reason: str,
    sender: Optional[Sender] = None,
) -> None:
    """Existing hook used by apply_outcome. Sends the reason Ayush already chose."""
    elder = session.get(Elder, task.elder_id)
    elder_name = elder.name if elder and elder.name else str(task.elder_id)
    active = sender if sender is not None else default_sender
    for contact in _contacts(session, task.elder_id):
        message = "{name}: {reason} — task '{title}' for {elder}".format(
            name=contact.name,
            reason=reason,
            title=task.title,
            elder=elder_name,
        )
        try:
            active.send(contact.phone, message)
        except Exception:
            log.exception("caregiver alert failed for task %s", task.id)
