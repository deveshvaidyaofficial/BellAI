"""Call-log reads. Owner: Utkarsh."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models import CallLog, CallOutcome, Task
from app.schemas import CallLogRead

router = APIRouter(prefix="/api/calls", tags=["calls"])

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@router.get("", response_model=List[CallLogRead])
def list_calls(
    task_id: Optional[int] = None,
    elder_id: Optional[int] = None,
    status: Optional[str] = None,
    outcome: Optional[CallOutcome] = None,
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    query = select(CallLog).order_by(CallLog.created_at.desc())
    if task_id is not None:
        query = query.where(CallLog.task_id == task_id)
    if elder_id is not None:
        task_ids = select(Task.id).where(Task.elder_id == elder_id)
        query = query.where(CallLog.task_id.in_(task_ids))
    if status is not None:
        query = query.where(CallLog.status == status)
    if outcome is not None:
        query = query.where(CallLog.outcome == outcome)
    return session.exec(query.offset(offset).limit(limit)).all()


@router.get("/{call_id}", response_model=CallLogRead)
def get_call(call_id: int, session: Session = Depends(get_session)):
    call = session.get(CallLog, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return call
