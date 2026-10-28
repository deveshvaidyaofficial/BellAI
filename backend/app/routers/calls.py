"""Call-log reads. Owner: Utkarsh."""

from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import CallLog
from app.schemas import CallLogRead

router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.get("", response_model=List[CallLogRead])
def list_calls(task_id: Optional[int] = None, session: Session = Depends(get_session)):
    query = select(CallLog).order_by(CallLog.created_at.desc())
    if task_id is not None:
        query = query.where(CallLog.task_id == task_id)
    return session.exec(query).all()
