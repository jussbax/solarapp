"""Optional email notice when a website lead arrives. Off unless SMTP is configured."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from .config import Settings

log = logging.getLogger(__name__)


def smtp_configured(settings: Settings) -> bool:
    return bool(settings.smtp_host and settings.notify_email)


def send_lead_notice(settings: Settings, subject: str, body: str) -> bool:
    """Send one plain-text email. Returns False (and logs) on any failure; never raises."""
    if not smtp_configured(settings):
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user or f"solarapp@{settings.smtp_host}"
    msg["To"] = settings.notify_email
    msg.set_content(body)
    try:
        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
            server.starttls()
        with server:
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001 - a failed notice must never fail the lead
        log.warning("lead notice not sent: %s", e)
        return False
