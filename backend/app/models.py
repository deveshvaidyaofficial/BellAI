"""DB tables. SHARED CONTRACT — announce changes before editing (see AGENTS.md)."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.utcnow()


class TaskType(str, Enum):
    medication = "medication"
    appointment = "appointment"
    meal = "meal"
    hydration = "hydration"
    other = "other"


class Recurrence(str, Enum):
    none = "none"
    daily = "daily"
    weekly = "weekly"


class TaskStatus(str, Enum):
    pending = "pending"
    calling = "calling"
    completed = "completed"
    snoozed = "snoozed"
    needs_help = "needs_help"
    missed = "missed"


class CallOutcome(str, Enum):
    completed = "completed"
    later = "later"
    needs_help = "needs_help"
    no_answer = "no_answer"


class Elder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    phone: str  # E.164, e.g. +919876543210
    language: str = "en"  # en, hi, mr, ...
    timezone: str = "Asia/Kolkata"
    call_window_start: str = "08:00"  # local time HH:MM
    call_window_end: str = "21:00"
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class TrustedContact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    elder_id: int = Field(foreign_key="elder.id", index=True)
    name: str
    phone: str
    relation: Optional[str] = None
    notify_on_missed: bool = True


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    elder_id: int = Field(foreign_key="elder.id", index=True)
    type: TaskType = TaskType.other
    title: str  # e.g. "Take Metformin 500mg"
    details: Optional[str] = None  # e.g. "after breakfast, with water"
    scheduled_at: datetime = Field(index=True)  # next due time, naive UTC
    # Planned time of the current occurrence. scheduled_at moves with snoozes and
    # retries; this does not, so recurring reminders don't drift. Internal only.
    occurrence_at: Optional[datetime] = None
    recurrence: Recurrence = Recurrence.none
    status: TaskStatus = Field(default=TaskStatus.pending, index=True)
    attempts: int = 0
    max_attempts: int = 3
    retry_minutes: int = 10
    created_at: datetime = Field(default_factory=utcnow)


class CallLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    bolna_call_id: Optional[str] = Field(default=None, index=True)
    status: str = "queued"  # raw provider status
    outcome: Optional[CallOutcome] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    extracted_note: Optional[str] = None
    delivery_result: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Caregiver(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    phone: Optional[str] = Field(default=None, unique=True, index=True)
    email: Optional[str] = Field(default=None, unique=True, index=True)
    google_sub: Optional[str] = Field(default=None, unique=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)


class OtpCode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(unique=True, index=True)
    code_hash: str
    expires_at: datetime
    attempts: int = 0
    created_at: datetime = Field(default_factory=utcnow)
