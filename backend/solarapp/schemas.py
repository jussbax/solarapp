"""The assessment document as edited in the browser and stored as JSON."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

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
    module_temp_c: float


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
