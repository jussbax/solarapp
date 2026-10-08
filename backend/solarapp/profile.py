"""The company's public profile: who you are, how to reach you, what you warrant.

Stored as app settings so the owner edits them on the Settings page; the public
estimate, the proposal, the roof check and the client card all read from here.
Blank fields are simply not printed.
"""
from __future__ import annotations

from sqlmodel import Session, select

from .config import Settings
from .models import AppSetting

# key -> (label, default). Order is the order on the Settings page.
PROFILE_FIELDS: list[tuple[str, str, str]] = [
    ("company_name", "Company name", ""),
    ("company_contact", "Contact line on documents (address, phone, email)", ""),
    ("address", "Office address", "Pila, Laguna"),
    ("phone", "Phone or mobile", ""),
    ("messenger", "Messenger link (https://m.me/yourpage)", ""),
    ("facebook", "Facebook page link", ""),
    ("email", "Email", ""),
    ("owner_name", "Owner's name (signs the proposal)", ""),
    ("pee_name", "Professional Electrical Engineer (name)", ""),
    ("pee_license", "PEE licence number (PRC)", ""),
    ("service_area", "Where you install", "Laguna and Batangas"),
    ("brands", "Brands you install (one line)", ""),
    ("warranty_workmanship_years", "Workmanship warranty (years)", ""),
    ("warranty_panels_product_years", "Panel product warranty (years)", ""),
    ("warranty_panels_performance_years", "Panel performance warranty (years)", ""),
    ("warranty_inverter_years", "Inverter warranty (years)", ""),
    ("warranty_battery_years", "Battery warranty (years)", ""),
    ("payment_details", "Where to pay (bank or GCash details for the proposal)", ""),
    ("callback_promise", "After a booking, you will reach out", "within one working day"),
    ("privacy_note", "Privacy line under the booking form", "We use your name and number only to arrange your visit and send your estimate. We keep them for up to 12 months unless you become a customer, and we never sell them or share them beyond the services that process them for us. Message us to see or delete your details."),
]
PROFILE_KEYS = [k for k, _, _ in PROFILE_FIELDS]
# fields only the website uses (the Settings page groups them under "Website"); the proposal fields stay with the documents
WEBSITE_KEYS = ["messenger", "facebook", "brands", "callback_promise", "privacy_note"]
# fields the public estimate page may show; the rest stay internal
PUBLIC_KEYS = [
    "company_name", "address", "phone", "messenger", "facebook", "email", "owner_name", "pee_name", "pee_license", "service_area", "brands",
    "warranty_workmanship_years", "warranty_panels_product_years", "warranty_panels_performance_years", "warranty_inverter_years", "warranty_battery_years",
    "callback_promise", "privacy_note",
]


def company_profile(session: Session, settings: Settings) -> dict[str, str]:
    stored = {s.key: s.value for s in session.exec(select(AppSetting)).all()}
    out: dict[str, str] = {}
    for key, _, default in PROFILE_FIELDS:
        if key == "company_name":
            out[key] = stored.get(key) or settings.company_name
        elif key == "company_contact":
            out[key] = stored.get(key) if key in stored else settings.company_contact
        else:
            out[key] = stored.get(key, default)
    return out


def public_profile(session: Session, settings: Settings) -> dict[str, str]:
    p = company_profile(session, settings)
    return {k: p[k] for k in PUBLIC_KEYS}


def warranty_lines(profile: dict[str, str]) -> list[str]:
    """Human sentences for the documents and the public page, from whatever is filled in."""
    out = []
    y = lambda k: (profile.get(k) or "").strip()  # noqa: E731
    if y("warranty_workmanship_years"):
        out.append(f"Workmanship: {y('warranty_workmanship_years')} years on our installation, including leak-free roof penetrations.")
    if y("warranty_panels_product_years") or y("warranty_panels_performance_years"):
        parts = []
        if y("warranty_panels_product_years"):
            parts.append(f"{y('warranty_panels_product_years')}-year product warranty")
        if y("warranty_panels_performance_years"):
            parts.append(f"{y('warranty_panels_performance_years')}-year performance warranty")
        out.append("Panels: " + " and ".join(parts) + " from the maker.")
    if y("warranty_inverter_years"):
        out.append(f"Inverter: {y('warranty_inverter_years')} years from the maker.")
    if y("warranty_battery_years"):
        out.append(f"Battery: {y('warranty_battery_years')} years from the maker.")
    return out
