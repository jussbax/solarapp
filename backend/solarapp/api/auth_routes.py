from __future__ import annotations

import logging
import threading
import time
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..auth import clear_session, current_user, set_session, verify_credentials
from ..config import Settings, get_settings
from ..schemas import LoginIn
from .quick_routes import client_ip

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = logging.getLogger("solarapp.audit")

# Login throttle per address: a handful of wrong passwords, then a quarter hour off. Cloudflare Access sits in front in production.
WINDOW_S, MAX_FAILS = 900, 10
_fails: dict[str, deque] = {}
_lock = threading.Lock()


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, settings: Settings = Depends(get_settings)) -> dict:
    ip = client_ip(request)
    now = time.time()
    with _lock:
        q = _fails.setdefault(ip, deque())
        while q and now - q[0] > WINDOW_S:
            q.popleft()
        if len(q) >= MAX_FAILS:
            log.warning("login throttled ip=%s", ip)
            raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.", headers={"Retry-After": str(WINDOW_S)})
    if not verify_credentials(settings, body.username, body.password):
        with _lock:
            _fails.setdefault(ip, deque()).append(now)
            if len(_fails) > 10_000:  # a flood of addresses must not grow memory
                _fails.clear()
        log.warning("login failed ip=%s user=%r", ip, body.username[:40])
        raise HTTPException(status_code=401, detail="Wrong username or password")
    with _lock:
        _fails.pop(ip, None)
    log.info("login ok ip=%s user=%s", ip, body.username)
    set_session(response, settings, body.username)
    return {"username": body.username}


@router.post("/logout")
def logout(request: Request, response: Response, user: str | None = Depends(current_user)) -> dict:
    clear_session(response)
    if user:
        log.info("logout ip=%s user=%s", client_ip(request), user)
    return {"ok": True}


@router.get("/me")
def me(user: str | None = Depends(current_user)) -> dict:
    return {"username": user, "signed_in": user is not None}
