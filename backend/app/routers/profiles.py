"""Elder and trusted-contact routes. Owner: Utkarsh."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Elder, Task, TrustedContact
from app.schemas import ContactCreate, ContactRead, ElderCreate, ElderRead, ElderUpdate
from app.services.phones import PHONE_ERROR, normalize_phone

router = APIRouter(prefix="/api/elders", tags=["profiles"])

# PATCH fields until a ContactUpdate schema exists. Same names as ContactCreate.
_CONTACT_FIELDS = set(ContactCreate.model_fields)


def _get_elder(session: Session, elder_id: int) -> Elder:
    elder = session.get(Elder, elder_id)
    if not elder:
        raise HTTPException(status_code=404, detail="Elder not found")
    return elder


def _get_contact(session: Session, elder_id: int, contact_id: int) -> TrustedContact:
    _get_elder(session, elder_id)
    contact = session.get(TrustedContact, contact_id)
    if not contact or contact.elder_id != elder_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


def _require_phone(phone: str) -> str:
    try:
        return normalize_phone(phone)
    except ValueError:
        raise HTTPException(status_code=422, detail=PHONE_ERROR)


def _contact_updates(body: Dict[str, Any]) -> Dict[str, Any]:
    unknown = sorted(set(body) - _CONTACT_FIELDS)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail="Unknown contact field: {names}".format(names=", ".join(unknown)),
        )
    updates: Dict[str, Any] = {}
    for key, value in body.items():
        if key in ("name", "relation") and value is not None and not isinstance(value, str):
            raise HTTPException(status_code=422, detail="{field} must be a string".format(field=key))
        if key == "name" and value is None:
            raise HTTPException(status_code=422, detail="name must be a string")
        if key == "notify_on_missed" and not isinstance(value, bool):
            raise HTTPException(status_code=422, detail="notify_on_missed must be true or false")
        if key == "phone":
            updates[key] = _require_phone(value)
        else:
            updates[key] = value
    return updates


@router.get("", response_model=List[ElderRead])
def list_elders(session: Session = Depends(get_session)):
    return session.exec(select(Elder)).all()


@router.post("", response_model=ElderRead, status_code=201)
def create_elder(body: ElderCreate, session: Session = Depends(get_session)):
    body.phone = _require_phone(body.phone)
    elder = Elder.model_validate(body)
    session.add(elder)
    session.commit()
    session.refresh(elder)
    return elder


@router.get("/{elder_id}", response_model=ElderRead)
def get_elder(elder_id: int, session: Session = Depends(get_session)):
    return _get_elder(session, elder_id)


@router.patch("/{elder_id}", response_model=ElderRead)
def update_elder(elder_id: int, body: ElderUpdate, session: Session = Depends(get_session)):
    elder = _get_elder(session, elder_id)
    changes = body.model_dump(exclude_unset=True)
    if "phone" in changes:
        changes["phone"] = _require_phone(changes["phone"])
    elder.sqlmodel_update(changes)
    session.add(elder)
    session.commit()
    session.refresh(elder)
    return elder


@router.delete("/{elder_id}", status_code=204)
def delete_elder(elder_id: int, session: Session = Depends(get_session)):
    elder = _get_elder(session, elder_id)
    has_tasks = session.exec(select(Task.id).where(Task.elder_id == elder_id)).first()
    if has_tasks is not None:
        raise HTTPException(
            status_code=409,
            detail="This elder still has tasks. Remove the tasks before deleting the elder.",
        )
    contacts = session.exec(select(TrustedContact).where(TrustedContact.elder_id == elder_id)).all()
    for contact in contacts:
        session.delete(contact)
    session.delete(elder)
    session.commit()


@router.get("/{elder_id}/contacts", response_model=List[ContactRead])
def list_contacts(elder_id: int, session: Session = Depends(get_session)):
    _get_elder(session, elder_id)
    return session.exec(select(TrustedContact).where(TrustedContact.elder_id == elder_id)).all()


@router.post("/{elder_id}/contacts", response_model=ContactRead, status_code=201)
def add_contact(elder_id: int, body: ContactCreate, session: Session = Depends(get_session)):
    _get_elder(session, elder_id)
    body.phone = _require_phone(body.phone)
    contact = TrustedContact.model_validate(body, update={"elder_id": elder_id})
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact


@router.get("/{elder_id}/contacts/{contact_id}", response_model=ContactRead)
def get_contact(elder_id: int, contact_id: int, session: Session = Depends(get_session)):
    return _get_contact(session, elder_id, contact_id)


@router.patch("/{elder_id}/contacts/{contact_id}", response_model=ContactRead)
def update_contact(
    elder_id: int,
    contact_id: int,
    body: Dict[str, Any],
    session: Session = Depends(get_session),
):
    contact = _get_contact(session, elder_id, contact_id)
    contact.sqlmodel_update(_contact_updates(body))
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact


@router.delete("/{elder_id}/contacts/{contact_id}", status_code=204)
def delete_contact(elder_id: int, contact_id: int, session: Session = Depends(get_session)):
    contact = _get_contact(session, elder_id, contact_id)
    session.delete(contact)
    session.commit()
