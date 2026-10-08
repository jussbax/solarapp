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
    continuous_a: Optional[float] = None        # batteries: continuous discharge current
    voc_v: Optional[float] = None               # panels: open-circuit voltage at STC
    vmp_v: Optional[float] = None               # panels: voltage at maximum power
    isc_a: Optional[float] = None               # panels: short-circuit current
    imp_a: Optional[float] = None               # panels: current at maximum power
    temp_coeff_voc_pct: Optional[float] = None  # panels: Voc temperature coefficient, % per degree C (negative)
    temp_coeff_isc_pct: Optional[float] = None  # panels: Isc temperature coefficient, % per degree C
    updated_at: datetime = Field(default_factory=utcnow)


class Passkey(SQLModel, table=True):
    """A registered security key or phone passkey (WebAuthn credential) that signs the owner in on its own."""
    __tablename__ = "passkeys"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = ""
    credential_id: bytes = Field(sa_column=Column(LargeBinary, nullable=False, unique=True))
    public_key: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    sign_count: int = 0
    transports: str = ""     # how the browser reached it: usb, nfc, ble, internal, hybrid
    aaguid: str = ""         # the authenticator model, when it says
    backed_up: bool = False  # a synced passkey (phone cloud) rather than a single hardware key
    created_at: datetime = Field(default_factory=utcnow)
    last_used_at: Optional[datetime] = None
