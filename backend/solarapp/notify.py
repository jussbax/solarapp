"""Optional email notice when a website lead arrives. Off unless SMTP is configured."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from .config import Settings
from .schemas import LeadEstimate

log = logging.getLogger(__name__)


def smtp_configured(settings: Settings) -> bool:
    return bool(settings.smtp_host and settings.notify_email)


def lead_notice(*, name: str, contact: str, preferred_time: str, wants: str, uses: str, kwh: float, monthly_php: Optional[float],
                estimate: Optional[LeadEstimate], place: str, pin_placed: bool, address: str, source: str, link: str, promise: str) -> tuple[str, str]:
    """Subject and body of the owner's lead email: one fact per line, so it reads on a phone.

    ``place`` is the town label ("Pila, Laguna"); ``promise`` is the callback promise the thank-you page showed.
    """
    town = place.split(",")[0].strip() if place else ""
    when = preferred_time.strip().lower()
    subject = f"New lead: {name}, {contact}, {town}" + (f" ({when})" if when else "")
    lines = [
        f"Name: {name}",
        f"Contact: {contact}" + (f", best time {when}" if when else ""),
        f"Wants: {wants}",
        f"Uses power: {uses}",
        f"Bill: about {kwh:,.0f} kWh" + (f" (₱{monthly_php:,.0f})" if monthly_php else ""),
    ]
    if estimate and estimate.panels:
        saw = [f"{estimate.panels} {'panel' if estimate.panels == 1 else 'panels'}", f"{estimate.kwp:.2f} kWp"]
        if estimate.battery_kwh >= 0.5:
            saw.append(f"{estimate.battery_kwh:.0f} kWh battery")
        saw.append(f"₱{estimate.price:,.0f}")
        if estimate.bill_before_monthly is not None and estimate.bill_after_monthly is not None:
            saw.append(f"bill ₱{estimate.bill_before_monthly:,.0f} → about ₱{estimate.bill_after_monthly:,.0f}")
        if estimate.payback_years is not None:
            saw.append(f"pays for itself in {estimate.payback_years:.1f} years")
        lines.append("Saw on the website: " + ", ".join(saw))
    if address.strip():
        lines.append(f"Address: {address.strip()}")
    lines.append(f"Location: {place}" + ("; pin placed by the customer, confirm on the visit" if pin_placed else ""))
    lines.append(f"Source: {source}")
    lines.append(f"Open: {link}")
    lines.append(f"The thank-you page promised a message or call {promise.strip()}.")
    return subject, "\n".join(lines) + "\n"


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
