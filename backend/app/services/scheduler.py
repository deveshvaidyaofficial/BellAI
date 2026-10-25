"""Polls for due tasks and places calls. Owner: intermediate layer."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine
from app.models import CallLog, CallOutcome, Elder, Task, TaskStatus, utcnow
from app.services import bolna
from app.services.outcomes import apply_outcome

log = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")


def place_call(session: Session, task: Task) -> CallLog:
    """Call the elder for one task and record a CallLog. Used by the poller and /call-now."""
    elder = session.get(Elder, task.elder_id)
    task.attempts += 1
    task.status = TaskStatus.calling
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


def poll_due_tasks() -> None:
    # TODO(intermediate): respect elder.call_window_start/end in the elder's timezone.
    with Session(engine) as session:
        due = session.exec(
            select(Task).where(
                Task.status.in_([TaskStatus.pending, TaskStatus.snoozed]),
                Task.scheduled_at <= utcnow(),
            )
        ).all()
        for task in due:
            place_call(session, task)


def start_scheduler() -> None:
    settings = get_settings()
    if not settings.scheduler_enabled or _scheduler.running:
        return
    _scheduler.add_job(
        poll_due_tasks, "interval", seconds=settings.scheduler_interval_seconds, id="poll_due_tasks"
    )
    _scheduler.start()
    log.info("scheduler started (every %ss)", settings.scheduler_interval_seconds)


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
