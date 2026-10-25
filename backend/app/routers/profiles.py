from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Elder, TrustedContact
from app.schemas import ContactCreate, ContactRead, ElderCreate, ElderRead, ElderUpdate

router = APIRouter(prefix="/api/elders", tags=["profiles"])


def _get_elder(session: Session, elder_id: int) -> Elder:
    elder = session.get(Elder, elder_id)
    if not elder:
        raise HTTPException(status_code=404, detail="Elder not found")
    return elder


@router.get("", response_model=List[ElderRead])
def list_elders(session: Session = Depends(get_session)):
    return session.exec(select(Elder)).all()


@router.post("", response_model=ElderRead, status_code=201)
def create_elder(body: ElderCreate, session: Session = Depends(get_session)):
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
    elder.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.add(elder)
    session.commit()
    session.refresh(elder)
    return elder


@router.delete("/{elder_id}", status_code=204)
def delete_elder(elder_id: int, session: Session = Depends(get_session)):
    session.delete(_get_elder(session, elder_id))
    session.commit()


@router.get("/{elder_id}/contacts", response_model=List[ContactRead])
def list_contacts(elder_id: int, session: Session = Depends(get_session)):
    _get_elder(session, elder_id)
    return session.exec(select(TrustedContact).where(TrustedContact.elder_id == elder_id)).all()


@router.post("/{elder_id}/contacts", response_model=ContactRead, status_code=201)
def add_contact(elder_id: int, body: ContactCreate, session: Session = Depends(get_session)):
    _get_elder(session, elder_id)
    contact = TrustedContact.model_validate(body, update={"elder_id": elder_id})
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact
