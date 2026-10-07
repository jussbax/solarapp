from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import Settings, get_settings

COOKIE = "solarapp_session"


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="session")


def verify_credentials(settings: Settings, username: str, password: str) -> bool:
    return hmac.compare_digest(username.encode(), settings.app_username.encode()) and hmac.compare_digest(
        password.encode(), settings.app_password.encode()
    )


def set_session(response: Response, settings: Settings, username: str) -> None:
    token = _serializer(settings).dumps({"u": username})
    response.set_cookie(COOKIE, token, max_age=settings.session_hours * 3600, httponly=True, samesite="lax", path="/")


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def current_user(request: Request, settings: Settings = Depends(get_settings)) -> Optional[str]:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    try:
        data = _serializer(settings).loads(token, max_age=settings.session_hours * 3600)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("u")


def require_user(user: Optional[str] = Depends(current_user)) -> str:
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user
