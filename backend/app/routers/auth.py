"""Auth placeholder. Owner: Utkarsh. TODO: OTP or Google login for caregivers."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login():
    raise HTTPException(status_code=501, detail="Auth not implemented yet")
