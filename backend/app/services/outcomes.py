"""After a call. Two owners, one file.

`classify` (Utkarsh) maps a Bolna status and extracted outcome onto the shared
categories. `apply_outcome` (Ayush) is the only place a call's result changes a
task's status, including retry, snooze, and when a caregiver alert is required.
The scheduler (also Ayush's) sets `calling` before the call is placed.

See the status lifecycle in AGENTS.md.
"""

from datetime import timedelta
from typing import Optional

from sqlmodel import Session

from app.models import CallOutcome, Recurrence, Task, TaskStatus, utcnow
from app.services.notifications import notify_caregivers

DEFAULT_SNOOZE_MINUTES = 30

# Bolna call statuses that mean nobody picked up.
NO_ANSWER_STATUSES = {"no-answer", "busy", "failed", "canceled", "call-disconnected"}


def classify(provider_status: Optional[str], extracted_outcome: Optional[str]) -> CallOutcome:
    if extracted_outcome in CallOutcome.__members__:
        return CallOutcome(extracted_outcome)
    if provider_status in NO_ANSWER_STATUSES:
        return CallOutcome.no_answer
    # Call connected but the agent couldn't tell — treat as needing a human.
    return CallOutcome.needs_help


def apply_outcome(
    session: Session,
    task: Task,
    outcome: CallOutcome,
    snooze_minutes: Optional[int] = None,
) -> Task:
    now = utcnow()

    if outcome == CallOutcome.completed:
        if task.recurrence == Recurrence.none:
            task.status = TaskStatus.completed
        else:
            step = timedelta(days=1 if task.recurrence == Recurrence.daily else 7)
            task.scheduled_at = task.scheduled_at + step
            while task.scheduled_at <= now:
                task.scheduled_at += step
            task.status = TaskStatus.pending
        task.attempts = 0

    elif outcome == CallOutcome.later:
        task.scheduled_at = now + timedelta(minutes=snooze_minutes or DEFAULT_SNOOZE_MINUTES)
        task.status = TaskStatus.snoozed

    elif outcome == CallOutcome.needs_help:
        task.status = TaskStatus.needs_help
        notify_caregivers(session, task, "elder asked for help")

    elif outcome == CallOutcome.no_answer:
        if task.attempts < task.max_attempts:
            task.scheduled_at = now + timedelta(minutes=task.retry_minutes)
            task.status = TaskStatus.pending
        else:
            task.status = TaskStatus.missed
            notify_caregivers(session, task, f"no answer after {task.attempts} attempts")

    session.add(task)
    return task
