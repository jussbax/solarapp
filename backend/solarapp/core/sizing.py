"""System sizing from the reconciled load profile and the roof's production profile.

All systems are hybrid inverters. The owner chooses net metering, battery
only (no export; surplus beyond the battery is lost), or the combination.
Target: net-zero annual energy, or whatever the roof can provide.

* PV: kWp = annual consumption / annual yield per kWp, capped by the roof,
  rounded to whole panels of the chosen model.
* Battery: usable capacity equal to the largest daily surplus-to-night shift
  over the twelve typical days, rounded up to whole modules, within a cap.
* Inverter: smallest catalogue size that covers the nameplate coincident
  peak, the surge of the largest motor at the stated surge factor, and the
  PV array at the allowed PV-to-inverter ratio. Parallel units if needed.
* Hour-by-hour balance per typical month day: direct use, battery charge and
  discharge, export or curtailment, grid import. Coverage and
  self-consumption follow from it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .audit import DAYS_IN_MONTH

SYSTEM_KINDS = ("net_metering", "battery_only", "combination")


@dataclass
class BatterySpec:
    module_kwh: float = 5.12
    depth_of_discharge: float = 0.90
    round_trip_efficiency: float = 0.92
    max_c_rate: float = 0.5          # kW of charge or discharge per kWh installed
    max_modules: int = 8


@dataclass
class InverterRules:
    sizes_kw: list[float] = field(default_factory=lambda: [6.0, 8.0, 10.0, 12.0])
    surge_factor: float = 2.0        # 200% of rated
    pv_ratio_max: float = 1.3        # PV kWp per inverter kW


@dataclass
class DayBalance:
    load: np.ndarray
    production: np.ndarray
    direct: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    soc: np.ndarray
    export: np.ndarray
    curtailed: np.ndarray
    imported: np.ndarray


def balance_day(load_kw: np.ndarray, prod_kw: np.ndarray, usable_kwh: float, power_kw: float, kind: str, eff_rt: float) -> DayBalance:
    """Steady-state hourly balance of one typical day (the day is repeated until the battery state settles)."""
    eff = math.sqrt(max(eff_rt, 1e-6))
    soc = 0.0
    n = 24
    arrays = {k: np.zeros(n) for k in ("direct", "charge", "discharge", "soc", "export", "curtailed", "imported")}
    for cycle in range(4):
        for h in range(n):
            p, l = float(prod_kw[h]), float(load_kw[h])
            direct = min(p, l)
            surplus, deficit = p - direct, l - direct
            charge = discharge = 0.0
            if usable_kwh > 0:
                charge = min(surplus, (usable_kwh - soc) / eff, power_kw)
                soc += charge * eff
                discharge = min(deficit, soc * eff, power_kw)
                soc -= discharge / eff
            rest = surplus - charge
            export = rest if kind in ("net_metering", "combination") else 0.0
            curtailed = rest - export
            imported = deficit - discharge
            if cycle == 3:
                arrays["direct"][h], arrays["charge"][h], arrays["discharge"][h] = direct, charge, discharge
                arrays["soc"][h], arrays["export"][h], arrays["curtailed"][h], arrays["imported"][h] = soc, export, curtailed, imported
    return DayBalance(load=np.asarray(load_kw, float), production=np.asarray(prod_kw, float), **arrays)


def pick_inverter(required_kw: float, rules: InverterRules) -> tuple[float, int]:
    sizes = sorted(rules.sizes_kw)
    for s in sizes:
        if s >= required_kw - 1e-9:
            return s, 1
    biggest = sizes[-1]
    return biggest, int(math.ceil(required_kw / biggest))


def size_system(
    load_kw: np.ndarray,            # [12, 24] kW
    prod_per_kwp_kw: np.ndarray,    # [12, 24] kW per kWp of the roof's selected configuration
    roof_max_panels: int,
    panel_wp: float,
    kind: str,
    peak_load_kw: float,
    largest_motor_kw: float,
    largest_motor_multiplier: float,
    battery: BatterySpec | None = None,
    inverter: InverterRules | None = None,
) -> dict:
    battery = battery or BatterySpec()
    inverter = inverter or InverterRules()
    if kind not in SYSTEM_KINDS:
        raise ValueError(f"unknown system kind {kind!r}")
    load = np.asarray(load_kw, float)
    per_kwp = np.asarray(prod_per_kwp_kw, float)
    days = np.array(DAYS_IN_MONTH, float)
    warnings: list[dict] = []

    annual_consumption = float((load.sum(axis=1) * days).sum())
    yield_per_kwp = float((per_kwp.sum(axis=1) * days).sum())
    roof_max_kwp = roof_max_panels * panel_wp / 1000.0

    target_kwp = annual_consumption / yield_per_kwp if yield_per_kwp > 0 else 0.0
    target_panels = int(math.ceil(target_kwp * 1000.0 / panel_wp)) if panel_wp > 0 else 0
    panels = max(min(target_panels, roof_max_panels), 0)
    roof_limited = target_panels > roof_max_panels
    kwp = panels * panel_wp / 1000.0
    if roof_limited:
        warnings.append({"code": "roof_limited", "message": f"Net-zero needs about {target_kwp:.1f} kWp but the roof holds {roof_max_kwp:.2f} kWp; the system is sized to what the roof can provide."})
    if panels == 0:
        warnings.append({"code": "no_pv", "message": "No panels fit or there is no consumption to cover."})

    prod = per_kwp * kwp

    # --- battery: largest daily swing the surplus-to-night shift needs
    modules = 0
    usable = 0.0
    if kind in ("battery_only", "combination") and kwp > 0:
        swings = []
        big = 1e6
        for m in range(12):
            b = balance_day(load[m], prod[m], big, big, kind, battery.round_trip_efficiency)
            swings.append(float(b.soc.max() - b.soc.min()))
        need = max(swings) if swings else 0.0
        per_module = battery.module_kwh * battery.depth_of_discharge
        modules = int(math.ceil(need / per_module)) if per_module > 0 else 0
        if modules > battery.max_modules:
            warnings.append({"code": "battery_capped", "message": f"The surplus-to-night shift would need {modules} modules; capped at {battery.max_modules}."})
            modules = battery.max_modules
        usable = modules * per_module
    battery_power = modules * battery.module_kwh * battery.max_c_rate

    # --- hourly balance with the chosen system
    monthly = []
    profiles = {}
    tot = {k: 0.0 for k in ("consumption", "production", "direct", "charge", "discharge", "export", "curtailed", "imported")}
    for m in range(12):
        b = balance_day(load[m], prod[m], usable, battery_power, kind, battery.round_trip_efficiency)
        row = {
            "month": m + 1, "days": int(days[m]),
            "consumption_kwh": float(b.load.sum() * days[m]), "production_kwh": float(b.production.sum() * days[m]),
            "direct_kwh": float(b.direct.sum() * days[m]), "battery_kwh": float(b.discharge.sum() * days[m]),
            "export_kwh": float(b.export.sum() * days[m]), "curtailed_kwh": float(b.curtailed.sum() * days[m]),
            "import_kwh": float(b.imported.sum() * days[m]),
        }
        monthly.append(row)
        for k, key in (("consumption", "consumption_kwh"), ("production", "production_kwh"), ("direct", "direct_kwh"), ("discharge", "battery_kwh"), ("export", "export_kwh"), ("curtailed", "curtailed_kwh"), ("imported", "import_kwh")):
            tot[k] += row[key]
        tot["charge"] += float(b.charge.sum() * days[m])
        profiles[m + 1] = {
            "load": b.load.round(4).tolist(), "production": b.production.round(4).tolist(), "direct": b.direct.round(4).tolist(),
            "charge": b.charge.round(4).tolist(), "discharge": b.discharge.round(4).tolist(), "soc": b.soc.round(4).tolist(),
            "export": b.export.round(4).tolist(), "curtailed": b.curtailed.round(4).tolist(), "imported": b.imported.round(4).tolist(),
        }
    served = tot["direct"] + tot["discharge"]
    coverage_pct = served / tot["consumption"] * 100.0 if tot["consumption"] > 0 else 0.0
    self_consumption_pct = (tot["direct"] + tot["charge"]) / tot["production"] * 100.0 if tot["production"] > 0 else 0.0
    net_kwh = tot["production"] - tot["consumption"] if kind != "battery_only" else served - tot["consumption"]

    # --- inverter
    surge_req = (peak_load_kw + largest_motor_kw * (largest_motor_multiplier - 1.0)) / inverter.surge_factor if inverter.surge_factor > 0 else peak_load_kw
    pv_req = kwp / inverter.pv_ratio_max if inverter.pv_ratio_max > 0 else kwp
    required = max(peak_load_kw, surge_req, pv_req)
    inv_kw, inv_units = pick_inverter(required, inverter) if required > 0 else (min(inverter.sizes_kw), 1)
    if inv_units > 1:
        warnings.append({"code": "inverter_parallel", "message": f"Requirement of {required:.1f} kW exceeds the largest catalogue size; {inv_units} x {inv_kw:g} kW in parallel."})
    binding = "peak load" if required == peak_load_kw else ("motor surge" if required == surge_req else "PV array")

    return {
        "kind": kind,
        "annual_consumption_kwh": annual_consumption,
        "annual_yield_kwh_per_kwp": yield_per_kwp,
        "target_kwp": target_kwp,
        "target_panels": target_panels,
        "roof_max_panels": roof_max_panels,
        "roof_max_kwp": roof_max_kwp,
        "roof_limited": roof_limited,
        "panels": panels,
        "kwp": kwp,
        "annual_production_kwh": tot["production"],
        "coverage_pct": coverage_pct,
        "self_consumption_pct": self_consumption_pct,
        "annual_direct_kwh": tot["direct"],
        "annual_battery_kwh": tot["discharge"],
        "annual_export_kwh": tot["export"],
        "annual_curtailed_kwh": tot["curtailed"],
        "annual_import_kwh": tot["imported"],
        "net_annual_kwh": net_kwh,
        "battery": {
            "modules": modules, "module_kwh": battery.module_kwh, "installed_kwh": modules * battery.module_kwh,
            "usable_kwh": usable, "power_kw": battery_power, "depth_of_discharge": battery.depth_of_discharge,
            "round_trip_efficiency": battery.round_trip_efficiency,
        },
        "inverter": {
            "size_kw": inv_kw, "units": inv_units, "required_kw": required, "binding": binding,
            "peak_load_kw": peak_load_kw, "surge_requirement_kw": surge_req, "pv_requirement_kw": pv_req,
            "largest_motor_kw": largest_motor_kw, "largest_motor_multiplier": largest_motor_multiplier,
            "surge_factor": inverter.surge_factor, "pv_ratio_max": inverter.pv_ratio_max, "sizes_kw": inverter.sizes_kw,
        },
        "monthly": monthly,
        "profiles": profiles,
        "warnings": warnings,
    }
