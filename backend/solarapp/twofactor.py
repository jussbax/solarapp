"""Second factor for the back office: a code from an authenticator app, plus one-time backup codes.

    python -m solarapp.twofactor setup     # creates the secret, shows the QR code and the backup codes once
    python -m solarapp.twofactor status
    python -m solarapp.twofactor disable

The secret and the hashed backup codes live in <data_dir>/twofactor.json (mode 0600),
never in .env. Codes work offline, so the login works on a roof with no signal.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import pyotp

from .config import Settings, get_settings

FILE = "twofactor.json"
BACKUP_CODES = 8
_lock = threading.Lock()
_last_step: dict[str, int] = {}  # secret -> last accepted 30 s step, so a code cannot be replayed within its window


def _path(settings: Settings) -> Path:
    return settings.data_dir / FILE


def _hash(code: str) -> str:
    return hashlib.sha256(code.replace("-", "").replace(" ", "").lower().encode()).hexdigest()


def load(settings: Settings) -> Optional[dict]:
    """The stored second factor, or one built from SOLARAPP_TOTP_SECRET, or None when off."""
    p = _path(settings)
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except (OSError, ValueError):
            return None
    if settings.totp_secret:
        return {"secret": settings.totp_secret.strip(), "backup": []}
    return None


def enabled(settings: Settings) -> bool:
    return load(settings) is not None


def setup(settings: Settings, account: str = "") -> tuple[str, list[str], str]:
    """Create a new secret and backup codes. Returns (secret, plain backup codes, otpauth URI)."""
    secret = pyotp.random_base32()
    codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(BACKUP_CODES)]
    data = {"secret": secret, "backup": [_hash(c) for c in codes], "created_at": time.strftime("%Y-%m-%d")}
    p = _path(settings)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))
    p.chmod(0o600)
    uri = pyotp.TOTP(secret).provisioning_uri(name=account or settings.app_username, issuer_name=settings.company_name or "Solar back office")
    return secret, codes, uri


def disable(settings: Settings) -> bool:
    p = _path(settings)
    if p.is_file():
        p.unlink()
        return True
    return False


def verify(settings: Settings, code: str) -> bool:
    """True for a fresh authenticator code or an unused backup code. A backup code is consumed."""
    data = load(settings)
    if data is None:
        return True  # second factor not set up: the password alone decides
    code = (code or "").strip()
    if not code:
        return False
    totp = pyotp.TOTP(data["secret"])
    with _lock:
        if code.isdigit() and len(code) == 6:
            now = time.time()
            for drift in (0, -1, 1):  # a phone clock up to 30 s off
                step = int(now // 30) + drift
                if hmac.compare_digest(totp.at(step * 30), code):
                    if _last_step.get(data["secret"], -1) >= step:
                        return False  # already used this window
                    _last_step[data["secret"]] = step
                    return True
            return False
        h = _hash(code)
        hashes = data.get("backup") or []
        for i, stored in enumerate(hashes):
            if hmac.compare_digest(stored, h):
                del hashes[i]
                p = _path(settings)
                if p.is_file():
                    p.write_text(json.dumps({**data, "backup": hashes}))
                return True
    return False


def remaining_backup_codes(settings: Settings) -> int:
    data = load(settings)
    return len(data.get("backup") or []) if data else 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["setup", "status", "disable"])
    parser.add_argument("--account", default="", help="name shown in the authenticator app (default: the username)")
    args = parser.parse_args(argv)
    settings = get_settings()
    if args.command == "status":
        if enabled(settings):
            print(f"Two-factor login is ON. Backup codes left: {remaining_backup_codes(settings)}.")
        else:
            print("Two-factor login is OFF. Run: python -m solarapp.twofactor setup")
        return 0
    if args.command == "disable":
        print("Two-factor login switched OFF." if disable(settings) else "Two-factor login was not set up.")
        return 0
    if enabled(settings) and sys.stdin.isatty():
        answer = input("Two-factor login is already set up. Replace the secret and the backup codes? [y/N] ").strip().lower()
        if answer != "y":
            return 1
    secret, codes, uri = setup(settings, args.account)
    print("\nScan this with Google Authenticator, Authy or any authenticator app:\n")
    try:
        import qrcode
        q = qrcode.QRCode(border=1)
        q.add_data(uri)
        q.make(fit=True)
        q.print_ascii(invert=True)
        png = settings.data_dir / "twofactor-qr.png"
        q.make_image().save(png)
        print(f"\nThe same QR code is saved as {png}; delete it after scanning.")
    except Exception:  # noqa: BLE001
        pass
    print(f"\nIf you cannot scan, enter this key by hand: {secret}")
    print("\nBackup codes, one use each. Keep them somewhere safe, away from the phone:\n")
    for c in codes:
        print(f"    {c}")
    print("\nDone. The login page now asks for the 6-digit code after the password.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
