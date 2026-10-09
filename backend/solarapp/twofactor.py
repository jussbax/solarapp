"""Each person's second factor: a code from an authenticator app, plus one-time backup codes.

Set up in the browser under Your account: the server makes a secret and a QR
code, the person scans it and confirms with one code, then the eight backup
codes are shown once. The secret and the hashed backup codes live on the
person's row. Codes work offline, so the login works on a roof with no signal.

    python -m solarapp.users reset-authenticator <username>   # a lost phone: switches it off so it can be set up again
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import secrets
import sys
import threading
import time

import pyotp
from sqlmodel import Session

from .models import User

BACKUP_CODES = 8
_lock = threading.Lock()


def _hash(code: str) -> str:
    return hashlib.sha256(code.replace("-", "").replace(" ", "").lower().encode()).hexdigest()


def enabled(user: User) -> bool:
    return bool(user.totp_secret)


def remaining_backup_codes(user: User) -> int:
    return len(user.totp_backup or [])


def provisioning_uri(secret: str, user: User, issuer: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=user.username, issuer_name=issuer or "Solar back office")


def qr_data_url(uri: str) -> str:
    """The QR code as a PNG data URL for the browser (nothing is written to disk)."""
    import qrcode

    q = qrcode.QRCode(border=1)
    q.add_data(uri)
    q.make(fit=True)
    buf = io.BytesIO()
    q.make_image().save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def begin_setup(session: Session, user: User, issuer: str) -> tuple[str, str]:
    """A new pending secret for this person; nothing changes for sign-in until it is confirmed. Returns (secret, uri)."""
    secret = pyotp.random_base32()
    user.totp_pending_secret = secret
    session.add(user)
    session.commit()
    return secret, provisioning_uri(secret, user, issuer)


def confirm_setup(session: Session, user: User, code: str) -> list[str]:
    """The first code from the app proves the scan worked; then the authenticator is on and the backup codes are
    returned once, in plain text, for the person to keep. Raises ValueError when the code does not match."""
    secret = user.totp_pending_secret
    if not secret:
        raise ValueError("Start the set-up first.")
    if not pyotp.TOTP(secret).verify((code or "").strip(), valid_window=1):
        raise ValueError("That code does not match. Scan the QR code again and enter the current code.")
    codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(BACKUP_CODES)]
    user.totp_secret = secret
    user.totp_pending_secret = ""
    user.totp_backup = [_hash(c) for c in codes]
    user.totp_last_step = int(time.time() // 30)
    session.add(user)
    session.commit()
    return codes


def disable(session: Session, user: User) -> None:
    user.totp_secret = ""
    user.totp_pending_secret = ""
    user.totp_backup = []
    user.totp_last_step = 0
    session.add(user)
    session.commit()


def verify(session: Session, user: User, code: str) -> bool:
    """True for a fresh authenticator code or an unused backup code. A backup code is consumed; a code cannot be
    replayed within its window. Check, consume and write back happen under one lock."""
    code = (code or "").strip()
    if not code or not user.totp_secret:
        return False
    with _lock:
        session.refresh(user)
        if not user.totp_secret:
            return False
        totp = pyotp.TOTP(user.totp_secret)
        if code.isdigit() and len(code) == 6:
            now = time.time()
            for drift in (0, -1, 1):  # a phone clock up to 30 s off
                step = int(now // 30) + drift
                if hmac.compare_digest(totp.at(step * 30), code):
                    if (user.totp_last_step or 0) >= step:
                        return False  # already used this window
                    user.totp_last_step = step
                    session.add(user)
                    session.commit()
                    return True
            return False
        h = _hash(code)
        hashes = list(user.totp_backup or [])
        for i, stored in enumerate(hashes):
            if hmac.compare_digest(stored, h):
                del hashes[i]
                user.totp_backup = hashes
                session.add(user)
                session.commit()
                return True
    return False


def main() -> int:
    print("The authenticator is set up per person in the browser, under Settings > Your account.")
    print("For a lost phone: python -m solarapp.users reset-authenticator <username>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
