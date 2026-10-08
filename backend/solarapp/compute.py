"""Turn an assessment document into results: layout, k, simulation, comparison."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from .core import audit as audit_core
from .core import kfactor, layout, shade
from .core.dataset import NasaReference, PvgisDataset
from .core.sizing import BatterySpec, InverterRules, OffGridRules, plan_from_faces, size_system
from .core.simulation import FaceSpec, ThermalModel, prepare_sky, simulate, typical_air_temperature
from .pricing.config import PricingConfig
from .pricing.job import PricingContext, price_assessment
from .pricing.economics import build_economics
from .pricing.program import build_program
from .schemas import AssessmentDoc

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class ComputeError(ValueError):
    pass


def _warn(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def compute_results(doc: AssessmentDoc, pvgis: PvgisDataset, nasa: NasaReference, pricing: Optional[PricingContext] = None) -> dict:
    if doc.lat is None or doc.lon is None:
        raise ComputeError("Set the site location (map pin) first.")
    if not doc.faces:
        raise ComputeError("Add at least one roof face.")
    if not doc.panels:
        raise ComputeError("Add at least one candidate panel.")
    if not pvgis.available:
        raise ComputeError("Weather dataset not found. Run the one-time download first (see README).")

    cell = pvgis.nearest_cell(doc.lat, doc.lon)
    assert cell is not None
    tmy = pvgis.load_tmy(cell)
    sky = prepare_sky(tmy, doc.lat, doc.lon, cell.elevation_m, cell.time_offset_h)
    warnings: list[dict] = []
    if cell.distance_km > 40:
        warnings.append(_warn("far_cell", f"The nearest weather record is {cell.distance_km:.0f} km from the pin. Results are less certain; check that the pin is on the house."))
    if pvgis.synthetic:
        warnings.append(_warn("synthetic_data", "Test weather data is in use. Results are not real. Download the real dataset (see README) before trusting them."))

    # Shade: wall strips per face and the hourly beam factor
    sun_el = (90.0 - sky.zenith.to_numpy(dtype=float))
    sun_az = sky.azimuth.to_numpy(dtype=float)
    cuts_by_face: dict[str, layout.FaceCuts] = {}
    beam_by_face: dict[str, Optional[np.ndarray]] = {}
    shade_block: dict[str, dict] = {}
    for f in doc.faces:
        cuts, wall_details = shade.face_cuts(f, doc.lat)
        cuts_by_face[f.id] = cuts
        beam_by_face[f.id] = shade.beam_factor(f, cuts, sun_az, sun_el, doc.lat)
        obstacles = []
        for t in f.obstacles:
            cls, text = shade.obstacle_class(t.direction_deg, t.elevation_deg)
            obstacles.append({"id": t.id, "label": t.label, "direction_deg": t.direction_deg, "elevation_deg": t.elevation_deg, "width_deg": t.width_deg, "cls": cls, "text": text})
        shade_block[f.id] = {"walls": [w.to_dict() for w in wall_details], "obstacles": obstacles}
        for w in wall_details:
            if w.whole_face:
                warnings.append(_warn("wall_shades_face", f"{f.name}: the wall on the {w.edge} side shades the whole face at midday. Leave this face out, or check the wall height."))

    # Panel candidates and layout
    panel_results = []
    for p in doc.panels:
        faces = {}
        total = 0
        for f in doc.faces:
            lr = layout.fit_face(f.shape, f.length_m, f.width_m, f.ridge_m, p.length_m, p.width_m, doc.setback_m, doc.gap_m,
                                 cuts_by_face[f.id], f.panels_left_out, f.panel_count_override)
            faces[f.id] = lr.to_dict()
            total += lr.count
        panel_results.append({
            "panel": p.model_dump(), "faces": faces, "total_count": total,
            "system_kwp": total * p.watt_peak / 1000.0, "best": False,
        })
    best_idx = max(range(len(panel_results)), key=lambda i: panel_results[i]["system_kwp"])
    panel_results[best_idx]["best"] = True
    selected_idx = next((i for i, pr in enumerate(panel_results) if pr["panel"]["id"] == doc.selected_panel_id), best_idx)
    selected = panel_results[selected_idx]
    selected_panel = doc.panels[selected_idx]
    if selected["total_count"] == 0:
        # a layout with no panels is an input error, not a result
        if panel_results[best_idx]["total_count"] == 0:
            raise ComputeError("No panel fits any roof face. Check the face sizes and the setback.")
        raise ComputeError(f"The chosen panel ({selected_panel.name}) fits no roof face. Pick another panel under Panel options, or check the face sizes and the setback.")
    for f in doc.faces:
        if selected["faces"][f.id]["gross"] == 0:
            warnings.append({**_warn("face_no_fit", f"{f.name}: no panel fits this face ({f.length_m:g} m along the eave × {f.width_m:g} m up the slope, setback {doc.setback_m:g} m). Check the size or reduce the setback."), "face_id": f.id})
    geometry_block = build_geometry(doc, selected, cuts_by_face, shade_block)  # the plan drawing of each face (contract C3)

    # k factor
    set_results: list[kfactor.ReadingSetResult] = []
    face_names = {f.id: f.name for f in doc.faces}
    for i, s in enumerate(doc.reading_sets):
        label = s.label or (face_names.get(s.face_id) if s.face_id else None) or f"Set {i + 1}"
        amb_est = None
        if s.measured_at is not None:
            amb_est = typical_air_temperature(tmy, s.measured_at.month, s.measured_at.hour)
        inp = kfactor.ReadingSetInput(
            readings=[kfactor.ReadingRow(r.irradiance_wm2, r.power_w, r.module_temp_c) for r in s.readings],
            measured_at=s.measured_at, ambient_temp_c=s.ambient_temp_c, sky_condition=s.sky_condition,
            face_id=s.face_id, label=label,
            test_panel_rating_w=doc.test_panel_rating_w, calibration_factor=doc.test_panel_calibration,
        )
        set_results.append(kfactor.evaluate_reading_set(inp, amb_est))

    selected_set = kfactor.select_site_set(set_results)
    if selected_set is None:
        raise ComputeError("Add at least one reading set with its three readings.")
    sr = set_results[selected_set]
    k_site, k_raw = sr.k_site, sr.k_raw
    if sr.rise_per_kw is not None and sr.rise_is_plausible:
        thermal = ThermalModel("site_rise", sr.rise_per_kw)
    else:
        thermal = ThermalModel()
    if sr.low_confidence:
        warnings.append(_warn("low_confidence_k", f"The reading set used for the site ('{sr.label}') is low confidence. Open it under Roof readings to see why, or retake it in steady sun."))

    face_specs = [
        FaceSpec(f.id, f.name, f.tilt_deg, f.azimuth_deg, selected["faces"][f.id]["count"], beam_by_face[f.id]) for f in doc.faces
    ]
    measured = simulate(tmy, doc.lat, doc.lon, cell.elevation_m, face_specs, selected_panel.watt_peak, k_site, thermal, sky=sky)
    reference = simulate(tmy, doc.lat, doc.lon, cell.elevation_m, face_specs, selected_panel.watt_peak, 1.0, ThermalModel(), sky=sky)
    deviation = ((measured.annual_kwh - reference.annual_kwh) / reference.annual_kwh * 100.0) if reference.annual_kwh > 0 else 0.0
    monthly_deviation = [
        ((m - r) / r * 100.0) if r > 0 else 0.0 for m, r in zip(measured.monthly_kwh, reference.monthly_kwh)
    ]

    # Owner's current formula, for continuity: N x Wp x k x avg in-plane sun hours x 30
    legacy_monthly = sum(
        fs.panel_count * selected_panel.watt_peak * k_raw * fs.avg_psh_per_day * 30.0 / 1000.0 for fs in measured.faces
    )

    nasa_point = nasa.nearest_point(doc.lat, doc.lon) if nasa.available else None
    nasa_block = None
    if nasa_point:
        pv = measured.ghi_psh_per_day
        na = nasa_point.get("ghi_kwh_m2_day") or [None] * 12
        diffs = [((n - p) / p * 100.0) if (n is not None and p) else None for n, p in zip(na, pv)]
        pv_ann = sum(pv) / 12
        na_ann = nasa_point.get("ghi_annual_kwh_m2_day")
        nasa_block = {
            "point": {k: nasa_point[k] for k in ("lat", "lon", "distance_km")},
            "nasa_ghi_psh": na, "pvgis_ghi_psh": pv, "monthly_diff_pct": diffs,
            "nasa_annual_psh": na_ann, "pvgis_annual_psh": pv_ann,
            "annual_diff_pct": ((na_ann - pv_ann) / pv_ann * 100.0) if (na_ann and pv_ann) else None,
        }

    for fs in measured.faces:
        shade_block[fs.face_id]["shade_loss_pct"] = fs.shade_loss_pct
        if fs.shade_loss_pct >= 5:
            warnings.append(_warn("shade_loss", f"{fs.name}: shade takes about {fs.shade_loss_pct:.0f}% of the direct sun over the year."))

    cfg = pricing.config if pricing is not None else PricingConfig()
    audit_block, sizing_block = compute_audit_and_sizing(doc, measured, selected, selected_panel.watt_peak, cfg)
    mark_sized_panels(doc, geometry_block, sizing_block, pricing)

    def set_to_dict(r: kfactor.ReadingSetResult, s) -> dict:
        d = asdict(r)
        d["warnings"] = [asdict(w) for w in r.warnings]
        d["measured_at"] = s.measured_at.isoformat() if s.measured_at else None
        d["sky_condition"] = s.sky_condition
        # per-row values aligned with the rows as typed: None where a row was dropped as unusable
        # (the same rule as core.kfactor: sunlight above zero and a non-negative power reading)
        usable = [bool(x.irradiance_wm2 > 0 and x.power_w >= 0) for x in s.readings]
        d["row_usable"] = usable
        for key in ("k_raw_values", "k_site_values"):
            if len(d[key]) == sum(usable):
                vals = iter(d[key])
                d[key] = [next(vals) if u else None for u in usable]
        return d

    results = {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "months": MONTHS,
        "dataset": {**cell.to_dict(), "synthetic": pvgis.synthetic, "source": pvgis.info().get("source")},
        "panels": panel_results,
        "geometry": geometry_block,
        "selected_panel_id": selected_panel.id,
        "best_panel": {
            "id": doc.panels[best_idx].id, "name": doc.panels[best_idx].name, "watt_peak": doc.panels[best_idx].watt_peak,
            "count": panel_results[best_idx]["total_count"], "system_kwp": panel_results[best_idx]["system_kwp"],
        },
        "k": {
            "sets": [set_to_dict(r, s) for r, s in zip(set_results, doc.reading_sets)],
            "selected_set_index": selected_set,
            "k_site": k_site,
            "k_raw": k_raw,
            "thermal": thermal.describe(),
            "thermal_kind": thermal.kind,
            "rise_c_per_kw": thermal.rise_c_per_kw,
        },
        "production": measured.to_dict(),
        "reference": reference.to_dict(),
        "shade": shade_block,
        "comparison": {
            "deviation_pct": deviation,
            "monthly_deviation_pct": monthly_deviation,
            "description": "Measured-k result versus a PVGIS-style simulation of the same roof with k = 1 and the PVGIS thermal model.",
        },
        "legacy_method": {
            "monthly_kwh": legacy_monthly,
            "annual_kwh": legacy_monthly * 12.0,
            "formula": "panels x Wp x k x average in-plane sun hours x 30",
        },
        "nasa_reference": nasa_block,
        "audit": audit_block,
        "sizing": sizing_block,
        "pricing": None,
        "program": None,
        "economics": None,
        "warnings": warnings,
    }
    add_ac_figures(results["production"], cfg.system_losses.factor)
    if pricing is not None:
        try:
            results["pricing"] = price_assessment(doc, results, pricing)
        except Exception as e:  # noqa: BLE001  pricing must never break the simulation
            results["pricing"] = {"available": False, "reason": f"Pricing failed: {e}", "warnings": []}
        try:
            results["program"] = build_program(doc, results, pricing.config)
        except Exception as e:  # noqa: BLE001
            results["program"] = {"available": False, "reason": f"Program of works failed: {e}", "warnings": []}
        try:
            results["economics"] = build_economics(doc, results, pricing.config)
        except Exception as e:  # noqa: BLE001
            results["economics"] = {"available": False, "reason": f"Economics failed: {e}", "warnings": []}
    return results


def add_ac_figures(production: dict, loss_factor: float) -> None:
    """Contract C2: the simulation stays "at the panels"; the figures at the meter (after the inverter, wiring,
    soiling and other losses) sit beside them for the customer documents."""
    production["loss_factor"] = loss_factor
    production["annual_kwh_ac"] = production["annual_kwh"] * loss_factor
    production["monthly_kwh_ac"] = [v * loss_factor for v in production["monthly_kwh"]]
    production["avg_monthly_kwh_ac"] = production["avg_monthly_kwh"] * loss_factor
    for f in production.get("faces") or []:
        f["annual_kwh_ac"] = f["annual_kwh"] * loss_factor
        f["monthly_kwh_ac"] = [v * loss_factor for v in f["monthly_kwh"]]


def compute_audit_and_sizing(doc: AssessmentDoc, production, selected_panel_result: dict, panel_wp: float, cfg: Optional[PricingConfig] = None) -> tuple[Optional[dict], Optional[dict]]:
    """Energy audit and system sizing, when the document carries appliances. The sizing works on energy at the
    meter (the system losses applied to the per-kWp profile) and places the sized panels on the roof best face
    first, simulating that allocation over the real hourly year."""
    cfg = cfg or PricingConfig()
    a = doc.audit
    if not a.appliances:
        return None, None
    appliances = [
        audit_core.Appliance(
            id=e.id, name=e.name or e.category, category=e.category, input_power_w=e.input_power_w, quantity=e.quantity,
            duty_factor=e.duty_factor, status=e.status,
            windows=[audit_core.Window(w.start, w.end, list(w.days), list(w.months)) for w in e.windows],
        )
        for e in a.appliances
    ]
    bills = [audit_core.Bill(b.id, b.billing_month, b.kwh, b.days, b.amount_php, b.utility) for b in a.bills if b.billing_month and b.kwh > 0]
    res = audit_core.run_audit(appliances, bills, reconcile=a.reconcile)
    audit_block = {
        "appliances": res.appliances,
        "daily_kwh_by_month": res.daily_kwh_by_month,
        "annual_kwh": res.annual_kwh,
        "peak_kw": res.peak_kw,
        "peak_avg_kw": res.peak_avg_kw,
        "peak_detail": res.peak_detail,
        "hour_table": res.hour_table,
        "largest_motor_kw": res.largest_motor_kw,
        "largest_motor_multiplier": res.largest_motor_multiplier,
        "audit_vs_bill": res.audit_vs_bill,
        "future_daily_kwh": res.future_daily_kwh,
        "load_profile_kw": np.asarray(res.load_kw).round(4).tolist(),
        "load_profile_unreconciled_kw": np.asarray(res.load_kw_unreconciled).round(4).tolist(),
        "weekday_profiles_kw": res.weekday_profiles_kw,
        "warnings": res.warnings,
    }
    kwp = production.system_kwp
    if kwp <= 0:
        return audit_block, None
    loss = cfg.system_losses.factor
    per_kwp = np.array(production.hourly_profile_kw) / kwp * loss   # at the meter
    faces_in = []
    for fs in production.faces:
        lr = selected_panel_result["faces"].get(fs.face_id) or {}
        best = lr.get("best") or {}
        rows = [int(r) for r in (best.get("rows") or []) if int(r) > 0]
        if not rows and best.get("along_length") and best.get("along_width"):
            rows = [int(best["along_length"])] * int(best["along_width"])
        faces_in.append({
            "face_id": fs.face_id, "name": fs.name, "panel_count": fs.panel_count, "hourly_profile_kw": fs.hourly_profile_kw,
            "specific_yield_kwh_per_kwp": fs.specific_yield_kwh_per_kwp, "rows": rows, "hourly_kw": fs.hourly_kw,
        })
    plan = plan_from_faces(faces_in, loss, production.hour_month, production.hour_local)
    s = a.system
    sizing = size_system(
        np.asarray(res.load_kw), per_kwp, roof_max_panels=int(selected_panel_result["total_count"]), panel_wp=panel_wp, kind=s.kind,
        peak_load_kw=res.peak_kw,
        largest_motor_kw=res.largest_motor_kw, largest_motor_multiplier=res.largest_motor_multiplier,
        battery=BatterySpec(s.battery_dod, s.battery_efficiency, days_of_autonomy=cfg.sizing.days_of_autonomy),
        inverter=InverterRules(list(s.inverter_sizes_kw), s.inverter_surge_factor, s.pv_ratio_max),
        offgrid=OffGridRules(s.offgrid_pv_margin),
        plan=plan,
    )
    return audit_block, sizing


def build_geometry(doc: AssessmentDoc, selected: dict, cuts_by_face: dict[str, layout.FaceCuts], shade_block: dict[str, dict]) -> list[dict]:
    """The plan of every face for the selected panel (contract C3): the fitted rows placed in the bands the fitter
    measured, the wall strips and the trees or buildings the shade model knows. Panels are not yet marked as used;
    that waits for the sizing (mark_sized_panels)."""
    panel = selected["panel"]
    out: list[dict] = []
    for f in doc.faces:
        lr = selected["faces"][f.id]
        best = lr.get("best") or {}
        sh = shade_block.get(f.id) or {}
        out.append(layout.face_geometry(
            face_id=f.id, name=f.name, shape=f.shape, eave_m=f.length_m, slope_m=f.width_m, ridge_m=f.ridge_m, azimuth_deg=f.azimuth_deg, tilt_deg=f.tilt_deg,
            panel_length_m=panel["length_m"], panel_width_m=panel["width_m"], setback_per_dimension_m=doc.setback_m, gap_m=doc.gap_m,
            cuts=cuts_by_face.get(f.id) or layout.FaceCuts(),
            orientation=best.get("orientation") or "portrait", rows=list(best.get("rows") or []), count=int(lr.get("count") or 0),
            gross=int(lr.get("gross") or 0), left_out=int(lr.get("left_out") or 0),
            walls=sh.get("walls") or [], obstacles=sh.get("obstacles") or [],
        ))
    return out


def mark_sized_panels(doc: AssessmentDoc, geometry: list[dict], sizing: Optional[dict], pricing: Optional[PricingContext]) -> None:
    """Flag the panels the sized system uses, faces in order and rows from the eave up (the BOQ fills its rows the same
    way), and number their strings by the BOQ's rule when the pricing settings are at hand. Without a sizing every
    panel stays unmarked: the roof check shows what the roof can hold."""
    if not sizing:
        return
    n = int(sizing.get("panels") or 0)
    per_string = None
    if pricing is not None and n > 0:
        pj = doc.pricing
        _strings, per_string = layout.string_rule(n, pj.max_panels_per_string or pricing.config.roles.max_panels_per_string, pj.strings_override)
    allocation = [(str(x["face_id"]), int(x.get("panels") or 0)) for x in (sizing.get("faces") or []) if x.get("face_id")]
    layout.mark_used(geometry, n, per_string, allocation or None)
