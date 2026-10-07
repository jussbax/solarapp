"""The assessment document as edited in the browser and stored as JSON."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class RoofFace(BaseModel):
    id: str
    name: str = "Roof"
    length_m: float = Field(gt=0)
    width_m: float = Field(gt=0)
    tilt_deg: float = Field(default=10, ge=0, le=90)
    azimuth_deg: float = Field(default=180, ge=0, lt=360)
    panel_count_override: Optional[int] = Field(default=None, ge=0)


class CandidatePanel(BaseModel):
    id: str
    name: str = ""
    watt_peak: float = Field(gt=0)
    length_m: float = Field(gt=0)
    width_m: float = Field(gt=0)


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
    system_kwp: Optional[float] = None
    annual_kwh: Optional[float] = None
    panel_count: Optional[int] = None


class AssessmentOut(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    doc: AssessmentDoc
    results: Optional[dict[str, Any]] = None
    results_stale: bool = False


class LoginIn(BaseModel):
    username: str
    password: str


class SettingsOut(BaseModel):
    company_name: str
    company_contact: str


class SettingsIn(BaseModel):
    company_name: Optional[str] = None
    company_contact: Optional[str] = None
