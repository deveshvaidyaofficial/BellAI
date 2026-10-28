"""Caregiver alerts. Owner: Utkarsh.

Ayush's `apply_outcome` decides when an alert is required. This module sends
it and, later, records whether delivery worked.

Prototype just logs. TODO: SMS / WhatsApp (e.g. Twilio, Gupshup) or a Bolna call to the contact.
"""

import logging

from sqlmodel import Session, select

from app.models import Elder, Task, TrustedContact

log = logging.getLogger(__name__)


def notify_caregivers(session: Session, task: Task, reason: str) -> None:
    elder = session.get(Elder, task.elder_id)
    contacts = session.exec(
        select(TrustedContact).where(
            TrustedContact.elder_id == task.elder_id,
            TrustedContact.notify_on_missed == True,  # noqa: E712
        )
    ).all()

    for c in contacts:
        log.warning(
            "[notify] %s (%s): %s — task '%s' for %s",
            c.name, c.phone, reason, task.title, elder.name if elder else task.elder_id,
        )
