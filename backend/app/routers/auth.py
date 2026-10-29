"""Caregiver login. Owner: Utkarsh."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.models import Caregiver
from app.schemas import (
    AuthSession,
    CaregiverRead,
    GoogleAuthRequest,
    OtpRequest,
    OtpRequestResponse,
    OtpVerify,
)
from app.services.auth import current_caregiver, login_with_google, request_phone_otp, verify_phone_otp

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login():
    raise HTTPException(status_code=501, detail="Auth not implemented yet")


@router.post("/otp/request", response_model=OtpRequestResponse)
def otp_request(body: OtpRequest, session: Session = Depends(get_session)):
    return request_phone_otp(session, body.phone)


@router.post("/otp/verify", response_model=AuthSession)
def otp_verify(body: OtpVerify, session: Session = Depends(get_session)):
    return verify_phone_otp(session, body.phone, body.code)


@router.post("/google", response_model=AuthSession)
def google_login(body: GoogleAuthRequest, session: Session = Depends(get_session)):
    return login_with_google(session, body.id_token)


@router.get("/me", response_model=CaregiverRead)
def me(caregiver: Caregiver = Depends(current_caregiver)):
    return caregiver
