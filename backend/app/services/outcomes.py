"""After a call. Two owners, one file.

`classify` (Utkarsh) maps a Bolna status and extracted outcome onto the shared
categories. `apply_outcome` (Ayush) is the only place a call's result changes a
task's status, including retry, snooze, and when a caregiver alert is required.
The scheduler (also Ayush's) sets `calling` before the call is placed.

See the status lifecycle in AGENTS.md.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlmodel import Session

from app.models import CallLog, CallOutcome, Recurrence, Task, TaskStatus, utcnow
from app.services.notifications import format_delivery_result, send_caregiver_alert

DEFAULT_SNOOZE_MINUTES = 30

# Bolna call statuses that mean nobody picked up.
NO_ANSWER_STATUSES = {"no-answer", "busy", "failed", "canceled", "call-disconnected"}


def classify(provider_status: Optional[str], extracted_outcome: Optional[str]) -> CallOutcome:
    def _clean(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = value.strip().lower()
        return text or None

    # Discussion names. The stored codes stay completed, later, needs_help, no_answer.
    aliases = {
        "requested-later": CallOutcome.later,
        "help-needed": CallOutcome.needs_help,
        "unresolved": CallOutcome.needs_help,
        "no-answer": CallOutcome.no_answer,
        "failed-call": CallOutcome.no_answer,
    }
    status = _clean(provider_status)
    outcome = _clean(extracted_outcome)
    if outcome in aliases:
        return aliases[outcome]
    if outcome in CallOutcome.__members__:
        return CallOutcome(outcome)
    if status in NO_ANSWER_STATUSES:
        return CallOutcome.no_answer
    # Call connected but the agent couldn't tell — treat as needing a human.
    return CallOutcome.needs_help


MIN_SNOOZE_MINUTES = 5
MAX_SNOOZE_MINUTES = 240


def snooze_minutes_from(raw: Any) -> int:
    """The agent's extracted snooze value, clamped. Missing or junk → the default."""
    try:
        minutes = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_SNOOZE_MINUTES
    return min(max(minutes, MIN_SNOOZE_MINUTES), MAX_SNOOZE_MINUTES)


def roll_to_next_occurrence(task: Task, now: datetime) -> None:
    """Move a recurring task to its next planned time after `now`."""
    step = timedelta(days=1 if task.recurrence == Recurrence.daily else 7)
    nxt = (task.occurrence_at or task.scheduled_at) + step
    while nxt <= now:
        nxt += step
    task.occurrence_at = nxt
    task.scheduled_at = nxt
    task.attempts = 0


def _alert(session: Session, task: Task, outcome: CallOutcome, call: Optional[CallLog]) -> None:
    results = send_caregiver_alert(session, task, outcome)
    if call is not None:
        call.delivery_result = format_delivery_result(results)
        session.add(call)


def apply_outcome(
    session: Session,
    task: Task,
    outcome: CallOutcome,
    snooze_minutes: Any = None,
    call: Optional[CallLog] = None,
) -> Task:
    """Apply a call result to a task.

    Recurring tasks never stop: after `needs_help` or the final missed attempt the
    caregiver is alerted, the task shows `needs_help` / `missed`, and it is
    already rolled to its next occurrence, where the scheduler picks it up again.

    When an alert goes out, whether it was delivered is saved on `call` (the
    call this outcome came from), if one is given.
    """
    now = utcnow()
    recurring = task.recurrence != Recurrence.none

    if outcome == CallOutcome.completed:
        if recurring:
            roll_to_next_occurrence(task, now)
            task.status = TaskStatus.pending
        else:
            task.status = TaskStatus.completed
            task.attempts = 0

    elif outcome == CallOutcome.later:
        task.scheduled_at = now + timedelta(minutes=snooze_minutes_from(snooze_minutes))
        task.status = TaskStatus.snoozed
        task.attempts = 0  # they picked up; retries count unanswered calls only

    elif outcome == CallOutcome.needs_help:
        task.status = TaskStatus.needs_help
        _alert(session, task, outcome, call)
        if recurring:
            roll_to_next_occurrence(task, now)

    elif outcome == CallOutcome.no_answer:
        if task.attempts < task.max_attempts:
            task.scheduled_at = now + timedelta(minutes=task.retry_minutes)
            task.status = TaskStatus.pending
        else:
            task.status = TaskStatus.missed
            _alert(session, task, outcome, call)
            if recurring:
                roll_to_next_occurrence(task, now)

    session.add(task)
    return task
