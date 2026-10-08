"""Quick estimate from four answers: goal, location, monthly consumption, usage pattern.

No roof or meter readings: a typical roof (tilt, facing) and a typical site factor
from the settings, a load shape for the pattern scaled to the monthly kWh, then
the same sizing, bill of materials, pricing and economics as the full assessment.
Customer-facing numbers only come out of it.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import numpy as np

from ..core.dataset import PvgisDataset
from ..core.simulation import FaceSpec, ThermalModel, prepare_sky, simulate
from ..core.sizing import BatterySpec, InverterRules, OffGridRules, size_system
from ..pricing.boq import BoqRequest, generate_boq, rows_for
from ..pricing.economics import build_economics
from ..pricing.engine import JobInputs, price_job
from ..pricing.job import PricingContext, extra_km_from_pin
from ..schemas import AssessmentDoc, BillEntry, EnergyAudit, QuickRequest

# share of the day's energy per hour, 0 to 23
SHAPES = {
    "morning": [0.6, 0.5, 0.5, 0.5, 0.6, 1.2, 2.2, 2.6, 2.4, 2.0, 1.6, 1.4, 1.3, 1.2, 1.1, 1.0, 1.0, 1.2, 1.4, 1.3, 1.1, 0.9, 0.8, 0.7],
    "balanced": [0.7, 0.6, 0.6, 0.6, 0.6, 0.8, 1.2, 1.4, 1.3, 1.2, 1.2, 1.3, 1.3, 1.2, 1.2, 1.2, 1.2, 1.4, 1.8, 1.9, 1.7, 1.4, 1.1, 0.9],
    "evening": [0.8, 0.6, 0.5, 0.5, 0.5, 0.6, 0.9, 1.0, 0.8, 0.7, 0.7, 0.8, 0.8, 0.7, 0.7, 0.8, 1.0, 1.6, 2.6, 3.0, 2.8, 2.2, 1.6, 1.1],
}
PATTERN_LABEL = {"morning": "mostly in the morning", "balanced": "spread through the day", "evening": "mostly in the evening"}
GOAL_LABEL = {"net_metering": "grid-tied with net metering", "combination": "net metering with a battery", "off_grid": "off-grid with a battery"}
_per_kwp_cache: dict[tuple, list] = {}


def load_profile(monthly_kwh: float, pattern: str) -> np.ndarray:
    shape = np.array(SHAPES.get(pattern) or SHAPES["balanced"], dtype=float)
    shape = shape / shape.sum()
    daily = monthly_kwh / 30.4
    return np.tile(shape * daily, (12, 1))  # [12, 24] kW, the same every month


def per_kwp_profile(pvgis: PvgisDataset, lat: float, lon: float, tilt: float, azimuth: float, k_site: float) -> tuple[np.ndarray, dict]:
    cell = pvgis.nearest_cell(lat, lon)
    if cell is None:
        raise ValueError("No weather data for this location.")
    key = (cell.id, round(tilt, 1), round(azimuth, 1), round(k_site, 3))
    if key not in _per_kwp_cache:
        tmy = pvgis.load_tmy(cell)
        sky = prepare_sky(tmy, cell.lat, cell.lon, cell.elevation_m, cell.time_offset_h)
        face = FaceSpec("quick", "Roof", tilt, azimuth, 1)
        res = simulate(tmy, cell.lat, cell.lon, cell.elevation_m, [face], 1000.0, k_site, ThermalModel(), sky=sky)
        _per_kwp_cache[key] = [np.array(res.hourly_profile_kw), res.annual_kwh, res.monthly_kwh]
    prof, annual, monthly = _per_kwp_cache[key]
    return prof, {"cell_id": cell.id, "distance_km": cell.distance_km, "annual_kwh_per_kwp": annual, "monthly_kwh_per_kwp": monthly}


def quick_estimate(req: QuickRequest, pvgis: PvgisDataset, ctx: PricingContext) -> dict:
    cfg, catalog = ctx.config, ctx.catalog
    q = cfg.quick
    assumptions: list[str] = []
    warnings: list[str] = []
    tariff = cfg.economics.tariff_php_per_kwh
    if req.monthly_kwh:
        monthly_kwh = float(req.monthly_kwh)
        if req.monthly_php:
            tariff = float(req.monthly_php) / monthly_kwh
    elif req.monthly_php:
        monthly_kwh = float(req.monthly_php) / tariff
        assumptions.append(f"Your bill of PHP {req.monthly_php:,.0f} is taken as about {monthly_kwh:,.0f} kWh at {tariff:.2f} PHP per kWh.")
    else:
        raise ValueError("Give the monthly consumption in kWh or the bill in pesos.")

    panel = catalog.get(q.panel_code)
    if panel is None or not panel.rating:
        raise ValueError("The quick estimate's panel is not in the materials database.")
    panel_wp = float(panel.rating)
    per_kwp, loc = per_kwp_profile(pvgis, req.lat, req.lon, q.tilt_deg, q.azimuth_deg, q.k_site)
    load = load_profile(monthly_kwh, req.pattern)
    peak = float(load.max() * q.peak_factor)
    s = cfg_sizing = size_system(
        load, per_kwp, roof_max_panels=q.max_panels, panel_wp=panel_wp, kind=req.goal, peak_load_kw=peak,
        largest_motor_kw=0.0, largest_motor_multiplier=1.0, battery=BatterySpec(), inverter=InverterRules(), offgrid=OffGridRules(),
    )
    panels = int(s["panels"])
    if panels <= 0:
        raise ValueError("The consumption is too small to size a system.")
    if s.get("roof_limited"):
        warnings.append(f"This needs more than {q.max_panels} panels; the estimate is capped there. The full assessment measures your roof.")
    dim = float(panel.panel_length_m or 2.278)
    width = float(panel.panel_width_m or 1.134)
    rows = rows_for(panels, q.panels_per_row, dim)
    inv = s["inverter"]
    bat_kwh = float(s["battery"]["installed_kwh"]) if req.goal != "net_metering" else 0.0
    boq = generate_boq(BoqRequest(panel.code, panels, rows, inverter_kw=float(inv["size_kw"]), inverter_units=int(inv["units"]),
                                  inverter_required_kw=float(inv.get("required_kw") or 0) or None, battery_kwh=bat_kwh), catalog, cfg)
    pin = extra_km_from_pin(req.lat, req.lon, cfg)
    d = cfg.job_defaults
    job = JobInputs(roof_factor=d.roof_factor, roof_closed_days=d.roof_closed_days, max_days=d.max_days, max_pairs=d.max_pairs,
                    battery_haul_hours=d.battery_haul_hours, owner_days=d.owner_days, extra_km=pin["extra_km"] if pin else d.extra_km,
                    extra_toll=d.extra_toll, net_metering=req.goal != "off_grid")
    priced = price_job(boq.lines, catalog, cfg, job)
    priced["available"] = True
    today = date.today()
    doc = AssessmentDoc(audit=EnergyAudit(bills=[BillEntry(id="q", billing_month=today.strftime("%Y-%m"), kwh=monthly_kwh, amount_php=monthly_kwh * tariff)]))
    daily = [monthly_kwh / 30.4] * 12
    eco = build_economics(doc, {"sizing": s, "pricing": priced, "audit": {"future_daily_kwh": 0.0, "daily_kwh_by_month": daily}}, cfg)
    cust = priced["customer"]
    sections = {x["key"]: x["amount"] for x in cust["sections"]}
    total = float(cust["total"])
    rounded = float(np.ceil(total / q.price_round_to) * q.price_round_to) if q.price_round_to > 0 else total
    area = panels * dim * width
    assumptions += [
        f"A {GOAL_LABEL[req.goal]} system sized to your consumption, used {PATTERN_LABEL[req.pattern]}.",
        f"A typical roof facing {'south' if q.azimuth_deg == 180 else str(q.azimuth_deg) + ' degrees'} at {q.tilt_deg:g} degrees, panels performing at {q.k_site * 100:.0f}% of the standard model, from PVGIS weather records for this location.",
        f"Prices from our current materials list and a {pin['road_km']:.0f} km trip from Pila, Laguna." if pin else "Prices from our current materials list.",
        f"Electricity at {tariff:.2f} PHP per kWh rising {cfg.economics.tariff_escalation * 100:.0f}% a year" + (f", export credited at {cfg.economics.export_rate_php_per_kwh:.2f} PHP per kWh under net metering." if req.goal != "off_grid" else "."),
    ]
    return {
        "inputs": {"goal": req.goal, "goal_label": GOAL_LABEL[req.goal], "pattern": req.pattern, "pattern_label": PATTERN_LABEL[req.pattern],
                   "monthly_kwh": monthly_kwh, "tariff_php_per_kwh": tariff, "lat": req.lat, "lon": req.lon},
        "location": {"distance_km": loc["distance_km"], "sun_kwh_per_kwp_year": loc["annual_kwh_per_kwp"]},
        "system": {
            "panels": panels, "panel_wp": panel_wp, "panel_name": panel.name, "kwp": float(s["kwp"]),
            "inverter_kw": float(inv["size_kw"]), "inverter_units": int(inv["units"]), "battery_kwh": bat_kwh,
            "roof_area_m2": area, "roof_limited": bool(s.get("roof_limited")),
        },
        "production": {
            "annual_kwh": float(s["annual_production_kwh"]), "monthly_kwh": [m["production_kwh"] for m in s["monthly"]],
            "coverage_pct": float(s["coverage_pct"]), "self_consumption_pct": float(s["self_consumption_pct"]),
            "annual_export_kwh": float(s["annual_export_kwh"]), "annual_import_kwh": float(s["annual_import_kwh"]),
            "annual_unserved_kwh": float(s["annual_unserved_kwh"]), "annual_consumption_kwh": float(s["annual_consumption_kwh"]),
        },
        "price": {"total": rounded, "materials": sections.get("materials", 0.0), "labor": sections.get("labor", 0.0),
                  "equipment": sections.get("equipment", 0.0), "tax": sections.get("tax", 0.0), "price_per_wp": rounded / (float(s["kwp"]) * 1000.0)},
        "economics": {
            "bill_before_monthly": eco["bill_before_monthly"], "bill_after_monthly": eco["bill_after_monthly"], "savings_monthly": eco["savings_monthly"],
            "savings_year1": eco["year1"]["savings"], "payback_years": eco["payback_years"], "lifetime_net": eco["lifetime_net"],
            "analysis_years": eco["assumptions"]["analysis_years"], "irr": eco["irr"], "co2_t_per_year": eco["co2_t_per_year"],
        } if eco.get("available") else None,
        "assumptions": assumptions,
        "warnings": warnings,
    }
