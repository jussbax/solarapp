"""The checks the datasheet figures unlock (round 12, docs/audits/round-12/engineer-brief.md, section 3): plain
functions the BOQ generator calls, each falling back to today's behaviour when a figure is absent. Every rule
carries its source as the brief gives it; every default is an assumption and says so in its warning.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .config import StringDesign


# ---------------------------------------------------------------- the design temperatures (section 3, head)

def faiman_rise_c_per_kw(u0: float, u1: float, wind_ms: float) -> float:
    """The module's rise above the air at 1 kW/m² under the Faiman model the simulation uses when the k readings give
    no plausible site rise: T_mod − T_air = G / (u0 + u1 · v), at G = 1 kW/m² and the typical year's mean wind."""
    return 1000.0 / (u0 + u1 * max(float(wind_ms), 0.0))


def design_temperatures(sd: StringDesign, cold_override: Optional[float], hot_override: Optional[float], tmy_min_c: Optional[float],
                        tmy_max_c: Optional[float], rise_c_per_kw: Optional[float]) -> dict:
    """Per project: T_cold = min(setting, floor(TMY minimum of the project's cell) − margin) and
    T_hot = max(setting, TMY maximum + rise × 1 kW/m²); the project's own figure (doc.pricing) stands in for the
    setting. The website estimate has no project and uses the settings alone (brief 4.5)."""
    cold_setting = float(cold_override) if cold_override is not None else float(sd.design_cold_c)
    hot_setting = float(hot_override) if hot_override is not None else float(sd.design_hot_cell_c)
    t_cold, cold_source = cold_setting, "project" if cold_override is not None else "setting"
    t_hot, hot_source = hot_setting, "project" if hot_override is not None else "setting"
    tmy_cold = tmy_hot = None
    if tmy_min_c is not None:
        tmy_cold = math.floor(float(tmy_min_c)) - float(sd.cold_margin_c)
        if tmy_cold < t_cold:
            t_cold, cold_source = tmy_cold, "tmy"
    if tmy_max_c is not None and rise_c_per_kw is not None:
        tmy_hot = float(tmy_max_c) + float(rise_c_per_kw)
        if tmy_hot > t_hot:
            t_hot, hot_source = tmy_hot, "tmy"
    return {
        "t_cold_c": t_cold, "t_hot_c": t_hot, "cold_source": cold_source, "hot_source": hot_source,
        "cold_setting_c": cold_setting, "hot_setting_c": hot_setting, "cold_margin_c": float(sd.cold_margin_c),
        "tmy_min_air_c": None if tmy_min_c is None else float(tmy_min_c), "tmy_max_air_c": None if tmy_max_c is None else float(tmy_max_c),
        "tmy_cold_c": tmy_cold, "tmy_hot_cell_c": tmy_hot, "rise_c_per_kw": None if rise_c_per_kw is None else float(rise_c_per_kw),
    }
