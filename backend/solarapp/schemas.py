"""The assessment document as edited in the browser and stored as JSON."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import ConfigDict, BaseModel, Field, field_validator, model_validator


class WallObstacle(BaseModel):
    """A firewall or long wall beside a face: it lies along one edge, height above the roof at that edge."""
    id: str
    edge: Literal["eave", "ridge", "left", "right"] = "left"
    height_m: float = Field(default=0, ge=0)
    gap_m: float = Field(default=0, ge=0)


class ShadeObstacle(BaseModel):
    """A tree or building: compass direction from the panels and the angle to its top from panel height."""
    id: str
    label: str = ""
    direction_deg: float = Field(default=180, ge=0, lt=360)
    elevation_deg: float = Field(default=0, ge=0, le=89)
    width_deg: float = Field(default=40, gt=0, le=180)   # how wide it looks from the roof
    share: float = Field(default=1.0, ge=0, le=1.0)      # share of the face it shades when the sun is behind it


class RoofFace(BaseModel):
    id: str
    name: str = "Roof"
    shape: Literal["rect", "hip", "tri"] = "rect"
    length_m: float = Field(gt=0)            # eave length
    width_m: float = Field(gt=0)             # slope length, eave to ridge
    ridge_m: Optional[float] = Field(default=None, ge=0)   # hip face only
    tilt_deg: float = Field(default=10, ge=0, le=90)
    azimuth_deg: float = Field(default=180, ge=0, lt=360)
    panels_left_out: int = Field(default=0, ge=0)          # vents, tanks, areas the surveyor excluded
    panel_count_override: Optional[int] = Field(default=None, ge=0)
    walls: list[WallObstacle] = Field(default_factory=list)
    obstacles: list[ShadeObstacle] = Field(default_factory=list)


class CandidatePanel(BaseModel):
    """A panel the layout fits to the roof. Since round 4 the candidates are the usable panels of the materials list
    (`Catalog.panel_candidates`), with the code as the id; a record no longer carries its own list."""
    id: str
    name: str = ""
    watt_peak: float = Field(gt=0)
    length_m: float = Field(gt=0)
    width_m: float = Field(gt=0)
    code: Optional[str] = None  # materials database code, used for pricing


class Reading(BaseModel):
    irradiance_wm2: float = Field(ge=0)
    power_w: float = Field(ge=0)
    module_temp_c: Optional[float] = None  # probe reading; blank = estimated


class ReadingSet(BaseModel):
    id: str
    face_id: Optional[str] = None
    label: str = ""
    measured_at: Optional[datetime] = None  # local (Asia/Manila), naive
    ambient_temp_c: Optional[float] = None
    sky_condition: str = "clear"
    readings: list[Reading] = Field(default_factory=list)

    @field_validator("measured_at")
    @classmethod
    def _strip_tz(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is not None:
            v = v.replace(tzinfo=None)
        return v


class UsageWindow(BaseModel):
    start: str = "18:00"   # HH:MM local
    end: str = "22:00"     # HH:MM; at or before start crosses midnight; equal = 24 h
    days: list[int] = Field(default_factory=lambda: list(range(7)))        # 0 = Monday
    months: list[int] = Field(default_factory=lambda: list(range(1, 13)))

    @field_validator("start", "end")
    @classmethod
    def _hhmm(cls, v: str) -> str:
        h, m = v.strip().split(":")
        h_i, m_i = int(h), int(m)
        if not (0 <= h_i <= 24 and 0 <= m_i < 60):
            raise ValueError("time must be HH:MM")
        return f"{h_i % 24:02d}:{m_i:02d}"


class ApplianceEntry(BaseModel):
    id: str
    name: str = ""
    brand: str = ""
    model: str = ""
    category: str = "other"
    input_power_w: float = Field(default=0, ge=0)
    quantity: int = Field(default=1, ge=1)
    duty_factor: Optional[float] = Field(default=None, gt=0, le=1.0)
    status: Literal["existing", "future", "retiring"] = "existing"
    windows: list[UsageWindow] = Field(default_factory=list)
    notes: str = ""


class BillEntry(BaseModel):
    id: str
    billing_month: str = ""   # YYYY-MM
    kwh: float = Field(default=0, ge=0)
    days: Optional[int] = Field(default=None, ge=20, le=40)
    amount_php: Optional[float] = Field(default=None, ge=0)
    utility: str = ""
    generation_rate_php_per_kwh: Optional[float] = Field(default=None, ge=0)   # the generation charge per kWh on the bill: the DU credits exports at this rate


class SystemSettings(BaseModel):
    kind: Literal["off_grid", "net_metering", "combination"] = "combination"
    offgrid_pv_margin: float = Field(default=1.25, ge=1.0, le=2.0)  # off-grid: worst-month production over consumption
    inverter_sizes_kw: list[float] = Field(default_factory=lambda: [6.0, 8.0, 10.0, 12.0])
    inverter_surge_factor: float = Field(default=2.0, ge=1.0, le=4.0)
    pv_ratio_max: float = Field(default=1.3, ge=1.0, le=2.0)
    battery_dod: float = Field(default=0.85, gt=0, le=1.0)
    battery_efficiency: float = Field(default=0.92, gt=0, le=1.0)


class EnergyAudit(BaseModel):
    appliances: list[ApplianceEntry] = Field(default_factory=list)
    bills: list[BillEntry] = Field(default_factory=list)
    reconcile: bool = True
    system: SystemSettings = Field(default_factory=SystemSettings)


class BomEdit(BaseModel):
    """A manual change to the generated bill of materials: a quantity override (0 removes) or an added item."""
    code: str
    qty: float = Field(ge=0)
    note: str = ""


class PricingJob(BaseModel):
    """Per-job pricing inputs; blanks follow the pricing settings or are prefilled from the assessment."""
    inverter_code: Optional[str] = None
    battery_code: Optional[str] = None
    strings_override: Optional[int] = Field(default=None, ge=1)
    max_panels_per_string: Optional[int] = Field(default=None, ge=1)
    roof_factor: Optional[float] = Field(default=None, gt=0, le=1.5)
    roof_closed_days: Optional[int] = Field(default=None, ge=1)   # at least a day; 0 reads as 1 (see below)
    max_days: Optional[int] = Field(default=None, ge=1)
    max_pairs: Optional[int] = Field(default=None, ge=1)
    owner_days: Optional[float] = Field(default=None, ge=0)
    extra_km: Optional[float] = Field(default=None, ge=0)     # blank = from the map pin
    extra_toll: Optional[float] = Field(default=None, ge=0)
    pv_run_m: Optional[float] = Field(default=None, gt=0)
    ac_run_m: Optional[float] = Field(default=None, gt=0)
    grounding_run_m: Optional[float] = Field(default=None, ge=0)
    conduit_m: Optional[float] = Field(default=None, ge=0)
    bom_edits: list[BomEdit] = Field(default_factory=list)     # overrides by code; qty 0 removes
    bom_extra: list[BomEdit] = Field(default_factory=list)     # added lines

    @field_validator("roof_closed_days", mode="before")
    @classmethod
    def _closed_days_floor(cls, v):  # noqa: ANN001
        """The roof closes in at least a day: a saved or typed 0 (the workbook's #DIV/0!) reads as 1, as the engine prices it."""
        return 1 if v == 0 else v


class PaymentMilestoneIn(BaseModel):
    key: str
    label: str
    share: float = Field(ge=0, le=1)
    event: str = "signing"
    offset_days: int = 0


class PaymentPlanIn(BaseModel):
    milestones: list[PaymentMilestoneIn] = Field(default_factory=list)
    installments: int = Field(default=0, ge=0)
    installment_share: float = Field(default=0, ge=0, le=1)
    installment_interval_days: int = Field(default=30, ge=1)
    installment_start_event: str = "commissioning"
    installment_first_offset_days: int = Field(default=30, ge=0)


# The job's stage, from the first visit to the closed job. Kept on the document for the CRM (quoted, signed) and the PM
# module (sourcing to closed) to come; since round 4 no engineering screen edits it and the project head shows the
# engineering status instead (EngineeringStatus below). "lead" and "contacted" belong to the booking (the CRM's data behind /api/leads).
JobStage = Literal["assessed", "quoted", "signed", "sourcing", "installing", "commissioned", "net_metering", "closed"]
JOB_STAGES: list[str] = ["assessed", "quoted", "signed", "sourcing", "installing", "commissioned", "net_metering", "closed"]
LEGACY_LEAD_STAGES = ("lead", "contacted")

# The engineering status (round 4): read-only, derived from the record's facts and never typed. Draft = nothing
# measured yet; surveyed = at least one reading set saved; designed = results calculated and not stale; proposal
# issued = the proposal PDF was generated for the record (the date is kept; "Reopen design" clears it).
EngineeringStatus = Literal["draft", "surveyed", "designed", "proposal_issued"]
ENGINEERING_STATUSES: list[str] = ["draft", "surveyed", "designed", "proposal_issued"]


class ProgramJob(BaseModel):
    """Program of works inputs; blanks follow the program settings."""
    stage: JobStage = "assessed"

    @field_validator("stage", mode="before")
    @classmethod
    def _legacy_stage(cls, v):  # noqa: ANN001
        """A record saved before bookings had their own table reads as "assessed"; the startup migration rewrites it for good."""
        return "assessed" if v in LEGACY_LEAD_STAGES else v
    signing_date: Optional[str] = None       # YYYY-MM-DD; blank = today
    install_date: Optional[str] = None       # blank = after the permit
    depart_time: Optional[str] = None        # HH:MM
    lunch_start: Optional[str] = None
    lunch_minutes: Optional[int] = Field(default=None, ge=0, le=180)
    permit_approval_days: Optional[int] = Field(default=None, ge=0)
    netmeter_application_days: Optional[int] = Field(default=None, ge=0)
    netmeter_meter_days: Optional[int] = Field(default=None, ge=0)
    payment: Optional[PaymentPlanIn] = None  # blank = company default plan


class EconomicsJob(BaseModel):
    """Per-job economics inputs; blanks follow the settings, the tariff follows the bill."""
    tariff_php_per_kwh: Optional[float] = Field(default=None, gt=0)
    export_rate_php_per_kwh: Optional[float] = Field(default=None, ge=0)
    tariff_escalation: Optional[float] = Field(default=None, ge=-0.2, le=0.5)
    degradation: Optional[float] = Field(default=None, ge=0, le=0.1)
    analysis_years: Optional[int] = Field(default=None, ge=1, le=40)
    discount_rate: Optional[float] = Field(default=None, ge=0, le=0.5)
    battery_life_years: Optional[int] = Field(default=None, ge=1, le=40)
    inverter_life_years: Optional[int] = Field(default=None, ge=1, le=40)
    om_per_year: Optional[float] = Field(default=None, ge=0)


class LeadSource(BaseModel):
    """Where a website lead came from; whatever the page could read."""
    model_config = ConfigDict(extra="ignore")
    utm_source: str = Field(default="", max_length=100)
    utm_medium: str = Field(default="", max_length=100)
    utm_campaign: str = Field(default="", max_length=100)
    utm_content: str = Field(default="", max_length=100)
    fbclid: str = Field(default="", max_length=200)
    referrer: str = Field(default="", max_length=300)
    page: str = Field(default="", max_length=300)


class LeadEstimate(BaseModel):
    """What the prospect saw when they booked."""
    model_config = ConfigDict(extra="ignore")
    goal: str = Field(default="", max_length=20)
    panels: int = Field(default=0, ge=0, le=500)
    kwp: float = Field(default=0.0, ge=0, le=500)
    battery_kwh: float = Field(default=0.0, ge=0, le=1000)
    price: float = Field(default=0.0, ge=0, le=100_000_000)
    bill_before_monthly: Optional[float] = Field(default=None, ge=0, le=10_000_000)
    bill_after_monthly: Optional[float] = Field(default=None, ge=0, le=10_000_000)
    payback_years: Optional[float] = Field(default=None, ge=0, le=1000)
    # what the visitor typed, filled in by the server so "Start project" can prefill the first bill
    monthly_kwh: Optional[float] = Field(default=None, ge=0, le=20000)
    monthly_php: Optional[float] = Field(default=None, ge=0, le=1000000)
    pattern: str = Field(default="", max_length=20)


class LeadInfo(BaseModel):
    """Kept on the assessment when it started as a website lead."""
    contact: str = ""
    town: str = ""
    preferred_time: str = ""
    consent: bool = False
    notice_version: str = ""      # the privacy line the visitor was shown
    created_at: str = ""
    source: LeadSource = Field(default_factory=LeadSource)
    estimate: LeadEstimate = Field(default_factory=LeadEstimate)


class AssessmentDoc(BaseModel):
    customer_name: str = ""
    address: str = ""
    notes: str = ""
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    faces: list[RoofFace] = Field(default_factory=list)
    # The panel is chosen in the background (round 4): the usable panels of the materials list are the candidates and
    # the one with the most kWp on this roof wins (ties to the lower list price per watt), unless the pricing settings
    # name one for every job or the engineer names one here. Blank = automatic.
    panel_code: Optional[str] = Field(default=None, max_length=40)
    # Panels typed by hand on a record saved before the materials list chose the panel (the old "Panel options" card):
    # the next calculation says they were replaced, then clears this.
    dropped_panels: list[str] = Field(default_factory=list)
    reading_sets: list[ReadingSet] = Field(default_factory=list)
    test_panel_rating_w: float = Field(default=50, gt=0)
    test_panel_calibration: float = Field(default=1.0, gt=0, le=1.5)
    setback_m: float = Field(default=0.6, ge=0)
    gap_m: float = Field(default=0.0, ge=0)
    audit: EnergyAudit = Field(default_factory=EnergyAudit)
    pricing: PricingJob = Field(default_factory=PricingJob)
    program: ProgramJob = Field(default_factory=ProgramJob)
    economics: EconomicsJob = Field(default_factory=EconomicsJob)
    lead: Optional[LeadInfo] = None   # old records that started as a website lead; converted leads carry only the estimate the visitor saw
    lead_id: Optional[int] = None     # the leads-inbox row this project was started from
    card_next_step: str = ""  # the card's next-step line, saved with the record

    @model_validator(mode="before")
    @classmethod
    def _legacy_panels(cls, data):  # noqa: ANN001
        """A record saved before round 4 carried its own candidate panels (`panels`) and the one ticked under Use
        (`selected_panel_id`). A ticked panel that is a materials-list item becomes the project's override; panels typed
        by hand are dropped and named under `dropped_panels`, so the next calculation can say what replaced them."""
        if not isinstance(data, dict) or ("panels" not in data and "selected_panel_id" not in data):
            return data
        data = dict(data)
        panels = data.pop("panels", None) or []
        selected = data.pop("selected_panel_id", None)
        if not isinstance(panels, list):
            return data
        chosen = next((p for p in panels if isinstance(p, dict) and p.get("id") == selected), None)
        if chosen and chosen.get("code") and not data.get("panel_code"):
            data["panel_code"] = str(chosen["code"])
        typed = [str(p.get("name") or f"{p.get('watt_peak')} W panel") for p in panels if isinstance(p, dict) and not p.get("code")]
        if typed and not data.get("dropped_panels"):
            data["dropped_panels"] = typed
        return data


class ApplianceCatalogOut(BaseModel):
    id: int
    name: str
    brand: str
    model: str
    category: str
    input_power_w: float
    use_count: int


class ApplianceCatalogIn(BaseModel):
    name: str
    brand: str = ""
    model: str = ""
    category: str = "other"
    input_power_w: float = Field(gt=0)


class AssessmentSummary(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    customer_name: str
    address: str
    has_results: bool
    results_stale: bool
    pricing_settings_changed: bool = False   # the pricing settings moved since this price was calculated (its own reason, apart from stale inputs)
    stage: str = "assessed"                  # the job stage the document keeps for the CRM and PM modules; no engineering screen shows it
    status: EngineeringStatus = "draft"      # the engineering status, derived from the facts (round 4)
    proposal_issued_at: Optional[datetime] = None
    contract_php: Optional[float] = None
    system_kwp: Optional[float] = None
    annual_kwh: Optional[float] = None
    panel_count: Optional[int] = None
    kind: Optional[str] = None
    face_count: int = 0
    battery_kwh: Optional[float] = None    # the battery the customer pays for (BOM), else the sized one; None without results or for net metering
    computed_at: Optional[str] = None      # when the results were last calculated
    lead_id: Optional[int] = None          # the leads-inbox row it was started from; the only lead field a project summary carries


class AssessmentOut(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    doc: AssessmentDoc
    results: Optional[dict[str, Any]] = None
    results_stale: bool = False
    pricing_settings_changed: bool = False   # see AssessmentSummary
    status: EngineeringStatus = "draft"
    proposal_issued_at: Optional[datetime] = None


class LoginIn(BaseModel):
    username: str = Field(max_length=120)
    password: str = Field(max_length=200)
    code: str = Field(default="", max_length=16)   # authenticator code or backup code, when two-factor login is on


class StepUpIn(BaseModel):
    """Managing keys and signing out everywhere ask for the password (and the code) again, so a stolen cookie alone cannot do it."""
    password: str = Field(max_length=200)
    code: str = Field(default="", max_length=16)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=200)
    code: str = Field(default="", max_length=16)
    new_password: str = Field(max_length=200)


class TotpCodeIn(BaseModel):
    code: str = Field(max_length=16)


class UserCreateIn(BaseModel):
    username: str = Field(max_length=40)
    display_name: str = Field(default="", max_length=80)
    role: str = Field(default="engineer", max_length=16)


class UserPatchIn(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=80)
    role: Optional[str] = Field(default=None, max_length=16)
    active: Optional[bool] = None


class PasskeyRegisterIn(BaseModel):
    """The challenge from /passkeys/options stands in for the password: it was issued only after a step-up."""
    challenge_id: str = Field(max_length=64)
    name: str = Field(default="", max_length=60)
    credential: dict[str, Any]   # the browser's PublicKeyCredential as JSON


class PasskeyLoginIn(BaseModel):
    challenge_id: str = Field(max_length=64)
    credential: dict[str, Any]


class SettingsOut(BaseModel):
    """Company profile; every key in profile.PROFILE_FIELDS."""
    model_config = ConfigDict(extra="allow")
    company_name: str
    company_contact: str


class SettingsIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    company_name: Optional[str] = None
    company_contact: Optional[str] = None


class MaterialItemIn(BaseModel):
    code: str = Field(min_length=3, max_length=40)
    category: str
    supplier: str
    name: str
    spec: str = ""
    unit: str = "pc"
    sold_as: str = "pc"
    list_price: float = Field(ge=0)
    rating: Optional[float] = None
    rating_unit: str = ""
    weight_kg: float = Field(default=0, ge=0)
    volume_m3: float = Field(default=0, ge=0)
    weight_source: str = ""
    storage: float = Field(default=0, ge=0)
    price_list_date: str = ""
    remarks: str = ""
    panel_length_m: Optional[float] = Field(default=None, gt=0)
    panel_width_m: Optional[float] = Field(default=None, gt=0)
    active: bool = True
    # electrical data (contract C4), all optional
    grid_interactive: Optional[bool] = None
    certifications: str = ""
    max_pv_voltage_v: Optional[float] = Field(default=None, gt=0)
    mppt_min_v: Optional[float] = Field(default=None, ge=0)
    mppt_max_v: Optional[float] = Field(default=None, gt=0)
    mppt_count: Optional[int] = Field(default=None, ge=1)
    mppt_max_a: Optional[float] = Field(default=None, gt=0)
    ac_input_a: Optional[float] = Field(default=None, gt=0)
    battery_max_a: Optional[float] = Field(default=None, gt=0)
    has_transfer_switch: Optional[bool] = None
    continuous_a: Optional[float] = Field(default=None, gt=0)
    voc_v: Optional[float] = Field(default=None, gt=0)
    vmp_v: Optional[float] = Field(default=None, gt=0)
    isc_a: Optional[float] = Field(default=None, gt=0)
    imp_a: Optional[float] = Field(default=None, gt=0)
    temp_coeff_voc_pct: Optional[float] = None
    temp_coeff_isc_pct: Optional[float] = None
    # round 12: the datasheet fields (brief, section 1); every one optional
    max_system_voltage_v: Optional[float] = Field(default=None, gt=0)
    inverter_type: str = ""
    phase: Optional[int] = Field(default=None, ge=1, le=3)
    battery_class: str = ""
    charge_v_max: Optional[float] = Field(default=None, gt=0)
    charge_a_max: Optional[float] = Field(default=None, gt=0)
    mppt_currents_a: str = ""
    battery_inputs: Optional[int] = Field(default=None, ge=1)
    nominal_v: Optional[float] = Field(default=None, gt=0)
    capacity_ah: Optional[float] = Field(default=None, gt=0)
    discharge_a_recommended: Optional[float] = Field(default=None, gt=0)


class MaterialItemPatch(BaseModel):
    category: Optional[str] = None
    supplier: Optional[str] = None
    name: Optional[str] = None
    spec: Optional[str] = None
    unit: Optional[str] = None
    sold_as: Optional[str] = None
    list_price: Optional[float] = Field(default=None, ge=0)
    rating: Optional[float] = None
    rating_unit: Optional[str] = None
    weight_kg: Optional[float] = Field(default=None, ge=0)
    volume_m3: Optional[float] = Field(default=None, ge=0)
    weight_source: Optional[str] = None
    storage: Optional[float] = Field(default=None, ge=0)
    price_list_date: Optional[str] = None
    remarks: Optional[str] = None
    panel_length_m: Optional[float] = Field(default=None, gt=0)
    panel_width_m: Optional[float] = Field(default=None, gt=0)
    active: Optional[bool] = None
    grid_interactive: Optional[bool] = None
    certifications: Optional[str] = None
    max_pv_voltage_v: Optional[float] = Field(default=None, gt=0)
    mppt_min_v: Optional[float] = Field(default=None, ge=0)
    mppt_max_v: Optional[float] = Field(default=None, gt=0)
    mppt_count: Optional[int] = Field(default=None, ge=1)
    mppt_max_a: Optional[float] = Field(default=None, gt=0)
    ac_input_a: Optional[float] = Field(default=None, gt=0)
    battery_max_a: Optional[float] = Field(default=None, gt=0)
    has_transfer_switch: Optional[bool] = None
    continuous_a: Optional[float] = Field(default=None, gt=0)
    voc_v: Optional[float] = Field(default=None, gt=0)
    vmp_v: Optional[float] = Field(default=None, gt=0)
    isc_a: Optional[float] = Field(default=None, gt=0)
    imp_a: Optional[float] = Field(default=None, gt=0)
    temp_coeff_voc_pct: Optional[float] = None
    temp_coeff_isc_pct: Optional[float] = None
    max_system_voltage_v: Optional[float] = Field(default=None, gt=0)
    inverter_type: Optional[str] = None
    phase: Optional[int] = Field(default=None, ge=1, le=3)
    battery_class: Optional[str] = None
    charge_v_max: Optional[float] = Field(default=None, gt=0)
    charge_a_max: Optional[float] = Field(default=None, gt=0)
    mppt_currents_a: Optional[str] = None
    battery_inputs: Optional[int] = Field(default=None, ge=1)
    nominal_v: Optional[float] = Field(default=None, gt=0)
    capacity_ah: Optional[float] = Field(default=None, gt=0)
    discharge_a_recommended: Optional[float] = Field(default=None, gt=0)


class DatasheetLink(BaseModel):
    """A manual link from a datasheet row to a material item, or the code of the item to add from it (round 12)."""
    code: str = Field(min_length=3, max_length=40)
    supplier: Optional[str] = None


class QuickRequest(BaseModel):
    """The four questions of the free estimate. Location is a listed town or a pin."""
    goal: Literal["net_metering", "combination", "off_grid"] = "combination"
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    town: str = Field(default="", max_length=60)
    province: str = Field(default="", max_length=40)
    monthly_kwh: Optional[float] = Field(default=None, gt=0, le=20000)
    monthly_php: Optional[float] = Field(default=None, gt=0, le=1000000)
    pattern: Literal["morning", "balanced", "evening"] = "balanced"


class QuickLead(QuickRequest):
    name: str = Field(min_length=1, max_length=120)
    contact: str = Field(min_length=3, max_length=120)
    address: str = Field(default="", max_length=200)
    preferred_time: str = Field(default="", max_length=40)
    consent: bool = True
    notice_version: str = Field(default="", max_length=40)
    website: str = Field(default="", max_length=200)   # honeypot: a real person leaves it empty
    source: LeadSource = Field(default_factory=LeadSource)
    estimate: LeadEstimate = Field(default_factory=LeadEstimate)


# ---- website bookings (the CRM's data; the engineering app lists the open ones and starts a project from one)

LeadStatus = Literal["new", "contacted", "visit_booked", "converted", "closed"]
LEAD_STATUSES: list[str] = ["new", "contacted", "visit_booked", "converted", "closed"]


class LeadOut(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    name: str
    contact: str
    town: str
    province: str
    place: str                      # "Pila, Laguna", or what the visitor's pin resolved to
    address: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    preferred_time: str
    consent: bool
    notice_version: str
    source: LeadSource
    source_label: str               # "fb/brownout1", a referrer host, or "direct"
    estimate: LeadEstimate
    notes: str
    status: LeadStatus
    project_id: Optional[int] = None
    closed_reason: str = ""
    anonymised: bool = False


class LeadPatch(BaseModel):
    """What the CRM (today the owner, through the API) edits on a booking: the status, the notes, and why it was closed."""
    status: Optional[LeadStatus] = None
    notes: Optional[str] = Field(default=None, max_length=4000)
    closed_reason: Optional[str] = Field(default=None, max_length=200)


class LeadConvertOut(BaseModel):
    project_id: int
    lead: LeadOut


class LeadFunnel(BaseModel):
    """The last N days: estimates run, leads, visits booked, converted (from the bookings), quoted and signed (from the projects)."""
    days: int
    estimates: int
    leads: int
    visits_booked: int
    converted: int
    quoted: int
    signed: int
    estimates_by_source: dict[str, int]
