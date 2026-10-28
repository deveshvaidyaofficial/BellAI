"""Reminder HTTP routes, including call-now. Owner: Ayush."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Elder, Task
from app.schemas import CallLogRead, TaskCreate, TaskRead, TaskUpdate
from app.services.scheduler import place_call

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _get_task(session: Session, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


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
    task = Task.model_validate(body)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: Session = Depends(get_session)):
    return _get_task(session, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, body: TaskUpdate, session: Session = Depends(get_session)):
    task = _get_task(session, task_id)
    task.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: Session = Depends(get_session)):
    session.delete(_get_task(session, task_id))
    session.commit()


@router.post("/{task_id}/call-now", response_model=CallLogRead)
def call_now(task_id: int, session: Session = Depends(get_session)):
    """Demo helper: place the reminder call immediately."""
    return place_call(session, _get_task(session, task_id))
