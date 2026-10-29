"""Due reminders, retries, and when a call is authorized. Owner: Ayush.

The provider request is Devesh's client (`bolna.trigger_call`). This module
stores the execution id he returns and does not call a task that is already
calling or finished.

Each poll:
1. Calls stuck in `calling` past CALL_TIMEOUT_MINUTES (the webhook never came)
   count as `no_answer`, so the task retries instead of hanging forever.
2. Due tasks are called if it is inside the elder's call window, in the elder's
   timezone. Outside the window they stay due and go out once it opens.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import and_, or_, update
from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine
from app.models import CallLog, CallOutcome, Elder, Recurrence, Task, TaskStatus, utcnow
from app.services import bolna
from app.services.outcomes import apply_outcome

log = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")

CALL_TIMEOUT_MINUTES = 15

# Statuses a call may start from. `missed` / `needs_help` are allowed because the
# scheduler re-calls recurring tasks at their next occurrence and a caregiver may
# retry from the dashboard. `calling` and `completed` are never called.
CALLABLE = (TaskStatus.pending, TaskStatus.snoozed, TaskStatus.missed, TaskStatus.needs_help)
ESCALATED = (TaskStatus.missed, TaskStatus.needs_help)


class CallNotAllowed(Exception):
    pass


def _parse_hhmm(value: str) -> Optional[time]:
    try:
        hours, minutes = value.split(":")
        return time(int(hours), int(minutes))
    except (AttributeError, ValueError):
        return None


def in_call_window(elder: Elder, now: datetime) -> bool:
    """Is `now` (naive UTC) inside the elder's call window, in their timezone?

    A window with start > end crosses midnight (e.g. 20:00–02:00). A bad
    timezone or time string falls back to "always allowed" rather than never
    calling.
    """
    try:
        tz = ZoneInfo(elder.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        log.warning("elder %s has unknown timezone %r", elder.id, elder.timezone)
        return True
    start, end = _parse_hhmm(elder.call_window_start), _parse_hhmm(elder.call_window_end)
    if start is None or end is None or start == end:
        return True

    local = now.replace(tzinfo=timezone.utc).astimezone(tz).time()
    if start < end:
        return start <= local < end
    return local >= start or local < end


def place_call(session: Session, task: Task) -> CallLog:
    """Call the elder for one task and record a CallLog. Used by the poller and /call-now.

    Raises CallNotAllowed if the task is not in a callable status. The status
    check and the move to `calling` are one UPDATE, so the poller and a
    call-now click can't both call the same task.
    """
    elder = session.get(Elder, task.elder_id)
    if elder is None:
        raise CallNotAllowed(f"task {task.id} has no elder")

    previous = task.status
    claimed = session.execute(
        update(Task)
        .where(Task.id == task.id, Task.status.in_(CALLABLE))
        .values(status=TaskStatus.calling)
    )
    if claimed.rowcount != 1:
        session.rollback()
        session.refresh(task)
        raise CallNotAllowed(f"task {task.id} is {task.status.value}")
    session.refresh(task)

    # A fresh occurrence (or a caregiver retry) after an escalation gets a full set of retries.
    task.attempts = 1 if previous in ESCALATED else task.attempts + 1
    log_row = CallLog(task_id=task.id)

    try:
        log_row.bolna_call_id = bolna.trigger_call(elder, task)
    except bolna.BolnaError as e:
        log.error("call failed for task %s: %s", task.id, e)
        log_row.status = "failed"
        log_row.outcome = CallOutcome.no_answer
        apply_outcome(session, task, CallOutcome.no_answer)

    session.add(task)
    session.add(log_row)
    session.commit()
    session.refresh(log_row)
    return log_row


def expire_stale_calls(session: Session, now: datetime) -> int:
    """Treat calls with no webhook after CALL_TIMEOUT_MINUTES as unanswered."""
    cutoff = now - timedelta(minutes=CALL_TIMEOUT_MINUTES)
    expired = 0
    for task in session.exec(select(Task).where(Task.status == TaskStatus.calling)).all():
        last = session.exec(
            select(CallLog).where(CallLog.task_id == task.id).order_by(CallLog.created_at.desc())
        ).first()
        if last is not None and last.created_at > cutoff:
            continue
        if last is not None and last.outcome is None:
            # Recording an outcome makes a late webhook for this call a no-op duplicate.
            last.status = "timeout"
            last.outcome = CallOutcome.no_answer
            last.updated_at = now
            session.add(last)
        log.warning("task %s: no webhook after %s min, treating as no answer", task.id, CALL_TIMEOUT_MINUTES)
        apply_outcome(session, task, CallOutcome.no_answer)
        expired += 1
    session.commit()
    return expired


def due_tasks(session: Session, now: datetime):
    return session.exec(
        select(Task)
        .where(
            Task.scheduled_at <= now,
            or_(
                Task.status.in_([TaskStatus.pending, TaskStatus.snoozed]),
                # Escalated recurring tasks were rolled to their next occurrence.
                and_(Task.status.in_(ESCALATED), Task.recurrence != Recurrence.none),
            ),
        )
        .order_by(Task.scheduled_at)
    ).all()


def poll_due_tasks() -> None:
    with Session(engine) as session:
        now = utcnow()
        expire_stale_calls(session, now)
        for task in due_tasks(session, now):
            elder = session.get(Elder, task.elder_id)
            if elder is None or not in_call_window(elder, now):
                continue
            try:
                place_call(session, task)
            except CallNotAllowed:
                continue
            except Exception:
                # One bad task must not stop the rest of this poll.
                log.exception("unexpected error calling task %s", task.id)
                session.rollback()


def start_scheduler() -> None:
    settings = get_settings()
    if not settings.scheduler_enabled or _scheduler.running:
        return
    _scheduler.add_job(
        poll_due_tasks,
        "interval",
        seconds=settings.scheduler_interval_seconds,
        id="poll_due_tasks",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    log.info("scheduler started (every %ss)", settings.scheduler_interval_seconds)


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
