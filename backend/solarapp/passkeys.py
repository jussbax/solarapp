"""Passkeys: a hardware security key or a phone passkey signs the owner in on its own.

A key proves possession, and its PIN or fingerprint proves it is the owner, so
one touch replaces the password and the authenticator code. The browser only
releases a signature for the exact hostname the key was registered on, so a
look-alike site gets nothing. Keys are added from Settings while signed in.
"""
from __future__ import annotations

import hashlib
import secrets
import threading
import time
from typing import Any, Optional

from fastapi import Request
from sqlmodel import Session, select
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import options_to_json_dict
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .config import Settings
from .models import Passkey, utcnow

CHALLENGE_TTL_S = 300
MAX_CHALLENGES = 500
_challenges: dict[str, tuple[bytes, str, float]] = {}   # id -> (challenge, kind, expires)
_lock = threading.Lock()


class PasskeyError(ValueError):
    """A plain-words reason the key was not accepted."""


def relying_party(settings: Settings, request: Request) -> tuple[str, list[str]]:
    """The hostname the key is bound to and the page origins the browser may report."""
    raw = (request.headers.get("host") or "").strip().rstrip(".").lower()
    host = raw.split(":")[0]
    if not host:
        raise PasskeyError("No hostname on this request.")
    origins = [f"https://{raw}"]
    if not settings.cookie_secure:
        origins.append(f"http://{raw}")
    return host, origins


def _remember(challenge: bytes, kind: str) -> str:
    cid = secrets.token_urlsafe(24)
    now = time.monotonic()
    with _lock:
        for k in [k for k, (_, _, exp) in _challenges.items() if exp < now]:
            del _challenges[k]
        while len(_challenges) >= MAX_CHALLENGES:  # a flood evicts the oldest, not everyone
            del _challenges[next(iter(_challenges))]
        _challenges[cid] = (challenge, kind, now + CHALLENGE_TTL_S)
    return cid


def _take(cid: str, kind: str) -> bytes:
    with _lock:
        item = _challenges.pop(cid or "", None)
    if item is None or item[1] != kind or item[2] < time.monotonic():
        raise PasskeyError("This sign-in attempt expired. Try again.")
    return item[0]


def _user_handle(username: str) -> bytes:
    """A stable, non-personal id for the one account, as the WebAuthn user handle."""
    return hashlib.sha256(b"solarapp-user:" + username.encode()).digest()[:16]


def _descriptors(keys: list[Passkey]) -> list[PublicKeyCredentialDescriptor]:
    return [PublicKeyCredentialDescriptor(id=k.credential_id) for k in keys]


def registration_options(settings: Settings, request: Request, session: Session) -> tuple[str, dict[str, Any]]:
    rp_id, _ = relying_party(settings, request)
    existing = session.exec(select(Passkey)).all()
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=settings.company_name or "Solar back office",
        user_id=_user_handle(settings.app_username),
        user_name=settings.app_username,
        user_display_name=settings.app_username,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=_descriptors(existing),
    )
    return _remember(options.challenge, "register"), options_to_json_dict(options)


def register(settings: Settings, request: Request, session: Session, challenge_id: str, name: str, credential: dict[str, Any]) -> Passkey:
    rp_id, origins = relying_party(settings, request)
    challenge = _take(challenge_id, "register")
    try:
        verified = verify_registration_response(
            credential=credential, expected_challenge=challenge, expected_rp_id=rp_id, expected_origin=origins, require_user_verification=True,
        )
    except (WebAuthnException, ValueError, KeyError, TypeError) as exc:
        raise PasskeyError(f"The key could not be registered: {exc}") from exc
    if session.exec(select(Passkey).where(Passkey.credential_id == verified.credential_id)).first():
        raise PasskeyError("This key is already registered.")
    transports = [t.value if hasattr(t, "value") else str(t) for t in ((credential.get("response") or {}).get("transports") or [])]
    key = Passkey(
        name=(name or "").strip()[:60] or "Security key",
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        transports=",".join(transports)[:80],
        aaguid=verified.aaguid or "",
        backed_up=bool(verified.credential_backed_up),
    )
    session.add(key)
    session.commit()
    session.refresh(key)
    return key


def authentication_options(settings: Settings, request: Request, session: Session) -> tuple[str, dict[str, Any]]:
    rp_id, _ = relying_party(settings, request)
    keys = session.exec(select(Passkey)).all()
    if not keys:
        raise PasskeyError("No security key is registered yet.")
    options = generate_authentication_options(rp_id=rp_id, allow_credentials=_descriptors(keys), user_verification=UserVerificationRequirement.REQUIRED)
    return _remember(options.challenge, "login"), options_to_json_dict(options)


def authenticate(settings: Settings, request: Request, session: Session, challenge_id: str, credential: dict[str, Any]) -> Passkey:
    """The key that signed this challenge, with its counter and last use updated. Raises PasskeyError otherwise."""
    rp_id, origins = relying_party(settings, request)
    challenge = _take(challenge_id, "login")
    try:
        from webauthn.helpers import base64url_to_bytes
        raw_id = base64url_to_bytes(credential.get("rawId") or credential.get("id") or "")
    except (ValueError, TypeError) as exc:
        raise PasskeyError("That key is not registered.") from exc
    key = session.exec(select(Passkey).where(Passkey.credential_id == raw_id)).first()
    if key is None:
        raise PasskeyError("That key is not registered.")
    try:
        verified = verify_authentication_response(
            credential=credential, expected_challenge=challenge, expected_rp_id=rp_id, expected_origin=origins,
            credential_public_key=key.public_key, credential_current_sign_count=key.sign_count, require_user_verification=True,
        )
    except (WebAuthnException, ValueError, KeyError, TypeError) as exc:
        raise PasskeyError(f"The key was not accepted: {exc}") from exc
    key.sign_count = verified.new_sign_count
    key.last_used_at = utcnow()
    session.add(key)
    session.commit()
    session.refresh(key)
    return key


def summary(key: Passkey) -> dict[str, Any]:
    return {
        "id": key.id, "name": key.name, "transports": [t for t in key.transports.split(",") if t], "backed_up": key.backed_up,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
    }


def count(session: Session) -> int:
    return len(session.exec(select(Passkey.id)).all())


def remove(session: Session, key_id: int) -> Optional[Passkey]:
    key = session.get(Passkey, key_id)
    if key is None:
        return None
    session.delete(key)
    session.commit()
    return key
