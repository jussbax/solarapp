from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..auth import require_user
from ..config import Settings, get_settings
from ..db import get_session
from ..models import AppSetting
from ..schemas import SettingsIn, SettingsOut

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_user)])


def company_settings(session: Session, settings: Settings) -> dict:
    stored = {s.key: s.value for s in session.exec(select(AppSetting)).all()}
    return {
        "company_name": stored.get("company_name") or settings.company_name,
        "company_contact": stored.get("company_contact") if "company_contact" in stored else settings.company_contact,
    }


@router.get("", response_model=SettingsOut)
def read_settings(session: Session = Depends(get_session), settings: Settings = Depends(get_settings)) -> SettingsOut:
    return SettingsOut(**company_settings(session, settings))


@router.put("", response_model=SettingsOut)
def write_settings(body: SettingsIn, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)) -> SettingsOut:
    for key, value in body.model_dump(exclude_none=True).items():
        row = session.get(AppSetting, key) or AppSetting(key=key)
        row.value = value
        session.add(row)
    session.commit()
    return read_settings(session, settings)
