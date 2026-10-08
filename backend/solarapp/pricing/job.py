"""Price an assessment: BOQ from the sizing and layout, manual edits, then the build-up."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from ..schemas import AssessmentDoc, CandidatePanel
from .boq import BoqRequest, RoofRow, generate_boq
from .catalog import Catalog, Item
from .config import PricingConfig
from .engine import BomLine, JobInputs, landed_cost, price_job


@dataclass
class PricingContext:
    catalog: Catalog
    config: PricingConfig


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def extra_km_from_pin(lat: Optional[float], lon: Optional[float], cfg: PricingConfig) -> Optional[dict]:
    """Extra one-way km beyond the route's reference site: straight line to base x road factor, less the reference."""
    if lat is None or lon is None:
        return None
    straight = haversine_km(lat, lon, cfg.route.base_lat, cfg.route.base_lon)
    road = straight * cfg.route.road_factor
    extra = max(road - cfg.route.reference_site_km, 0.0)
    return {"straight_km": straight, "road_km": road, "reference_site_km": cfg.route.reference_site_km, "extra_km": round(extra, 1)}


def resolve_panel(panel: CandidatePanel, catalog: Catalog, cfg: PricingConfig) -> tuple[Optional[Item], Optional[str]]:
    """The DB panel for the selected candidate: by code, else the cheapest DB panel of the same wattage."""
    if panel.code:
        it = catalog.get(panel.code)
        if it is not None:
            return it, None
    same = [i for i in catalog.by_category("Solar Panel") if i.rating and (i.rating_unit or "").upper() == "W" and abs(i.rating - panel.watt_peak) < 1.0]
    if same:
        same.sort(key=lambda i: landed_cost(i, catalog, cfg).landed)
        return same[0], f"Candidate panel '{panel.name or panel.watt_peak}' is not linked to the materials database; priced as {same[0].code} {same[0].name} (cheapest {panel.watt_peak:g} W panel)."
    return None, None


def rows_from_layout(doc: AssessmentDoc, panel: CandidatePanel, selected_panel_result: dict, count: int, gap_m: float) -> list[RoofRow]:
    """Fill rows face by face using the fitted rows (from the eave up); the panel's long side runs along the row in landscape."""
    rows: list[RoofRow] = []
    left = count
    for f in doc.faces:
        if left <= 0:
            break
        lr = selected_panel_result["faces"].get(f.id) or {}
        best = lr.get("best") or {}
        fitted = [int(r) for r in (best.get("rows") or []) if int(r) > 0]
        if not fitted and best.get("along_length") and best.get("along_width"):
            fitted = [int(best["along_length"])] * int(best["along_width"])
        dim = panel.length_m if best.get("orientation") == "landscape" else panel.width_m
        for per_row in fitted:
            if left <= 0:
                break
            n = min(per_row, left)
            rows.append(RoofRow(n, dim, gap_m))
            left -= n
    if left > 0:  # more panels than the layout holds (override): one more row
        rows.append(RoofRow(left, panel.length_m, gap_m))
    return rows


def apply_edits(lines: list[BomLine], doc: AssessmentDoc, catalog: Catalog) -> tuple[list[BomLine], list[dict]]:
    warnings: list[dict] = []
    out: list[BomLine] = []
    overrides = {e.code: e for e in doc.pricing.bom_edits}
    for l in lines:
        e = overrides.get(l.code)
        if e is None:
            out.append(l)
        elif e.qty > 0:
            out.append(BomLine(l.code, e.qty, l.role, (l.note + " " if l.note else "") + "(edited)"))
        # qty 0 = removed
    for e in doc.pricing.bom_extra:
        if e.qty <= 0:
            continue
        if catalog.get(e.code) is None:
            warnings.append({"code": "missing_item", "message": f"Added item {e.code} is not in the materials database."})
            continue
        existing = next((i for i, l in enumerate(out) if l.code == e.code), None)
        if existing is not None:
            o = out[existing]
            out[existing] = BomLine(o.code, o.qty + e.qty, o.role, (o.note + " " if o.note else "") + "(+ added)")
        else:
            out.append(BomLine(e.code, e.qty, "extra", e.note or "added"))
    return out, warnings


def price_assessment(doc: AssessmentDoc, results: dict, ctx: PricingContext) -> dict:
    """Returns the pricing block for results. Needs sizing (inverter kW, battery kWh, panel count)."""
    cfg, catalog = ctx.config, ctx.catalog
    warnings: list[dict] = []
    sizing = results.get("sizing")
    selected = next((p for p in results["panels"] if p["panel"]["id"] == results["selected_panel_id"]), None)
    if not catalog.items:
        return {"available": False, "reason": "The materials database is empty. Import the workbook on the Materials page.", "warnings": []}
    if sizing is None or selected is None:
        return {"available": False, "reason": "Pricing needs the energy audit and sizing (inverter and battery size).", "warnings": []}
    panel_doc = next(p for p in doc.panels if p.id == results["selected_panel_id"])
    db_panel, note = resolve_panel(panel_doc, catalog, cfg)
    if note:
        warnings.append({"code": "panel_unlinked", "message": note})
    if db_panel is None:
        return {"available": False, "reason": f"No {panel_doc.watt_peak:g} W panel in the materials database. Pick the candidate panel from the database or add it on the Materials page.", "warnings": warnings}

    count = int(sizing["panels"])
    if count <= 0:
        return {"available": False, "reason": "The sizing recommends no panels.", "warnings": warnings}
    rows = rows_from_layout(doc, panel_doc, selected, count, doc.gap_m)
    pj = doc.pricing
    cfg_job = cfg.model_copy(deep=True)
    if pj.max_panels_per_string:
        cfg_job.roles.max_panels_per_string = pj.max_panels_per_string
    inv = sizing["inverter"]
    bat_kwh = float(sizing["battery"]["installed_kwh"]) if sizing["kind"] != "net_metering" else 0.0
    req = BoqRequest(
        panel_code=db_panel.code, panel_count=count, rows=rows,
        inverter_kw=float(inv["size_kw"]), inverter_units=int(inv["units"]), inverter_required_kw=float(inv.get("required_kw") or 0) or None, battery_kwh=bat_kwh,
        strings_override=pj.strings_override, inverter_code=pj.inverter_code, battery_code=pj.battery_code,
        pv_run_m=pj.pv_run_m, ac_run_m=pj.ac_run_m, grounding_run_m=pj.grounding_run_m, conduit_m=pj.conduit_m,
    )
    boq = generate_boq(req, catalog, cfg_job)
    warnings += boq.warnings
    generated = [{"code": l.code, "qty": l.qty, "role": l.role, "note": l.note} for l in boq.lines]
    lines, edit_warnings = apply_edits(boq.lines, doc, catalog)
    warnings += edit_warnings

    pin = extra_km_from_pin(doc.lat, doc.lon, cfg)
    d = cfg.job_defaults
    job = JobInputs(
        roof_factor=pj.roof_factor if pj.roof_factor is not None else d.roof_factor,
        roof_closed_days=pj.roof_closed_days if pj.roof_closed_days is not None else d.roof_closed_days,
        max_days=pj.max_days if pj.max_days is not None else d.max_days,
        max_pairs=pj.max_pairs if pj.max_pairs is not None else d.max_pairs,
        battery_haul_hours=d.battery_haul_hours,
        owner_days=pj.owner_days if pj.owner_days is not None else d.owner_days,
        extra_km=pj.extra_km if pj.extra_km is not None else (pin["extra_km"] if pin else d.extra_km),
        extra_toll=pj.extra_toll if pj.extra_toll is not None else d.extra_toll,
        net_metering=sizing["kind"] != "off_grid",
    )
    priced = price_job(lines, catalog, cfg_job, job)
    cash_by_supplier: dict[str, float] = {}
    for l in lines:
        it = catalog.get(l.code)
        if it is None:
            continue
        lc = landed_cost(it, catalog, cfg_job)
        cash_by_supplier[it.supplier] = cash_by_supplier.get(it.supplier, 0.0) + (lc.net_price + lc.payment_fee) * l.qty
    priced.update({
        "cash_by_supplier": cash_by_supplier,
        "available": True,
        "panel": {"code": db_panel.code, "name": db_panel.name, "watt_peak": db_panel.rating},
        "generated_bom": generated,
        "choices": boq.choices,
        "pin_distance": pin,
        "warnings": warnings + [{"code": "missing_item", "message": f"Code {c} is not in the materials database."} for c in priced["missing_codes"]],
        "quotation_validity_days": cfg.job.quotation_validity_days,
    })
    return priced
