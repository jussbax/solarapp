from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session

from .. import passkeys, twofactor
from ..auth import clear_session, current_user, require_user, set_session, verify_credentials
from ..config import Settings, get_settings
from ..db import get_session
from ..schemas import LoginIn, PasskeyLoginIn, PasskeyRegisterIn
from .quick_routes import client_ip

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = logging.getLogger("solarapp.audit")

# Login throttle per address: a handful of wrong attempts, then a quarter hour off. Shared by every way in.
WINDOW_S, MAX_FAILS = 900, 10
_fails: dict[str, deque] = {}
_lock = threading.Lock()


def _check_throttle(ip: str, now: float) -> None:
    with _lock:
        q = _fails.setdefault(ip, deque())
        while q and now - q[0] > WINDOW_S:
            q.popleft()
        if len(q) >= MAX_FAILS:
            log.warning("login throttled ip=%s", ip)
            raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.", headers={"Retry-After": str(WINDOW_S)})


def _fail(ip: str, now: float) -> None:
    with _lock:
        _fails.setdefault(ip, deque()).append(now)
        if len(_fails) > 10_000:  # a flood of addresses must not grow memory
            _fails.clear()


def _clear(ip: str) -> None:
    with _lock:
        _fails.pop(ip, None)


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, settings: Settings = Depends(get_settings)) -> dict:
    ip = client_ip(request)
    now = time.time()
    _check_throttle(ip, now)
    if not verify_credentials(settings, body.username, body.password):
        _fail(ip, now)
        log.warning("login failed ip=%s user=%r", ip, body.username[:40])
        raise HTTPException(status_code=401, detail="Wrong username or password")
    if twofactor.enabled(settings):
        if not body.code.strip():
            raise HTTPException(status_code=401, detail="Enter the 6-digit code from your authenticator app.")
        if not twofactor.verify(settings, body.code):
            _fail(ip, now)
            log.warning("login code rejected ip=%s user=%s", ip, body.username[:40])
            raise HTTPException(status_code=401, detail="That code is wrong or already used. Check the clock on your phone and try the next one.")
    _clear(ip)
    log.info("login ok ip=%s user=%s method=password two_factor=%s", ip, body.username, twofactor.enabled(settings))
    set_session(response, settings, body.username)
    return {"username": body.username}


@router.post("/logout")
def logout(request: Request, response: Response, user: str | None = Depends(current_user)) -> dict:
    clear_session(response)
    if user:
        log.info("logout ip=%s user=%s", client_ip(request), user)
    return {"ok": True}


@router.get("/me")
def me(user: str | None = Depends(current_user), settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    return {"username": user, "signed_in": user is not None, "two_factor": twofactor.enabled(settings), "passkeys": passkeys.count(session) > 0}


# --- Signing in with a security key or passkey (no password, no code: the key and its PIN or fingerprint are the two factors) ---

@router.post("/passkey/options")
def passkey_login_options(request: Request, settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    _check_throttle(client_ip(request), time.time())
    try:
        challenge_id, options = passkeys.authentication_options(settings, request, session)
    except passkeys.PasskeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"challenge_id": challenge_id, "options": options}


@router.post("/passkey/login")
def passkey_login(body: PasskeyLoginIn, request: Request, response: Response, settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    ip = client_ip(request)
    now = time.time()
    _check_throttle(ip, now)
    try:
        key = passkeys.authenticate(settings, request, session, body.challenge_id, body.credential)
    except passkeys.PasskeyError as exc:
        _fail(ip, now)
        log.warning("passkey rejected ip=%s reason=%s", ip, str(exc)[:160])
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _clear(ip)
    log.info("login ok ip=%s user=%s method=passkey key=%r", ip, settings.app_username, key.name)
    set_session(response, settings, settings.app_username)
    return {"username": settings.app_username}


# --- Managing keys, while signed in ---

@router.get("/passkeys")
def list_passkeys(user: str = Depends(require_user), session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    from sqlmodel import select
    from ..models import Passkey
    return [passkeys.summary(k) for k in session.exec(select(Passkey).order_by(Passkey.created_at)).all()]


@router.post("/passkeys/options")
def passkey_register_options(request: Request, user: str = Depends(require_user), settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    try:
        challenge_id, options = passkeys.registration_options(settings, request, session)
    except passkeys.PasskeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"challenge_id": challenge_id, "options": options}


@router.post("/passkeys", status_code=201)
def passkey_register(body: PasskeyRegisterIn, request: Request, user: str = Depends(require_user), settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    try:
        key = passkeys.register(settings, request, session, body.challenge_id, body.name, body.credential)
    except passkeys.PasskeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log.info("passkey added ip=%s user=%s key=%r", client_ip(request), user, key.name)
    return passkeys.summary(key)


@router.delete("/passkeys/{key_id}", status_code=204)
def passkey_delete(key_id: int, request: Request, user: str = Depends(require_user), session: Session = Depends(get_session)) -> Response:
    key = passkeys.remove(session, key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="No such key")
    log.info("passkey removed ip=%s user=%s key=%r", client_ip(request), user, key.name)
    return Response(status_code=204)
