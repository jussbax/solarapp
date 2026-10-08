from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..auth import require_user
from ..config import Settings, get_settings
from ..db import get_session
from ..models import AppSetting
from ..profile import PROFILE_KEYS, company_profile
from ..schemas import SettingsIn, SettingsOut

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_user)])


def company_settings(session: Session, settings: Settings) -> dict:
    """Company profile for documents: name, contact line and the public-profile fields."""
    return company_profile(session, settings)


@router.get("", response_model=SettingsOut)
def read_settings(session: Session = Depends(get_session), settings: Settings = Depends(get_settings)) -> SettingsOut:
    return SettingsOut(**company_settings(session, settings))


@router.put("", response_model=SettingsOut)
def write_settings(body: SettingsIn, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)) -> SettingsOut:
    for key, value in body.model_dump(exclude_none=True).items():
        if key not in PROFILE_KEYS or not isinstance(value, str):
            continue
        row = session.get(AppSetting, key) or AppSetting(key=key)
        row.value = value.strip()
        session.add(row)
    session.commit()
    return read_settings(session, settings)
