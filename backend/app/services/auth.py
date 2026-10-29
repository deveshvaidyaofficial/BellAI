"""Caregiver sign-in. Owner: Utkarsh.

Phone OTP and Google both return a signed session token. Codes and tokens are
never written to the log. The OTP text is handed to the notifications sender
when that sender exists.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import jwt
from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.models import Caregiver, OtpCode, utcnow
from app.schemas import AuthSession, CaregiverRead, OtpRequestResponse
from app.services.phones import normalize_phone

OTP_TTL = timedelta(minutes=5)
OTP_COOLDOWN = timedelta(seconds=30)
OTP_ATTEMPTS = 5
TOKEN_TTL = timedelta(days=7)
_EPOCH = datetime(1970, 1, 1)
_GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


class _Outbox(object):
    """Used only when notifications.default_sender is not on this branch."""

    def __init__(self) -> None:
        self.sent: List[Tuple[str, str]] = []

    def send(self, to: str, message: str) -> None:
        self.sent.append((to, message))


_outbox = _Outbox()


def get_code_sender() -> Any:
    """Notifications MockSender when it is imported; otherwise an in-memory outbox.

    The outbox does not log. MockSender, on the alerts branch, logs the message
    text, which would include the code.
    """
    from app.services import notifications

    sender = getattr(notifications, "default_sender", None)
    if sender is not None and callable(getattr(sender, "send", None)):
        return sender
    return _outbox


def _epoch(value: datetime) -> int:
    """Naive UTC datetime as a unix timestamp. Avoid datetime.timestamp(), which
    treats a naive value as local time."""
    return int((value - _EPOCH).total_seconds())


def _phone_or_422(phone: str) -> str:
    try:
        return normalize_phone(phone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _hash_code(phone: str, code: str) -> str:
    secret = get_settings().auth_secret.encode("utf-8")
    text = "{phone}:{code}".format(phone=phone, code=code).encode("utf-8")
    return hmac.new(secret, text, hashlib.sha256).hexdigest()


def _caregiver_read(caregiver: Caregiver) -> CaregiverRead:
    return CaregiverRead(
        id=caregiver.id,
        name=caregiver.name,
        phone=caregiver.phone,
        email=caregiver.email,
        created_at=caregiver.created_at,
    )


def make_token(caregiver_id: int) -> str:
    secret = get_settings().auth_secret
    if not secret:
        raise HTTPException(status_code=500, detail="Auth is not configured")
    payload = {"sub": str(caregiver_id), "exp": _epoch(utcnow() + TOKEN_TTL)}
    encoded = jwt.encode(payload, secret, algorithm="HS256")
    if isinstance(encoded, bytes):
        return encoded.decode("ascii")
    return encoded


def _session_for(caregiver: Caregiver) -> AuthSession:
    if caregiver.id is None:
        raise HTTPException(status_code=500, detail="Could not create the account")
    return AuthSession(token=make_token(caregiver.id), caregiver=_caregiver_read(caregiver))


def request_phone_otp(session: Session, phone: str) -> OtpRequestResponse:
    normalized = _phone_or_422(phone)
    now = utcnow()
    row = session.exec(select(OtpCode).where(OtpCode.phone == normalized)).first()
    if row is not None and row.created_at + OTP_COOLDOWN > now:
        raise HTTPException(status_code=429, detail="Wait 30 seconds before requesting another code.")

    code = "{:06d}".format(secrets.randbelow(1000000))
    message = "Your BellAI sign-in code is {code}. It expires in 5 minutes.".format(code=code)
    try:
        get_code_sender().send(normalized, message)
    except Exception:
        raise HTTPException(status_code=502, detail="Could not send the code.")

    if row is None:
        row = OtpCode(
            phone=normalized,
            code_hash=_hash_code(normalized, code),
            expires_at=now + OTP_TTL,
            attempts=0,
            created_at=now,
        )
    else:
        row.code_hash = _hash_code(normalized, code)
        row.expires_at = now + OTP_TTL
        row.attempts = 0
        row.created_at = now
    session.add(row)
    session.commit()

    shown = code if get_settings().otp_mock else None
    return OtpRequestResponse(ok=True, code=shown)


def verify_phone_otp(session: Session, phone: str, code: str) -> AuthSession:
    normalized = _phone_or_422(phone)
    submitted = (code or "").strip()
    row = session.exec(select(OtpCode).where(OtpCode.phone == normalized)).first()
    if row is None or len(submitted) != 6 or not submitted.isdigit():
        raise HTTPException(status_code=401, detail="That code is wrong.")
    if row.expires_at <= utcnow():
        raise HTTPException(status_code=401, detail="That code has expired. Request a new one.")
    if row.attempts >= OTP_ATTEMPTS:
        raise HTTPException(status_code=401, detail="Too many attempts. Request a new one.")
    if not hmac.compare_digest(row.code_hash, _hash_code(normalized, submitted)):
        row.attempts += 1
        session.add(row)
        session.commit()
        if row.attempts >= OTP_ATTEMPTS:
            raise HTTPException(status_code=401, detail="Too many attempts. Request a new one.")
        raise HTTPException(status_code=401, detail="That code is wrong.")

    session.delete(row)
    caregiver = session.exec(select(Caregiver).where(Caregiver.phone == normalized)).first()
    if caregiver is None:
        caregiver = Caregiver(name=normalized, phone=normalized)
        session.add(caregiver)
    session.commit()
    session.refresh(caregiver)
    return _session_for(caregiver)


def verify_google_id_token(id_token: str) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        info = google_id_token.verify_oauth2_token(
            id_token, google_requests.Request(), settings.google_client_id
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Google sign-in failed")
    if info.get("iss") not in _GOOGLE_ISSUERS or not info.get("sub"):
        raise HTTPException(status_code=401, detail="Google sign-in failed")
    return info


def login_with_google(session: Session, id_token: str) -> AuthSession:
    info = verify_google_id_token(id_token)
    sub = str(info.get("sub"))
    email = (info.get("email") or "").strip().lower() or None
    if info.get("email_verified") is False:
        email = None
    name = (info.get("name") or email or "Caregiver").strip() or "Caregiver"

    caregiver = session.exec(select(Caregiver).where(Caregiver.google_sub == sub)).first()
    if caregiver is None and email:
        caregiver = session.exec(select(Caregiver).where(Caregiver.email == email)).first()
        if caregiver is not None and caregiver.google_sub and caregiver.google_sub != sub:
            raise HTTPException(
                status_code=409,
                detail="This email is already linked to another Google account.",
            )
        if caregiver is not None:
            caregiver.google_sub = sub
    if caregiver is None:
        caregiver = Caregiver(name=name, email=email, google_sub=sub)
        session.add(caregiver)
    session.add(caregiver)
    session.commit()
    session.refresh(caregiver)
    return _session_for(caregiver)


def current_caregiver(
    session: Session = Depends(get_session),
    authorization: Optional[str] = Header(default=None),
) -> Caregiver:
    """Other routers can depend on this later. It is not applied anywhere yet."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in again.")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in again.")
    secret = get_settings().auth_secret
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        caregiver_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Sign in again.")
    caregiver = session.get(Caregiver, caregiver_id)
    if caregiver is None:
        raise HTTPException(status_code=401, detail="Sign in again.")
    return caregiver
