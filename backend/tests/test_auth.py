"""Caregiver phone OTP and Google login. Owner: Utkarsh."""

import os
from datetime import timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["BOLNA_MOCK"] = "true"
os.environ["OTP_MOCK"] = "true"
os.environ["AUTH_SECRET"] = "test-secret"
os.environ["GOOGLE_CLIENT_ID"] = "test-client.apps.googleusercontent.com"

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine, select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Caregiver, OtpCode, utcnow  # noqa: E402
from app.services.auth import _epoch, get_code_sender, verify_google_id_token  # noqa: E402
from app.services.phones import PHONE_ERROR  # noqa: E402

PHONE = "+919876543210"


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    get_code_sender().sent.clear()
    with TestClient(app) as test_client:
        test_client.engine = engine
        yield test_client
    app.dependency_overrides.clear()


def _otp_row(client, phone=PHONE):
    with Session(client.engine) as session:
        return session.exec(select(OtpCode).where(OtpCode.phone == phone)).one()


def _request(client, phone=PHONE):
    res = client.post("/api/auth/otp/request", json={"phone": phone})
    assert res.status_code == 200, res.text
    return res.json()["code"]


def test_otp_sends_a_hashed_code_and_verify_starts_a_session(client):
    code = _request(client, " +919876543210 ")
    assert len(code) == 6 and code.isdigit()
    row = _otp_row(client)
    assert row.code_hash != code
    assert code in get_code_sender().sent[-1][1]

    verified = client.post("/api/auth/otp/verify", json={"phone": PHONE, "code": code})
    assert verified.status_code == 200
    body = verified.json()
    assert body["caregiver"]["phone"] == PHONE
    assert body["caregiver"]["name"] == PHONE
    payload = jwt.decode(body["token"], "test-secret", algorithms=["HS256"])
    assert payload["sub"] == str(body["caregiver"]["id"])
    remaining = payload["exp"] - _epoch(utcnow())
    assert 6 * 24 * 3600 < remaining < 8 * 24 * 3600

    me = client.get("/api/auth/me", headers={"Authorization": "Bearer " + body["token"]})
    assert me.status_code == 200
    assert me.json()["id"] == body["caregiver"]["id"]

    again = client.post("/api/auth/otp/verify", json={"phone": PHONE, "code": code})
    assert again.status_code == 401


def test_otp_cooldown_expiry_and_attempt_limit(client):
    code = _request(client)
    cooled = client.post("/api/auth/otp/request", json={"phone": PHONE})
    assert cooled.status_code == 429
    assert len(get_code_sender().sent) == 1

    with Session(client.engine) as session:
        row = session.exec(select(OtpCode).where(OtpCode.phone == PHONE)).one()
        row.created_at = utcnow() - timedelta(seconds=31)
        session.add(row)
        session.commit()
    new_code = _request(client)
    assert new_code != code

    with Session(client.engine) as session:
        row = session.exec(select(OtpCode).where(OtpCode.phone == PHONE)).one()
        row.expires_at = utcnow() - timedelta(seconds=1)
        session.add(row)
        session.commit()
    expired = client.post("/api/auth/otp/verify", json={"phone": PHONE, "code": new_code})
    assert expired.status_code == 401
    assert "expired" in expired.json()["detail"]

    with Session(client.engine) as session:
        row = session.exec(select(OtpCode).where(OtpCode.phone == PHONE)).one()
        row.expires_at = utcnow() + timedelta(minutes=5)
        row.created_at = utcnow() - timedelta(seconds=31)
        session.add(row)
        session.commit()
    fresh = _request(client)
    wrong_code = "000000" if fresh != "000000" else "000001"
    for _ in range(5):
        wrong = client.post("/api/auth/otp/verify", json={"phone": PHONE, "code": wrong_code})
        assert wrong.status_code == 401
    locked = client.post("/api/auth/otp/verify", json={"phone": PHONE, "code": fresh})
    assert locked.status_code == 401
    assert "Too many attempts" in locked.json()["detail"]


def test_invalid_phone_is_rejected(client):
    res = client.post("/api/auth/otp/request", json={"phone": "123"})
    assert res.status_code == 422
    assert res.json()["detail"] == PHONE_ERROR


def test_otp_mock_off_hides_the_code(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "otp_mock", False)
    res = client.post("/api/auth/otp/request", json={"phone": PHONE})
    assert res.status_code == 200
    assert res.json()["code"] is None
    message = get_code_sender().sent[-1][1]
    code = message.split("code is ", 1)[1][:6]
    verified = client.post("/api/auth/otp/verify", json={"phone": PHONE, "code": code})
    assert verified.status_code == 200


def test_me_rejects_a_missing_or_bad_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_google_creates_and_links_by_email(client, monkeypatch):
    def fake(id_token):
        if id_token == "first":
            return {
                "sub": "google-sub-1",
                "email": "Asha@Example.com",
                "email_verified": True,
                "name": "Asha",
                "iss": "https://accounts.google.com",
            }
        return {
            "sub": "google-sub-1",
            "email": "asha@example.com",
            "email_verified": True,
            "name": "Asha",
            "iss": "accounts.google.com",
        }

    monkeypatch.setattr("app.services.auth.verify_google_id_token", fake)
    first = client.post("/api/auth/google", json={"id_token": "first"}).json()
    second = client.post("/api/auth/google", json={"id_token": "again"})
    assert second.status_code == 200
    assert second.json()["caregiver"]["id"] == first["caregiver"]["id"]
    assert second.json()["caregiver"]["email"] == "asha@example.com"

    with Session(client.engine) as session:
        other = Caregiver(name="Ravi", email="ravi@example.com", google_sub="other-sub")
        session.add(other)
        session.commit()

    def clash(id_token):
        return {
            "sub": "new-sub",
            "email": "ravi@example.com",
            "email_verified": True,
            "name": "Ravi Two",
            "iss": "https://accounts.google.com",
        }

    monkeypatch.setattr("app.services.auth.verify_google_id_token", clash)
    blocked = client.post("/api/auth/google", json={"id_token": "clash"})
    assert blocked.status_code == 409


def test_google_wrapper_checks_audience_and_issuer(monkeypatch):
    seen = {}

    def fake_verify(token, request, audience):
        seen["audience"] = audience
        return {"sub": "abc", "iss": "https://evil.example"}

    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", fake_verify)
    monkeypatch.setattr("google.auth.transport.requests.Request", lambda: None)
    with pytest.raises(Exception) as caught:
        verify_google_id_token("header.payload.sig")
    assert caught.value.status_code == 401
    assert seen["audience"] == "test-client.apps.googleusercontent.com"

    monkeypatch.setattr(get_settings(), "google_client_id", "")
    with pytest.raises(Exception) as missing:
        verify_google_id_token("header.payload.sig")
    assert missing.value.status_code == 503


def test_same_phone_returns_the_same_caregiver(client):
    code = _request(client)
    first = client.post("/api/auth/otp/verify", json={"phone": PHONE, "code": code}).json()
    with Session(client.engine) as session:
        row = session.exec(select(OtpCode).where(OtpCode.phone == PHONE)).first()
        assert row is None
    again_code = _request(client)
    second = client.post("/api/auth/otp/verify", json={"phone": PHONE, "code": again_code}).json()
    assert second["caregiver"]["id"] == first["caregiver"]["id"]
