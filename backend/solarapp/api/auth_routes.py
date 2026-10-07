from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from ..auth import clear_session, current_user, set_session, verify_credentials
from ..config import Settings, get_settings
from ..schemas import LoginIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginIn, response: Response, settings: Settings = Depends(get_settings)) -> dict:
    if not verify_credentials(settings, body.username, body.password):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    set_session(response, settings, body.username)
    return {"username": body.username}


@router.post("/logout")
def logout(response: Response) -> dict:
    clear_session(response)
    return {"ok": True}


@router.get("/me")
def me(user: str | None = Depends(current_user)) -> dict:
    return {"username": user, "signed_in": user is not None}
