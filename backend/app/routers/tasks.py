"""Reminder HTTP routes, including call-now. Owner: Ayush."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import CallOutcome, Elder, Recurrence, Task, TaskStatus
from app.schemas import CallLogRead, TaskCreate, TaskRead, TaskUpdate
from app.services.outcomes import apply_outcome
from app.services.scheduler import ESCALATED, CallNotAllowed, place_call

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

MAX_ATTEMPTS_LIMIT = 10
RETRY_MINUTES_LIMIT = 240


def _get_task(session: Session, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _check_fields(title: Optional[str], max_attempts: Optional[int], retry_minutes: Optional[int]) -> None:
    if title is not None and not title.strip():
        raise HTTPException(status_code=422, detail="title must not be empty")
    if max_attempts is not None and not 1 <= max_attempts <= MAX_ATTEMPTS_LIMIT:
        raise HTTPException(status_code=422, detail=f"max_attempts must be 1–{MAX_ATTEMPTS_LIMIT}")
    if retry_minutes is not None and not 1 <= retry_minutes <= RETRY_MINUTES_LIMIT:
        raise HTTPException(status_code=422, detail=f"retry_minutes must be 1–{RETRY_MINUTES_LIMIT}")


@router.get("", response_model=List[TaskRead])
def list_tasks(elder_id: Optional[int] = None, session: Session = Depends(get_session)):
    query = select(Task).order_by(Task.scheduled_at)
    if elder_id is not None:
        query = query.where(Task.elder_id == elder_id)
    return session.exec(query).all()


@router.post("", response_model=TaskRead, status_code=201)
def create_task(body: TaskCreate, session: Session = Depends(get_session)):
    if not session.get(Elder, body.elder_id):
        raise HTTPException(status_code=404, detail="Elder not found")
    _check_fields(body.title, body.max_attempts, body.retry_minutes)
    task = Task.model_validate(body, update={"title": body.title.strip(), "occurrence_at": body.scheduled_at})
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: Session = Depends(get_session)):
    return _get_task(session, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, body: TaskUpdate, session: Session = Depends(get_session)):
    """Edit a reminder. The only status a client may set is `pending`: reopen a
    resolved task, or reset one stuck in `calling` (a late webhook for that call
    is then recorded but not applied). Other status changes go through the
    scheduler or /resolve."""
    task = _get_task(session, task_id)
    changes = body.model_dump(exclude_unset=True)
    _check_fields(changes.get("title"), changes.get("max_attempts"), changes.get("retry_minutes"))

    if "status" in changes:
        if changes["status"] != TaskStatus.pending:
            raise HTTPException(status_code=422, detail="status can only be set to 'pending'")
        if task.status != TaskStatus.calling:
            task.attempts = 0  # reopening a finished task is a fresh start; a stuck call still counts
    if "scheduled_at" in changes:
        task.occurrence_at = changes["scheduled_at"]
        task.attempts = 0
    if "title" in changes:
        changes["title"] = changes["title"].strip()

    task.sqlmodel_update(changes)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: Session = Depends(get_session)):
    # Call logs are kept as history; the webhook handles a call whose task is gone.
    session.delete(_get_task(session, task_id))
    session.commit()


@router.post("/{task_id}/call-now", response_model=CallLogRead)
def call_now(task_id: int, session: Session = Depends(get_session)):
    """Place the reminder call immediately, ignoring the call window (the caregiver asked)."""
    try:
        return place_call(session, _get_task(session, task_id))
    except CallNotAllowed as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{task_id}/resolve", response_model=TaskRead)
def resolve(task_id: int, session: Session = Depends(get_session)):
    """Caregiver marks the current occurrence as handled (e.g. after a help alert).

    One-off tasks become `completed`. Recurring tasks go to their next occurrence;
    escalated ones were already moved there, so they just return to `pending`.
    """
    task = _get_task(session, task_id)
    if task.recurrence != Recurrence.none and task.status in ESCALATED:
        task.status = TaskStatus.pending
        session.add(task)
    else:
        apply_outcome(session, task, CallOutcome.completed)
    session.commit()
    session.refresh(task)
    return task
