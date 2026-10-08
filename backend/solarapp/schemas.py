"""The assessment document as edited in the browser and stored as JSON."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import ConfigDict, BaseModel, Field, field_validator


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
    roof_closed_days: Optional[int] = Field(default=None, ge=0)
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


JobStage = Literal["lead", "contacted", "assessed", "quoted", "signed", "sourcing", "installing", "commissioned", "net_metering", "closed"]


class ProgramJob(BaseModel):
    """Program of works inputs; blanks follow the program settings."""
    stage: JobStage = "assessed"
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
    panels: list[CandidatePanel] = Field(default_factory=list)
    selected_panel_id: Optional[str] = None
    reading_sets: list[ReadingSet] = Field(default_factory=list)
    test_panel_rating_w: float = Field(default=50, gt=0)
    test_panel_calibration: float = Field(default=1.0, gt=0, le=1.5)
    setback_m: float = Field(default=0.6, ge=0)
    gap_m: float = Field(default=0.0, ge=0)
    audit: EnergyAudit = Field(default_factory=EnergyAudit)
    pricing: PricingJob = Field(default_factory=PricingJob)
    program: ProgramJob = Field(default_factory=ProgramJob)
    economics: EconomicsJob = Field(default_factory=EconomicsJob)
    lead: Optional[LeadInfo] = None


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
    stage: str = "assessed"
    contract_php: Optional[float] = None
    system_kwp: Optional[float] = None
    annual_kwh: Optional[float] = None
    panel_count: Optional[int] = None
    kind: Optional[str] = None
    lead_contact: Optional[str] = None
    lead_town: Optional[str] = None
    lead_source: Optional[str] = None
    lead_estimate: Optional[LeadEstimate] = None


class AssessmentOut(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    doc: AssessmentDoc
    results: Optional[dict[str, Any]] = None
    results_stale: bool = False


class LoginIn(BaseModel):
    username: str = Field(max_length=120)
    password: str = Field(max_length=200)
    code: str = Field(default="", max_length=16)   # authenticator code or backup code, when two-factor login is on


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
