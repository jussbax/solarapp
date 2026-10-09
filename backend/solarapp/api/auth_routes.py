from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session

from .. import passkeys, twofactor
from ..auth import (
    clear_session,
    current_account,
    hash_password,
    new_generation,
    password_problem,
    require_account,
    set_session,
    sign_out_everywhere,
    touch_login,
    verify_credentials,
)
from ..config import Settings, get_settings
from ..db import get_session
from ..models import User
from ..schemas import LoginIn, PasskeyLoginIn, PasskeyRegisterIn, PasswordChangeIn, StepUpIn, TotpCodeIn
from .quick_routes import _bucket_ok, _hits, _lock as _hits_lock, client_ip

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


def _step_up(session: Session, request: Request, user: User, body: StepUpIn) -> None:
    """The person's password (and code) again, for actions a stolen cookie must not be able to take."""
    ip = client_ip(request)
    now = time.time()
    _check_throttle(ip, now)
    ok = verify_credentials(session, user.username, body.password) is not None
    if ok and twofactor.enabled(user) and not twofactor.verify(session, user, body.code):
        ok = False
    if not ok:
        _fail(ip, now)
        log.warning("step-up failed ip=%s user=%s", ip, user.username)
        raise HTTPException(status_code=403, detail="Confirm with your password" + (" and a fresh code" if twofactor.enabled(user) else "") + " to do this.")


OPTIONS_PER_HOUR = 60   # anonymous passkey challenges per address; a key sign-in needs one


def _options_allowed(request: Request) -> None:
    """The estimate limiter's dictionary under the estimate limiter's lock: one lock per shared structure."""
    key = "pk:" + client_ip(request)
    now = time.time()
    with _hits_lock:
        if not _bucket_ok(key, OPTIONS_PER_HOUR, now):
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later.", headers={"Retry-After": "600"})
        _hits.setdefault(key, deque()).append(now)


def _me(user: User, session: Session) -> dict:
    return {
        "username": user.username, "display_name": user.display_name or user.username, "role": user.role, "signed_in": True,
        "must_change_password": user.must_change_password, "two_factor": twofactor.enabled(user),
        "backup_codes_left": twofactor.remaining_backup_codes(user), "passkeys": bool(passkeys.keys_of(session, user)),
    }


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    ip = client_ip(request)
    now = time.time()
    _check_throttle(ip, now)
    user = verify_credentials(session, body.username, body.password)
    if user is None:
        _fail(ip, now)
        log.warning("login failed ip=%s user=%r", ip, body.username[:40])
        raise HTTPException(status_code=401, detail="Wrong username or password")
    if twofactor.enabled(user):
        if not body.code.strip():
            raise HTTPException(status_code=401, detail="Enter the 6-digit code from your authenticator app.")
        if not twofactor.verify(session, user, body.code):
            _fail(ip, now)
            log.warning("login code rejected ip=%s user=%s", ip, user.username)
            raise HTTPException(status_code=401, detail="That code is wrong or already used. Check the clock on your phone and try the next one.")
    _clear(ip)
    touch_login(session, user)
    log.info("login ok ip=%s user=%s method=password two_factor=%s", ip, user.username, twofactor.enabled(user))
    set_session(response, settings, user)
    return _me(user, session)


@router.post("/logout")
def logout(request: Request, response: Response, user: User | None = Depends(current_account)) -> dict:
    clear_session(response)
    if user:
        log.info("logout ip=%s user=%s", client_ip(request), user.username)
    return {"ok": True}


@router.post("/signout-everywhere")
def signout_everywhere(request: Request, response: Response, user: User = Depends(require_account), session: Session = Depends(get_session)) -> dict:
    """Every device of this person signed out at once, for a lost phone or laptop. The caller signs in again too."""
    sign_out_everywhere(session, user)
    clear_session(response)
    log.warning("sign-out everywhere ip=%s user=%s", client_ip(request), user.username)
    return {"ok": True}


@router.get("/me")
def me(user: User | None = Depends(current_account), session: Session = Depends(get_session)) -> dict:
    if user is None:
        # before sign-in: only whether a security key exists anywhere, so the login page can offer the button
        return {"username": None, "signed_in": False, "two_factor": False, "passkeys": passkeys.any_registered(session)}
    return _me(user, session)


# --- the person's own password and authenticator

@router.post("/password")
def change_password(body: PasswordChangeIn, request: Request, response: Response, user: User = Depends(require_account),
                    settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    """The current password (and code) prove it is the person; the new password ends every other session."""
    _step_up(session, request, user, StepUpIn(password=body.current_password, code=body.code))
    problem = password_problem(body.new_password, user.username)
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    if body.new_password == body.current_password:
        raise HTTPException(status_code=422, detail="Choose a password different from your current one.")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.session_generation = new_generation()
    session.add(user)
    session.commit()
    session.refresh(user)
    set_session(response, settings, user)   # this device stays signed in; every other one is out
    log.info("password changed ip=%s user=%s", client_ip(request), user.username)
    return _me(user, session)


@router.post("/totp/begin")
def totp_begin(body: StepUpIn, request: Request, user: User = Depends(require_account), settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    """Start the authenticator set-up: a new secret and its QR code; nothing changes until a code confirms it."""
    _step_up(session, request, user, body)
    secret, uri = twofactor.begin_setup(session, user, settings.company_name)
    return {"secret": secret, "uri": uri, "qr": twofactor.qr_data_url(uri)}


@router.post("/totp/confirm")
def totp_confirm(body: TotpCodeIn, request: Request, user: User = Depends(require_account), session: Session = Depends(get_session)) -> dict:
    try:
        codes = twofactor.confirm_setup(session, user, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    log.info("authenticator enabled ip=%s user=%s", client_ip(request), user.username)
    return {"ok": True, "backup_codes": codes}


@router.post("/totp/disable")
def totp_disable(body: StepUpIn, request: Request, user: User = Depends(require_account), session: Session = Depends(get_session)) -> dict:
    _step_up(session, request, user, body)
    twofactor.disable(session, user)
    log.warning("authenticator disabled ip=%s user=%s", client_ip(request), user.username)
    return {"ok": True}


# --- Signing in with a security key or passkey (no password, no code: the key and its PIN or fingerprint are the two factors) ---

@router.post("/passkey/options")
def passkey_login_options(request: Request, settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    _check_throttle(client_ip(request), time.time())
    _options_allowed(request)
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
        key, user = passkeys.authenticate(settings, request, session, body.challenge_id, body.credential)
    except passkeys.PasskeyError as exc:
        _fail(ip, now)
        log.warning("passkey rejected ip=%s reason=%s", ip, str(exc)[:160])
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _clear(ip)
    touch_login(session, user)
    log.info("login ok ip=%s user=%s method=passkey key=%r", ip, user.username, key.name)
    set_session(response, settings, user)
    return _me(user, session)


# --- Managing one's own keys, while signed in ---

@router.get("/passkeys")
def list_passkeys(user: User = Depends(require_account), session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    return [passkeys.summary(k) for k in passkeys.keys_of(session, user)]


@router.post("/passkeys/options")
def passkey_register_options(body: StepUpIn, request: Request, user: User = Depends(require_account), settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    _step_up(session, request, user, body)
    try:
        challenge_id, options = passkeys.registration_options(settings, request, session, user)
    except passkeys.PasskeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"challenge_id": challenge_id, "options": options}


@router.post("/passkeys", status_code=201)
def passkey_register(body: PasskeyRegisterIn, request: Request, user: User = Depends(require_account), settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> dict:
    """No second step-up: the challenge was issued to this person after one, is single-use and expires in minutes, so
    a one-time authenticator code is spent once for the whole set-up."""
    try:
        key = passkeys.register(settings, request, session, user, body.challenge_id, body.name, body.credential)
    except passkeys.PasskeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log.info("passkey added ip=%s user=%s key=%r", client_ip(request), user.username, key.name)
    return passkeys.summary(key)


@router.post("/passkeys/{key_id}/remove", status_code=204)
def passkey_delete(key_id: int, body: StepUpIn, request: Request, user: User = Depends(require_account), session: Session = Depends(get_session)) -> Response:
    _step_up(session, request, user, body)
    key = passkeys.remove(session, user, key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="No such key")
    log.info("passkey removed ip=%s user=%s key=%r", client_ip(request), user.username, key.name)
    return Response(status_code=204)
