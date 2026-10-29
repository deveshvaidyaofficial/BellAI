"""API request/response shapes. SHARED CONTRACT — mirror in frontend/src/lib/types.ts."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import field_validator
from sqlmodel import SQLModel

from app.models import CallOutcome, Recurrence, TaskStatus, TaskType


def _naive_utc(v: datetime) -> datetime:
    """We store naive UTC; convert any tz-aware input (e.g. '...Z' from browsers)."""
    return v.astimezone(timezone.utc).replace(tzinfo=None) if v.tzinfo else v


# ---- Elder ----
class ElderCreate(SQLModel):
    name: str
    phone: str
    language: str = "en"
    timezone: str = "Asia/Kolkata"
    call_window_start: str = "08:00"
    call_window_end: str = "21:00"
    notes: Optional[str] = None


class ElderUpdate(SQLModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    call_window_start: Optional[str] = None
    call_window_end: Optional[str] = None
    notes: Optional[str] = None


class ElderRead(ElderCreate):
    id: int
    created_at: datetime


# ---- Trusted contact ----
class ContactCreate(SQLModel):
    name: str
    phone: str
    relation: Optional[str] = None
    notify_on_missed: bool = True


class ContactRead(ContactCreate):
    id: int
    elder_id: int


# ---- Task ----
class TaskCreate(SQLModel):
    elder_id: int
    type: TaskType = TaskType.other
    title: str
    details: Optional[str] = None
    scheduled_at: datetime
    recurrence: Recurrence = Recurrence.none
    max_attempts: int = 3
    retry_minutes: int = 10

    @field_validator("scheduled_at")
    @classmethod
    def to_naive_utc(cls, v: datetime) -> datetime:
        return _naive_utc(v)


class TaskUpdate(SQLModel):
    type: Optional[TaskType] = None
    title: Optional[str] = None
    details: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    recurrence: Optional[Recurrence] = None
    status: Optional[TaskStatus] = None
    max_attempts: Optional[int] = None
    retry_minutes: Optional[int] = None

    @field_validator("scheduled_at")
    @classmethod
    def to_naive_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _naive_utc(v) if v else v


class TaskRead(TaskCreate):
    id: int
    status: TaskStatus
    attempts: int
    created_at: datetime


# ---- Call log ----
class CallLogRead(SQLModel):
    id: int
    task_id: int
    bolna_call_id: Optional[str]
    status: str
    outcome: Optional[CallOutcome]
    transcript: Optional[str]
    summary: Optional[str]
    delivery_result: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---- Bolna webhook ----
class BolnaWebhook(SQLModel):
    """Subset of Bolna's execution payload we rely on. Extra keys are ignored.

    `extracted_data` is produced by the agent's extraction prompt (see agent/README.md):
      {"outcome": "completed" | "later" | "needs_help", "snooze_minutes": 30, "note": "..."}
    """

    id: str  # Bolna execution / call id
    status: Optional[str] = None  # completed, no-answer, busy, failed, ...
    transcript: Optional[str] = None
    summary: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}


# ---- Caregiver auth ----
class OtpRequest(SQLModel):
    phone: str


class OtpRequestResponse(SQLModel):
    ok: bool = True
    code: Optional[str] = None


class OtpVerify(SQLModel):
    phone: str
    code: str


class GoogleAuthRequest(SQLModel):
    id_token: str


class CaregiverRead(SQLModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime


class AuthSession(SQLModel):
    token: str
    caregiver: CaregiverRead
