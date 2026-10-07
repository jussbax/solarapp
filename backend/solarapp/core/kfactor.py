"""k-factor computation from on-site readings.

Conventions agreed with the owner (see DECISIONS.md):

* A reading row pairs one irradiance reading (W/m2), one MPPT power reading (W)
  and the module surface temperature (deg C) from the probe, taken together.
* ``k_raw_i = P_i / (rating * calibration * G_i / 1000)`` per row (S1, S7).
* ``k_site_i = k_raw_i / eta_rel(G_i, T_i)`` where ``eta_rel`` is the relative
  efficiency of a crystalline-silicon module at that irradiance and
  temperature from the PVGIS module model (Huld). This removes the heat and
  low-light effects present at the moment of measurement (S2). What remains
  is the site factor applied as a constant in the simulation.
* ``rise_per_kw_i = (T_i - T_ambient) / (G_i / 1000)`` describes how much the
  roof heats the module per kW/m2. It calibrates the thermal model.
* Quality checks (S6) produce warnings for internal use only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
from pvlib.pvarray import huld
from pvlib.temperature import faiman

LOW_IRRADIANCE_WM2 = 500.0
MAX_SPREAD_FRACTION = 0.10
CLOUDY_SKY = {"cloudy", "overcast"}
RISE_RANGE_C_PER_KW = (5.0, 60.0)
K_SITE_RANGE = (0.60, 1.15)
DEFAULT_TEST_PANEL_W = 50.0
ASSUMED_AMBIENT_C = 30.0
PVGIS_FAIMAN_U0, PVGIS_FAIMAN_U1 = 26.9, 6.2


def relative_efficiency(irradiance_wm2: float, module_temp_c: float) -> float:
    """Module efficiency relative to STC at the given irradiance and temperature.

    Uses the PVGIS 5 Huld coefficients for crystalline silicon. Equals 1.0 at
    1000 W/m2 and 25 deg C.
    """
    g = max(float(irradiance_wm2), 1e-6)
    power_per_wp = float(huld(g, float(module_temp_c), 1.0, cell_type="csi"))
    return power_per_wp / (g / 1000.0)


@dataclass
class ReadingRow:
    irradiance_wm2: float
    power_w: float
    module_temp_c: Optional[float] = None  # probe reading; None = estimate from ambient with the PVGIS thermal model


@dataclass
class ReadingSetInput:
    readings: list[ReadingRow]
    measured_at: Optional[datetime] = None
    ambient_temp_c: Optional[float] = None
    sky_condition: str = "clear"
    face_id: Optional[str] = None
    label: str = ""
    test_panel_rating_w: float = DEFAULT_TEST_PANEL_W
    calibration_factor: float = 1.0


@dataclass
class Warning_:
    code: str
    message: str


@dataclass
class ReadingSetResult:
    label: str
    face_id: Optional[str]
    k_raw_values: list[float]
    k_raw: float
    eta_rel_values: list[float]
    k_site_values: list[float]
    k_site: float
    avg_irradiance_wm2: float
    irradiance_spread_fraction: float
    avg_module_temp_c: float
    module_temp_source: str  # "measured" | "estimated" | "mixed"
    ambient_temp_c: Optional[float]
    ambient_source: str  # "measured" | "estimated" | "assumed" | "none"
    rise_per_kw_values: list[float]
    rise_per_kw: Optional[float]
    rise_is_plausible: bool
    warnings: list[Warning_] = field(default_factory=list)
    low_confidence: bool = False
    valid: bool = True


def evaluate_reading_set(
    s: ReadingSetInput, ambient_estimate_c: Optional[float] = None
) -> ReadingSetResult:
    """Compute k values for one set of readings.

    ``ambient_estimate_c`` is the typical air temperature for the measurement
    month and hour from the weather dataset, used only when the set carries no
    measured ambient temperature.
    """
    warnings: list[Warning_] = []
    rows = [r for r in s.readings if r.irradiance_wm2 > 0 and r.power_w >= 0]
    if not rows:
        return ReadingSetResult(
            label=s.label, face_id=s.face_id, k_raw_values=[], k_raw=float("nan"),
            eta_rel_values=[], k_site_values=[], k_site=float("nan"),
            avg_irradiance_wm2=0.0, irradiance_spread_fraction=0.0,
            avg_module_temp_c=float("nan"), module_temp_source="measured", ambient_temp_c=None, ambient_source="none",
            rise_per_kw_values=[], rise_per_kw=None, rise_is_plausible=False,
            warnings=[Warning_("no_readings", "No usable readings in this set.")],
            low_confidence=True, valid=False,
        )
    if len(rows) < 3:
        warnings.append(Warning_("few_readings", f"Only {len(rows)} usable reading(s); three are expected."))

    rating = s.test_panel_rating_w * s.calibration_factor
    k_raw_values = [r.power_w / (rating * r.irradiance_wm2 / 1000.0) for r in rows]

    g = np.array([r.irradiance_wm2 for r in rows])
    avg_g = float(g.mean())
    spread = float((g.max() - g.min()) / avg_g) if avg_g > 0 else 0.0

    # ambient: measured, else typical for the month and hour, else assumed
    if s.ambient_temp_c is not None:
        ambient, ambient_source = float(s.ambient_temp_c), "measured"
    elif ambient_estimate_c is not None:
        ambient, ambient_source = float(ambient_estimate_c), "estimated"
        warnings.append(Warning_(
            "ambient_estimated",
            f"No ambient temperature recorded; typical air temperature {ambient:.1f} C for that month and hour was used.",
        ))
    else:
        ambient, ambient_source = None, "none"

    # module temperature: probe reading, else PVGIS thermal model from irradiance and ambient
    measured_t = [r.module_temp_c for r in rows if r.module_temp_c is not None]
    missing = len(measured_t) < len(rows)
    if missing:
        amb_for_model = ambient if ambient is not None else ASSUMED_AMBIENT_C
        if ambient is None:
            ambient_source = "assumed"
            warnings.append(Warning_("ambient_assumed", f"No ambient temperature available; {ASSUMED_AMBIENT_C:.0f} C assumed for the module temperature estimate."))
        warnings.append(Warning_(
            "module_temp_estimated",
            "Panel temperature not recorded; estimated with the PVGIS thermal model, so the roof's own heating cannot be measured and the PVGIS thermal model is used in the simulation.",
        ))
    elif ambient is None:
        warnings.append(Warning_("no_ambient", "No ambient temperature available; PVGIS default thermal model used."))
    temps: list[float] = []
    for r in rows:
        if r.module_temp_c is not None:
            temps.append(float(r.module_temp_c))
        else:
            temps.append(float(faiman(r.irradiance_wm2, amb_for_model, 1.0, u0=PVGIS_FAIMAN_U0, u1=PVGIS_FAIMAN_U1)))
    module_temp_source = "measured" if not missing else ("estimated" if not measured_t else "mixed")
    eta_values = [relative_efficiency(r.irradiance_wm2, t) for r, t in zip(rows, temps)]
    k_site_values = [k / e for k, e in zip(k_raw_values, eta_values)]
    avg_t = float(np.mean(temps))

    # site thermal rise only from probe readings
    rise_values: list[float] = []
    rise: Optional[float] = None
    plausible = False
    if ambient is not None and measured_t:
        rise_values = [(r.module_temp_c - ambient) / (r.irradiance_wm2 / 1000.0) for r in rows if r.module_temp_c is not None]
        rise = float(np.mean(rise_values))
        plausible = RISE_RANGE_C_PER_KW[0] <= rise <= RISE_RANGE_C_PER_KW[1]
        if not plausible:
            warnings.append(Warning_(
                "rise_implausible",
                f"Module temperature rise of {rise:.1f} C per kW/m2 is outside {RISE_RANGE_C_PER_KW[0]:.0f}-{RISE_RANGE_C_PER_KW[1]:.0f}; PVGIS default thermal model used.",
            ))

    if avg_g < LOW_IRRADIANCE_WM2:
        warnings.append(Warning_("low_irradiance", f"Average irradiance {avg_g:.0f} W/m2 is below {LOW_IRRADIANCE_WM2:.0f} W/m2."))
    if spread > MAX_SPREAD_FRACTION:
        warnings.append(Warning_("unstable_irradiance", f"Irradiance readings spread by {spread*100:.0f}%, above {MAX_SPREAD_FRACTION*100:.0f}%."))
    if (s.sky_condition or "").strip().lower() in CLOUDY_SKY:
        warnings.append(Warning_("cloudy_sky", f"Sky condition recorded as {s.sky_condition}."))

    k_site = float(np.mean(k_site_values))
    if not (K_SITE_RANGE[0] <= k_site <= K_SITE_RANGE[1]):
        warnings.append(Warning_("k_site_out_of_range", f"Site factor {k_site:.3f} is outside the expected range {K_SITE_RANGE[0]:.2f}-{K_SITE_RANGE[1]:.2f}."))

    low_conf = any(w.code in {"low_irradiance", "unstable_irradiance", "cloudy_sky", "k_site_out_of_range", "few_readings"} for w in warnings)

    return ReadingSetResult(
        label=s.label, face_id=s.face_id,
        k_raw_values=k_raw_values, k_raw=float(np.mean(k_raw_values)),
        eta_rel_values=eta_values, k_site_values=k_site_values, k_site=k_site,
        avg_irradiance_wm2=avg_g, irradiance_spread_fraction=spread, avg_module_temp_c=avg_t, module_temp_source=module_temp_source,
        ambient_temp_c=ambient, ambient_source=ambient_source,
        rise_per_kw_values=rise_values, rise_per_kw=rise, rise_is_plausible=plausible,
        warnings=warnings, low_confidence=low_conf, valid=True,
    )


def select_site_set(results: list[ReadingSetResult]) -> Optional[int]:
    """Index of the reading set that supplies the site k: the highest k_site.

    Owner's rule: the face that measures best is the source of k for the site.
    """
    best: Optional[int] = None
    for i, r in enumerate(results):
        if not r.valid or not np.isfinite(r.k_site):
            continue
        if best is None or r.k_site > results[best].k_site:
            best = i
    return best
