"""Who is signed in: people with their own passwords, authenticators and keys.

Passwords are argon2id hashes in the database; nothing about a person lives in
.env except the first owner's bootstrap. The session cookie names the person
and carries a signature bound to their session generation, so a password
change, a sign-out everywhere or a deactivation ends every session at once.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlmodel import Session, select

from .config import Settings, get_settings
from .db import get_session
from .models import Passkey, User

COOKIE = "solarapp_session"
ROLES = ("owner", "engineer")
MIN_PASSWORD = 12
log = logging.getLogger("solarapp.audit")
_hasher = PasswordHasher()   # argon2id, the library's current defaults
# verified when the username does not exist, so a missing account takes as long as a wrong password
_DUMMY_HASH = _hasher.hash(secrets.token_hex(16))


# ---- passwords

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def check_password(stored_hash: str, password: str) -> bool:
    try:
        return bool(stored_hash) and _hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_problem(password: str, username: str = "") -> Optional[str]:
    """Why a new password is not acceptable, in plain words; None when it is."""
    if len(password) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters; a short sentence works well."
    if username and username.lower() in password.lower():
        return "The password must not contain the username."
    if len(set(password)) < 5:
        return "Use more different characters."
    return None


def temporary_password() -> str:
    """Shown once to the owner; the person changes it at their first sign-in."""
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4))


def new_generation() -> str:
    return secrets.token_hex(8)


def normalise_username(name: str) -> str:
    return (name or "").strip().lower()


# ---- sessions

def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="session")


def _signature(settings: Settings, user: User) -> str:
    """Bound to the person's generation and password hash, keyed with the server secret: a cookie holder
    learns nothing about the password, and any of the three changing ends the session."""
    material = f"{user.id}|{user.session_generation}|{user.password_hash[-24:]}".encode()
    return hmac.new(settings.secret_key.encode(), material, hashlib.sha256).hexdigest()[:16]


def set_session(response: Response, settings: Settings, user: User) -> None:
    token = _serializer(settings).dumps({"id": user.id, "u": user.username, "g": _signature(settings, user)})
    # Strict: the app signs in with same-origin fetch, never on a navigation, so Strict costs nothing and blocks same-site forgery.
    response.set_cookie(COOKIE, token, max_age=settings.session_hours * 3600, httponly=True, secure=settings.cookie_secure, samesite="strict", path="/")


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def load_account(request: Request, settings: Settings, session: Session) -> Optional[User]:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    try:
        data = _serializer(settings).loads(token, max_age=settings.session_hours * 3600)
    except (BadSignature, SignatureExpired):
        return None
    uid = data.get("id")
    if not isinstance(uid, int):
        return None
    user = session.get(User, uid)
    if user is None or not user.active:
        return None
    if not hmac.compare_digest(str(data.get("g", "")), _signature(settings, user)):
        return None
    return user


def current_account(request: Request, settings: Settings = Depends(get_settings), session: Session = Depends(get_session)) -> Optional[User]:
    return load_account(request, settings, session)


def current_user(account: Optional[User] = Depends(current_account)) -> Optional[str]:
    """The username of the signed-in person, or None (for log lines and the old call sites)."""
    return account.username if account else None


def require_account(account: Optional[User] = Depends(current_account)) -> User:
    if account is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return account


def require_user(account: User = Depends(require_account)) -> str:
    """A signed-in person who has finished setting up: a temporary password must be changed first."""
    if account.must_change_password:
        raise HTTPException(status_code=403, detail="Change your temporary password first (under Your account).")
    return account.username


def require_owner(account: User = Depends(require_account)) -> User:
    if account.must_change_password:
        raise HTTPException(status_code=403, detail="Change your temporary password first (under Your account).")
    if account.role != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can do this.")
    return account


# ---- sign-in

def verify_credentials(session: Session, username: str, password: str) -> Optional[User]:
    """The active person with that username and password, or None. A missing account costs the same time as a wrong password."""
    user = session.exec(select(User).where(User.username == normalise_username(username))).first()
    if user is None:
        check_password(_DUMMY_HASH, password or "")
        return None
    if not check_password(user.password_hash, password or ""):
        return None
    return user if user.active else None


def touch_login(session: Session, user: User) -> None:
    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()


def sign_out_everywhere(session: Session, user: User) -> None:
    """Every session of this person ends: the next request needs a fresh sign-in."""
    user.session_generation = new_generation()
    session.add(user)
    session.commit()


def owners(session: Session) -> list[User]:
    return list(session.exec(select(User).where(User.role == "owner", User.active == True)).all())  # noqa: E712


# ---- the first owner

def bootstrap_owner(session: Session, settings: Settings) -> Optional[User]:
    """With no accounts yet, the owner comes from .env (the only time the .env password is used). The authenticator
    set up with the old file and the keys registered before accounts existed move to that owner. Idempotent."""
    created = None
    if session.exec(select(User)).first() is None:
        if not settings.app_password:
            log.error("bootstrap: no accounts and no SOLARAPP_APP_PASSWORD in .env; nobody can sign in until an owner exists "
                      "(set the variable and restart, or run: python -m solarapp.users create <username> --role owner)")
            return None
        user = User(username=normalise_username(settings.app_username) or "admin", display_name=settings.app_username, role="owner",
                    password_hash=hash_password(settings.app_password), session_generation=new_generation())
        legacy = settings.data_dir / "twofactor.json"
        if legacy.is_file():
            try:
                data = json.loads(legacy.read_text())
                user.totp_secret = str(data.get("secret") or "")
                user.totp_backup = list(data.get("backup") or [])
                legacy.rename(legacy.with_suffix(".json.migrated"))
            except (OSError, ValueError):
                log.warning("bootstrap: the old two-factor file could not be read; set the authenticator up again under Your account")
        session.add(user)
        session.commit()
        session.refresh(user)
        created = user
        log.info("bootstrap: owner account %r created from .env%s", user.username, " with the existing authenticator" if user.totp_secret else "")
    first_owner = next(iter(owners(session)), None)
    if first_owner is not None:
        orphans = session.exec(select(Passkey).where(Passkey.user_id == None)).all()  # noqa: E711
        for k in orphans:
            k.user_id = first_owner.id
            session.add(k)
        if orphans:
            session.commit()
            log.info("bootstrap: %s security key(s) attached to %r", len(orphans), first_owner.username)
    return created
