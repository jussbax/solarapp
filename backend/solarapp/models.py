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
    # when the proposal PDF was first generated for this record (round 4): the engineering status reads "proposal
    # issued" from it and the price lock keys off it; "Reopen design" clears it. Outside the document, so a Save never wipes it.
    proposal_issued_at: Optional[datetime] = None
    # Round 13 (docs/audits/round-13/engineer-brief.md, 6.3): when the plans PDF was first generated for this record, which is
    # revision 0 ("first issue") of the drawing set, and the append-only revision log the office adds to with "Issue a
    # revision" on the Documents card: entries {no, date, note, by}. Both outside the document, so a Save never wipes them;
    # "Reopen design" leaves them (the log is a record, not a status). An older database gets the columns at start-up
    # (db.ensure_columns); an older record without them prints "Rev. 0" as before.
    plans_issued_at: Optional[datetime] = None
    revisions: Optional[list[dict[str, Any]]] = Field(default=None, sa_column=Column(JSON, nullable=True))


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
    # Round 12: the eleven fields the maker's datasheet workbooks fill (docs/audits/round-12/engineer-brief.md, section 1).
    # Added to an older database at start-up by store.ensure_material_columns.
    max_system_voltage_v: Optional[float] = None   # panels: maximum DC system voltage
    inverter_type: str = ""                        # inverters: grid_tie, hybrid, off_grid, charge_controller, ess_set; blank = unknown
    phase: Optional[int] = None                    # inverters: 1 or 3
    battery_class: str = ""                        # LV, HV or none (no battery port); blank = unknown
    charge_v_max: Optional[float] = None           # inverters: the battery port's maximum charge voltage; batteries: the pack's ceiling
    charge_a_max: Optional[float] = None           # inverters: maximum charge current into the battery; batteries: the most the pack accepts
    mppt_currents_a: str = ""                      # inverters: per-input MPPT currents as typed ("18/36/36")
    battery_inputs: Optional[int] = None           # inverters: battery ports; blank reads as one
    nominal_v: Optional[float] = None              # batteries: nominal voltage
    capacity_ah: Optional[float] = None            # batteries: capacity
    discharge_a_recommended: Optional[float] = None   # batteries: recommended continuous discharge current
    # Round 13 (docs/audits/round-13/engineer-brief.md, 2.3): the six figures the design analysis sheet reads from the items;
    # blank = the row prints "not checked" or the labelled assumption. Added to an older database at start-up like the rest.
    overall_area_mm2: Optional[float] = None       # wires: the insulated conductor's overall cross-section (conduit fill)
    inner_diameter_mm: Optional[float] = None      # raceways: the conduit's inside diameter (conduit fill)
    insulation_c: Optional[float] = None           # wires: the insulation's temperature rating (°C); blank reads as 90 with the note
    ampacity_a: Optional[float] = None             # wires: the maker's ampacity at the insulation rating; blank = the wiring rules' table with "verify"
    fault_current_a: Optional[float] = None        # inverters: maximum output fault current; batteries: the BMS's short-circuit trip
    aic_ka: Optional[float] = None                 # protective devices: the interrupting rating (AIC)
    updated_at: datetime = Field(default_factory=utcnow)


class DatasheetSpec(SQLModel, table=True):
    """One row per row of the maker's datasheet workbooks (round 12), never deleted: the figures as parsed, every
    cell as typed, the notices the parser raised, where the row came from, and the material item it matched.
    Keyed by category, normalised model and brand, so a re-run upserts."""

    __tablename__ = "datasheet_specs"

    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(index=True)                 # Solar Panel, Inverter, Battery, All-in-one System
    brand: str = ""                                   # the sheet's brand column
    brand_in_model: str = ""                          # the maker named in the model text when it differs (brief 6.1)
    model: str = ""                                   # as typed
    model_norm: str = Field(default="", index=True)   # upper case, letters and digits only
    fields: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))        # the parsed figures applied to the item
    held_fields: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))   # figures held back until the owner answers (1.5)
    raw: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))           # every cell as typed, by header
    notices: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    source_file: str = ""
    source_sheet: str = ""
    source_row: int = 0
    file_sha256: str = ""
    imported_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)
    matched_code: Optional[str] = Field(default=None, index=True)
    match_tier: str = ""                              # exact, contains, base, manual; blank = no item
    match_note: str = ""
    overridden_fields: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))   # typed over on the Materials page; left alone on a re-run
    held: bool = False                                # battery figures on a grid-tie unit (brief 1.5, 6.4), or a battery maximum above 1 C (6.8)
    held_applied_at: Optional[datetime] = None        # when the owner said to apply the held figures; kept through every later run (review finding 2)


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
