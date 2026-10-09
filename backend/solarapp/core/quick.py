"""Free estimate from four answers: goal, location, monthly consumption, usage pattern.

No roof or meter readings: a typical roof (tilt, facing) and a typical site factor
from the settings, a load shape for the pattern scaled to the monthly kWh, then
the same sizing, bill of materials, pricing and economics as the full assessment.
Customer-facing numbers only come out of it. For the two net-metering goals the
other one is worked out too, so the page can show the battery as a priced add-on.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import numpy as np

from ..core.dataset import PvgisDataset
from ..core.simulation import FaceSpec, ThermalModel, prepare_sky, simulate
from ..core.sizing import BatterySpec, InverterRules, OffGridRules, size_system
from ..core.towns import find_town, nearest_town
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
GOAL_LABEL = {"net_metering": "solar with net metering, no battery", "combination": "solar with a battery and net metering", "off_grid": "battery first, nothing sold back (the grid as backup)"}
NIGHT_HOURS = list(range(18, 24)) + list(range(0, 6))   # 6 pm to 6 am, the night the battery is asked to carry
OUT_OF_AREA_KM = 25.0
# Under this a system is one panel and a ₱180,000 inverter: refused with a plain message instead of a silly figure.
MIN_MONTHLY_KWH = 60.0
TOO_LITTLE = "That's very little usage; a solar system would not pay for itself. If the kWh on your bill is higher, enter that figure."
_per_kwp_cache: dict[tuple, list] = {}


def load_profile(monthly_kwh: float, pattern: str) -> np.ndarray:
    shape = np.array(SHAPES.get(pattern) or SHAPES["balanced"], dtype=float)
    shape = shape / shape.sum()
    daily = monthly_kwh / 30.4
    return np.tile(shape * daily, (12, 1))  # [12, 24] kW, the same every month


def battery_note(battery_kwh: float, monthly_kwh: float, pattern: str, depth_of_discharge: float) -> dict:
    """What the battery carries, from the pattern shape scaled to the monthly kWh (there is no audit on the website):
    night = the shape's share from 6 pm to 6 am of a day's use; usable = the priced battery × the depth of discharge
    the sizing designs to. The proposal does the same sum from the audit's hourly balance."""
    if battery_kwh < 0.5:
        return {"night_kwh": 0.0, "usable_kwh": 0.0, "hours": None, "text": ""}
    shape = np.array(SHAPES.get(pattern) or SHAPES["balanced"], dtype=float)
    night = float(shape[NIGHT_HOURS].sum() / shape.sum() * monthly_kwh / 30.4)
    usable = battery_kwh * depth_of_discharge
    if usable >= night:
        return {"night_kwh": night, "usable_kwh": usable, "hours": None, "text": "enough for a typical night of your use when the grid is down"}
    hours = usable / (night / len(NIGHT_HOURS))
    return {"night_kwh": night, "usable_kwh": usable, "hours": hours, "text": f"about {hours:.0f} hours of your evening use when the grid is down"}


def per_kwp_profile(pvgis: PvgisDataset, lat: float, lon: float, tilt: float, azimuth: float, k_site: float) -> tuple[np.ndarray, dict]:
    cell = pvgis.nearest_cell(lat, lon)
    if cell is None:
        raise ValueError("We don't have sun records for that spot. Check that the pin is on your house in the Philippines.")
    key = (cell.id, round(tilt, 1), round(azimuth, 1), round(k_site, 3))
    if key not in _per_kwp_cache:
        if len(_per_kwp_cache) >= 256:
            _per_kwp_cache.pop(next(iter(_per_kwp_cache)))
        tmy = pvgis.load_tmy(cell)
        sky = prepare_sky(tmy, cell.lat, cell.lon, cell.elevation_m, cell.time_offset_h)
        face = FaceSpec("quick", "Roof", tilt, azimuth, 1)
        res = simulate(tmy, cell.lat, cell.lon, cell.elevation_m, [face], 1000.0, k_site, ThermalModel(), sky=sky)
        _per_kwp_cache[key] = [np.array(res.hourly_profile_kw), res.annual_kwh, res.monthly_kwh]
    prof, annual, monthly = _per_kwp_cache[key]
    return prof, {"cell_id": cell.id, "distance_km": cell.distance_km, "annual_kwh_per_kwp": annual, "monthly_kwh_per_kwp": monthly}


def resolve_location(req: QuickRequest) -> dict:
    """A town name or a pin -> lat, lon, the town label, and whether it is in the usual area."""
    if req.town:
        t = find_town(req.town, req.province)
        if t is None:
            raise ValueError("Please pick your town from the list, or use your phone's location.")
        return {"lat": t[2], "lon": t[3], "town": t[0], "province": t[1], "label": f"{t[0]}, {t[1]}", "in_area": True, "km_to_listed_town": 0.0}
    if req.lat is None or req.lon is None:
        raise ValueError("Tell us where the house is: pick your town or use your phone's location.")
    t, km = nearest_town(req.lat, req.lon)
    in_area = km <= OUT_OF_AREA_KM
    label = f"near {t[0]}, {t[1]}" if in_area else "outside Laguna and Batangas"
    return {"lat": req.lat, "lon": req.lon, "town": t[0] if in_area else "", "province": t[1] if in_area else "", "label": label, "in_area": in_area, "km_to_listed_town": km}


def _consumption(req: QuickRequest, default_tariff: float) -> tuple[float, float, Optional[str]]:
    if req.monthly_kwh:
        kwh = float(req.monthly_kwh)
        tariff = float(req.monthly_php) / kwh if req.monthly_php else default_tariff
        note = None
    elif req.monthly_php:
        kwh = float(req.monthly_php) / default_tariff
        tariff = default_tariff
        note = f"We read your ₱{req.monthly_php:,.0f} bill as about {kwh:,.0f} kWh, at ₱{default_tariff:.2f} per kWh."
    else:
        raise ValueError("Enter the kWh from your bill, or the amount you paid.")
    if kwh < MIN_MONTHLY_KWH:
        raise ValueError(TOO_LITTLE)
    return kwh, tariff, note


def _priced_battery_kwh(boq, catalog, required_kwh: float) -> float:
    """The battery the price includes: units times the catalogue rating, so the website figure and the proposal agree."""
    if required_kwh <= 0:
        return 0.0
    code, units = boq.choices.get("battery_code"), int(boq.choices.get("battery_units") or 0)
    item = catalog.get(code) if code else None
    if item is None or not item.rating or units <= 0:
        raise LookupError("No battery in the materials list covers the estimate; add one with its kWh rating on the Materials page.")
    return float(units * item.rating)


def battery_part_for(priced: dict, vat: float) -> float:
    """The battery's share of the price as the proposal prints it: the customer's battery line (its freight and
    commission shares inside) plus VAT. One figure for the website hero, the "add a battery" line and the proposal."""
    items = [i for s in priced["customer"]["sections"] for i in s.get("items", []) if i.get("key") == "Battery"]
    return sum(float(i["amount"]) for i in items) * (1 + vat)


def _estimate_once(goal: str, pattern: str, monthly_kwh: float, tariff: float, lat: float, lon: float, pvgis: PvgisDataset, ctx: PricingContext) -> dict:
    """Size, price and value one system kind. Returns the customer-facing block for that kind."""
    cfg, catalog = ctx.config, ctx.catalog
    q = cfg.quick
    panel = catalog.get(q.panel_code)
    if panel is None or not panel.rating:
        raise LookupError("The estimate's panel code is not in the materials list; set it under Pricing settings › Quick estimate.")
    panel_wp = float(panel.rating)
    per_kwp, loc = per_kwp_profile(pvgis, lat, lon, q.tilt_deg, q.azimuth_deg, q.k_site)
    loss = cfg.system_losses.factor
    load = load_profile(monthly_kwh, pattern)
    peak = float(load.max() * q.peak_factor)
    s = size_system(
        load, per_kwp * loss, roof_max_panels=q.max_panels, panel_wp=panel_wp, kind=goal, peak_load_kw=peak,   # sized at the meter
        largest_motor_kw=0.0, largest_motor_multiplier=1.0, battery=BatterySpec(days_of_autonomy=cfg.sizing.days_of_autonomy),
        inverter=InverterRules(), offgrid=OffGridRules(),
    )
    panels = int(s["panels"])
    if panels <= 0:
        raise ValueError("That's too little usage for a solar system to pay off. Check the kWh on your bill.")
    dim = float(panel.panel_length_m or 2.278)
    width = float(panel.panel_width_m or 1.134)
    rows = rows_for(panels, q.panels_per_row, dim)
    inv = s["inverter"]
    # the sizing's nominal kWh picks the unit; the visitor sees the unit the price includes
    required_kwh = float(s["battery"]["installed_kwh"]) if goal != "net_metering" else 0.0
    boq = generate_boq(BoqRequest(panel.code, panels, rows, inverter_kw=float(inv["size_kw"]), inverter_units=int(inv["units"]),
                                  inverter_required_kw=float(inv.get("required_kw") or 0) or None, battery_kwh=required_kwh, kind=goal), catalog, cfg)
    bat_kwh = _priced_battery_kwh(boq, catalog, required_kwh)
    carries = battery_note(bat_kwh, monthly_kwh, pattern, float(s["battery"].get("depth_of_discharge") or 0.85))
    pin = extra_km_from_pin(lat, lon, cfg)
    d = cfg.job_defaults
    job = JobInputs(roof_factor=d.roof_factor, roof_closed_days=d.roof_closed_days, max_days=d.max_days, max_pairs=d.max_pairs,
                    battery_haul_hours=d.battery_haul_hours, owner_days=d.owner_days, extra_km=pin["extra_km"] if pin else d.extra_km,
                    extra_toll=d.extra_toll, net_metering=goal != "off_grid")
    priced = price_job(boq.lines, catalog, cfg, job)
    priced["available"] = True
    today = date.today()
    doc = AssessmentDoc(audit=EnergyAudit(bills=[BillEntry(id="q", billing_month=today.strftime("%Y-%m"), kwh=monthly_kwh, amount_php=monthly_kwh * tariff)]))
    daily = [monthly_kwh / 30.4] * 12
    eco = build_economics(doc, {"sizing": s, "pricing": priced, "audit": {"future_daily_kwh": 0.0, "daily_kwh_by_month": daily}}, cfg, ctx.profile)
    cust = priced["customer"]
    sections = {x["key"]: x["amount"] for x in cust["sections"]}
    total = float(cust["total"])
    rounded = float(np.ceil(total / q.price_round_to) * q.price_round_to) if q.price_round_to > 0 else total
    battery_share = battery_part_for(priced, cfg.job.vat)   # the proposal's own battery figure, not rounded here
    return {
        "goal": goal, "goal_label": GOAL_LABEL[goal],
        "location": {"distance_km": loc["distance_km"], "sun_kwh_per_kwp_year": loc["annual_kwh_per_kwp"], "road_km": pin["road_km"] if pin else None},
        "system": {
            "panels": panels, "panel_wp": panel_wp, "panel_name": panel.name, "kwp": float(s["kwp"]),
            "inverter_kw": float(inv["size_kw"]), "inverter_units": int(inv["units"]), "battery_kwh": bat_kwh,
            "roof_area_m2": panels * dim * width, "roof_limited": bool(s.get("roof_limited")),
            "battery_note": carries["text"], "battery_night_kwh": carries["night_kwh"], "battery_usable_kwh": carries["usable_kwh"],
        },
        "production": {
            "annual_kwh": float(s["annual_production_kwh"]), "monthly_kwh": [m["production_kwh"] for m in s["monthly"]],   # at the meter
            "loss_factor": loss, "annual_kwh_at_panels": float(s["annual_production_kwh"]) / loss if loss > 0 else float(s["annual_production_kwh"]),
            "coverage_pct": float(s["coverage_pct"]), "self_consumption_pct": float(s["self_consumption_pct"]),
            "annual_export_kwh": float(s["annual_export_kwh"]), "annual_import_kwh": float(s["annual_import_kwh"]),
            "annual_unserved_kwh": float(s["annual_unserved_kwh"]), "annual_consumption_kwh": float(s["annual_consumption_kwh"]),
            "production_vs_use_pct": 100.0 * float(s["annual_production_kwh"]) / max(float(s["annual_consumption_kwh"]), 1.0),
        },
        "price": {"total": rounded, "materials": sections.get("materials", 0.0), "labor": sections.get("labor", 0.0),
                  "equipment": sections.get("equipment", 0.0), "tax": sections.get("tax", 0.0), "price_per_wp": rounded / (float(s["kwp"]) * 1000.0),
                  "battery_part": battery_share},
        "economics": {
            "bill_before_monthly": eco["bill_before_monthly"], "bill_after_monthly": eco["bill_after_monthly"], "savings_monthly": eco["savings_monthly"],
            "savings_year1": eco["year1"]["savings"], "payback_years": eco["payback_years"], "lifetime_net": eco["lifetime_net"],
            "analysis_years": eco["assumptions"]["analysis_years"], "irr": eco["irr"], "co2_t_per_year": eco["co2_t_per_year"],
        } if eco.get("available") else None,
    }


def quick_estimate(req: QuickRequest, pvgis: PvgisDataset, ctx: PricingContext) -> dict:
    cfg = ctx.config
    q = cfg.quick
    assumptions: list[str] = []
    warnings: list[str] = []
    where = resolve_location(req)
    monthly_kwh, tariff, note = _consumption(req, cfg.economics.tariff_php_per_kwh)
    if note:
        assumptions.append(note)
    main = _estimate_once(req.goal, req.pattern, monthly_kwh, tariff, where["lat"], where["lon"], pvgis, ctx)
    alternative = None
    other = {"net_metering": "combination", "combination": "net_metering"}.get(req.goal)
    if other:
        try:
            alternative = _estimate_once(other, req.pattern, monthly_kwh, tariff, where["lat"], where["lon"], pvgis, ctx)
        except (ValueError, LookupError):
            alternative = None
    if main["system"]["roof_limited"]:
        warnings.append(f"Your usage needs more than {q.max_panels} panels. We capped the estimate at {q.max_panels}. On the roof visit we'll see how many your roof can really take.")
    if not where["in_area"]:
        warnings.append("This address is outside Laguna and Batangas, where we usually install. Message us and we'll tell you if we can come.")
    facing = "south" if q.azimuth_deg == 180 else f"{q.azimuth_deg:g}°"
    road = main["location"]["road_km"]
    if road is None:
        travel = "Prices are from our current supplier list."
    elif round(road) >= 1:
        travel = f"Prices are from our current supplier list and include the {road:.0f} km trip from Pila, Laguna."
    else:
        travel = "Prices are from our current supplier list; no travel charge within Pila."
    loss = cfg.system_losses.factor
    assumptions += [
        f"Sized for a house using about {monthly_kwh:,.0f} kWh a month, {PATTERN_LABEL[req.pattern]}: {GOAL_LABEL[req.goal]}.",
        f"We assumed a typical roof facing {facing} with a {q.tilt_deg:g}° pitch, and used long-term sun records for your area (PVGIS). "
        f"Panels are taken at {q.k_site * 100:.0f}% of their rating, which is what we usually measure on roofs here. "
        f"The figures are what reaches your meter: about {(1 - loss) * 100:.0f}% is lost in the inverter, the cables and dust on the panels.",
        travel,
        f"Savings assume electricity at ₱{tariff:.2f} per kWh, rising {cfg.economics.tariff_escalation * 100:.0f}% a year."
        + (f" Power you send back to the grid is credited at ₱{cfg.economics.export_rate_php_per_kwh:.2f} per kWh (the net metering rate)." if req.goal != "off_grid" else ""),
    ]
    if main["system"]["battery_note"] or (alternative and alternative["system"]["battery_note"]):
        dod = BatterySpec().depth_of_discharge   # the sizing's own figure (no setting of its own)
        assumptions.append(f"What the battery carries assumes your evening follows the pattern you chose ({PATTERN_LABEL[req.pattern]}) and that {dod * 100:.0f}% of the battery's rating is usable each night; the energy audit on the visit uses your real appliances.")
    out = dict(main)
    out.update({
        "inputs": {"goal": req.goal, "goal_label": GOAL_LABEL[req.goal], "pattern": req.pattern, "pattern_label": PATTERN_LABEL[req.pattern],
                   "monthly_kwh": monthly_kwh, "tariff_php_per_kwh": tariff, "lat": where["lat"], "lon": where["lon"],
                   "town": where["town"], "province": where["province"], "place": where["label"], "in_area": where["in_area"]},
        "alternative": alternative,
        "assumptions": assumptions,
        "warnings": warnings,
    })
    return out
