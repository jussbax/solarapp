from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import Settings, get_settings

COOKIE = "solarapp_session"


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="session")


NONCE_FILE = "session.key"


def _nonce(settings: Settings, rotate: bool = False) -> str:
    """A random value on the data volume; new on first use or when every session must end."""
    path = settings.data_dir / NONCE_FILE
    if not rotate and path.is_file():
        try:
            value = path.read_text().strip()
            if value:
                return value
        except OSError:
            pass
    value = secrets.token_hex(16)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return value


def _generation(settings: Settings) -> str:
    """Changes with the password or when sessions are revoked. Keyed with the secret, so a cookie
    holder cannot test password guesses against it offline."""
    material = settings.app_password.encode() + b"|" + _nonce(settings).encode()
    return hmac.new(settings.secret_key.encode(), material, hashlib.sha256).hexdigest()[:16]


def sign_out_everywhere(settings: Settings) -> None:
    """Every signed-in device, this one included, is signed out: the next request needs a fresh login."""
    _nonce(settings, rotate=True)


def verify_credentials(settings: Settings, username: str, password: str) -> bool:
    return hmac.compare_digest(username.encode(), settings.app_username.encode()) and hmac.compare_digest(
        password.encode(), settings.app_password.encode()
    )


def set_session(response: Response, settings: Settings, username: str) -> None:
    token = _serializer(settings).dumps({"u": username, "g": _generation(settings)})
    # Strict: the app signs in with same-origin fetch, never on a navigation, so Strict costs nothing and blocks same-site forgery.
    response.set_cookie(COOKIE, token, max_age=settings.session_hours * 3600, httponly=True, secure=settings.cookie_secure, samesite="strict", path="/")


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
    if data.get("g") != _generation(settings):
        return None
    return data.get("u")


def require_user(user: Optional[str] = Depends(current_user)) -> str:
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user
