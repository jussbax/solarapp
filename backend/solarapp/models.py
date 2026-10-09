from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column, LargeBinary
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Assessment(SQLModel, table=True):
    __tablename__ = "assessments"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    customer_name: str = ""
    address: str = ""
    doc: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    results: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    results_stale: bool = False


class ApplianceCatalog(SQLModel, table=True):
    """Every appliance ever entered in an audit, for reuse. Keyed by name, brand and model."""

    __tablename__ = "appliance_catalog"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    brand: str = ""
    model: str = ""
    category: str = "other"
    input_power_w: float = 0.0
    use_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class QuickEstimateLog(SQLModel, table=True):
    """One row per public estimate shown, so the owner can count estimates against leads."""
    __tablename__ = "quick_estimates"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    goal: str = ""
    pattern: str = ""
    monthly_kwh: float = 0.0
    town: str = ""
    lat: float = 0.0
    lon: float = 0.0
    panels: int = 0
    kwp: float = 0.0
    battery_kwh: float = 0.0
    price: float = 0.0
    source: str = ""      # utm_source or referrer host
    campaign: str = ""
    visitor: str = ""


class Lead(SQLModel, table=True):
    """A website booking (the CRM's data). Not a project; "Start project" creates the project from it.

    A future CRM module takes this table over; the engineering project keeps only ``lead_id``.
    """
    __tablename__ = "leads"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
    name: str = ""
    contact: str = ""
    town: str = ""
    province: str = ""
    address: str = ""
    lat: Optional[float] = None       # the visitor's pin, when they used their phone's location
    lon: Optional[float] = None
    preferred_time: str = ""
    consent: bool = False
    notice_version: str = ""          # the privacy line the visitor was shown
    source: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))    # utm, fbclid, referrer, page
    estimate: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))  # what the visitor saw (LeadEstimate)
    notes: str = ""                   # the plain-words summary the website route composes; the owner may edit it
    status: str = Field(default="new", index=True)   # new | contacted | visit_booked | converted | closed
    project_id: Optional[int] = None  # the assessment it became
    closed_reason: str = ""
    anonymised_at: Optional[datetime] = None  # set by the retention run


class AppSetting(SQLModel, table=True):
    __tablename__ = "app_settings"

    key: str = Field(primary_key=True)
    value: str = ""


class MaterialSupplier(SQLModel, table=True):
    __tablename__ = "material_suppliers"

    name: str = Field(primary_key=True)
    pickup_address: str = ""
    dealer_discount: float = 0.0
    payment_fee: float = 0.0
    delivers_free: bool = False
    price_list_date: str = ""
    prices_note: str = ""
    warranty: str = ""
    remarks: str = ""


class MaterialItem(SQLModel, table=True):
    """Materials database: one row per supplier item. The app is the master after import."""

    __tablename__ = "material_items"

    code: str = Field(primary_key=True)
    category: str = Field(index=True)
    supplier: str = Field(index=True)
    name: str = Field(index=True)
    spec: str = ""
    unit: str = "pc"
    sold_as: str = "pc"
    list_price: float = 0.0
    rating: Optional[float] = None
    rating_unit: str = ""
    weight_kg: float = 0.0
    volume_m3: float = 0.0
    weight_source: str = ""
    storage: float = 0.0
    price_list_date: str = ""
    remarks: str = ""
    panel_length_m: Optional[float] = None
    panel_width_m: Optional[float] = None
    active: bool = True
    # Electrical data from the datasheet (contract C4); all optional, None until the owner or the workbook fills them.
    grid_interactive: Optional[bool] = None     # inverters: may export to the grid (anti-islanding certified); None = unknown
    certifications: str = ""                    # inverters: the listing the DU asks for, e.g. "IEC 61727 / 62116"
    max_pv_voltage_v: Optional[float] = None    # inverters: maximum PV input voltage
    mppt_min_v: Optional[float] = None          # inverters: MPPT window, low end
    mppt_max_v: Optional[float] = None          # inverters: MPPT window, high end
    mppt_count: Optional[int] = None            # inverters: number of MPPT inputs
    mppt_max_a: Optional[float] = None          # inverters: maximum current per MPPT
    ac_input_a: Optional[float] = None          # inverters: maximum AC input (grid pass-through) current
    battery_max_a: Optional[float] = None       # inverters: maximum battery charge/discharge current
    has_transfer_switch: Optional[bool] = None  # inverters: carries its own transfer switch, so no external ATS; None = unknown
    continuous_a: Optional[float] = None        # batteries: continuous discharge current
    voc_v: Optional[float] = None               # panels: open-circuit voltage at STC
    vmp_v: Optional[float] = None               # panels: voltage at maximum power
    isc_a: Optional[float] = None               # panels: short-circuit current
    imp_a: Optional[float] = None               # panels: current at maximum power
    temp_coeff_voc_pct: Optional[float] = None  # panels: Voc temperature coefficient, % per degree C (negative)
    temp_coeff_isc_pct: Optional[float] = None  # panels: Isc temperature coefficient, % per degree C
    updated_at: datetime = Field(default_factory=utcnow)


class User(SQLModel, table=True):
    """A person who may sign in: the owner (manages people, settings and materials) or an engineer (projects and
    documents). Passwords are stored as argon2id hashes; the authenticator and the security keys are per person."""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)   # lower case, no spaces
    display_name: str = ""
    role: str = "engineer"                            # owner | engineer
    password_hash: str = ""
    must_change_password: bool = False                # a temporary password from the owner: change it before working
    active: bool = True
    session_generation: str = ""                      # rotated on a password change, a sign-out everywhere or a deactivation
    totp_secret: str = ""                             # blank = authenticator off
    totp_pending_secret: str = ""                     # set-up started in the browser, not yet confirmed with a code
    totp_backup: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))   # hashed one-time codes
    totp_last_step: int = 0                           # replay guard: the last 30 s step accepted
    created_at: datetime = Field(default_factory=utcnow)
    last_login_at: Optional[datetime] = None


class Passkey(SQLModel, table=True):
    """A registered security key or phone passkey (WebAuthn credential) that signs its person in on its own."""
    __tablename__ = "passkeys"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, index=True)   # the person it belongs to; keys from before accounts existed go to the first owner
    name: str = ""
    credential_id: bytes = Field(sa_column=Column(LargeBinary, nullable=False, unique=True))
    public_key: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    sign_count: int = 0
    transports: str = ""     # how the browser reached it: usb, nfc, ble, internal, hybrid
    aaguid: str = ""         # the authenticator model, when it says
    backed_up: bool = False  # a synced passkey (phone cloud) rather than a single hardware key
    created_at: datetime = Field(default_factory=utcnow)
    last_used_at: Optional[datetime] = None
