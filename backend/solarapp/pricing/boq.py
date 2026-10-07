"""Bill of quantities from the sized system.

Rules agreed with the owner: panels from the materials DB, the cheapest hybrid
inverter at or above the required kW, the cheapest battery combination at or
above the required nominal kWh, mounting per row (two rail lines, three L-feet
per rail, four end clamps per row, two mid clamps per panel gap, one splice per
rail joint), wire runs priced at a standard allowance with the gauge checked
against the voltage-drop limit, strings from a maximum panels per string,
protection, enclosures, grounding and consumables as on the sample job.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional

from .catalog import Catalog, Item
from .config import PricingConfig
from .engine import BomLine, landed_cost


@dataclass
class RoofRow:
    panels: int
    panel_dim_along_row_m: float
    gap_m: float = 0.0

    @property
    def length_m(self) -> float:
        return self.panels * self.panel_dim_along_row_m + max(self.panels - 1, 0) * self.gap_m


def rows_for(panel_count: int, per_row: int, dim_m: float, gap_m: float = 0.0) -> list[RoofRow]:
    rows: list[RoofRow] = []
    left = panel_count
    per_row = max(per_row, 1)
    while left > 0:
        n = min(per_row, left)
        rows.append(RoofRow(n, dim_m, gap_m))
        left -= n
    return rows


@dataclass
class BoqRequest:
    panel_code: str
    panel_count: int
    rows: list[RoofRow]
    inverter_kw: float
    inverter_units: int = 1
    inverter_required_kw: Optional[float] = None   # the sizing requirement; sets the units of a fixed model
    battery_kwh: float = 0.0
    strings_override: Optional[int] = None
    inverter_code: Optional[str] = None
    battery_code: Optional[str] = None
    pv_run_m: Optional[float] = None
    ac_run_m: Optional[float] = None
    grounding_run_m: Optional[float] = None
    conduit_m: Optional[float] = None


@dataclass
class BoqResult:
    lines: list[BomLine]
    choices: dict = field(default_factory=dict)
    warnings: list[dict] = field(default_factory=list)


def _excluded(item: Item, words: list[str]) -> bool:
    text = f"{item.name} {item.spec}".lower()
    return any(w.lower() in text for w in words)


def _cheapest(items: list[Item], catalog: Catalog, cfg: PricingConfig, units_fn=lambda i: 1) -> list[tuple[Item, int, float]]:
    out = []
    for it in items:
        n = units_fn(it)
        if n <= 0:
            continue
        cost = n * landed_cost(it, catalog, cfg).landed
        out.append((it, n, cost))
    out.sort(key=lambda x: (x[2], x[1]))
    return out


def select_inverter(kw: float, catalog: Catalog, cfg: PricingConfig) -> list[tuple[Item, int, float]]:
    cands = [
        i for i in catalog.by_category("Inverter")
        if i.is_hybrid_inverter and (i.rating_unit or "").lower() == "kw" and i.rating and i.rating >= kw - 1e-9
        and not _excluded(i, cfg.roles.inverter_exclude_words)
    ]
    return _cheapest(cands, catalog, cfg)


def select_battery(kwh: float, catalog: Catalog, cfg: PricingConfig) -> list[tuple[Item, int, float]]:
    cands = [
        i for i in catalog.by_category("Battery")
        if (i.rating_unit or "").lower() == "kwh" and i.rating and i.rating >= 1.0 and not _excluded(i, cfg.roles.battery_exclude_words)
    ]
    return _cheapest(cands, catalog, cfg, units_fn=lambda i: int(math.ceil(kwh / i.rating - 1e-9)))


def pick_gauge(current_a: float, run_m: float, voltage: float, drop_limit: float, ampacity: dict[str, float], cfg: PricingConfig) -> tuple[str, float, bool]:
    """Smallest gauge whose ampacity covers the continuous current and whose drop at run_m is within the limit."""
    rho = cfg.wiring.copper_resistivity
    needed = current_a * cfg.wiring.continuous_factor
    best: Optional[tuple[str, float]] = None
    for g, amps in sorted(ampacity.items(), key=lambda kv: float(kv[0])):
        area = float(g)
        drop = 2 * run_m * current_a * rho / area / voltage if voltage > 0 else 0.0
        if amps >= needed and drop <= drop_limit:
            return g, drop, True
        best = (g, drop)
    g, drop = best if best else ("", 0.0)
    return g, drop, False


def _by_amps(pattern: str, amps_required: float, catalog: Catalog, cfg: PricingConfig, category: str = "Protective Devices") -> Optional[Item]:
    rx = re.compile(pattern, re.I)
    cands = [(i.amps_in_name(), i) for i in catalog.by_category(category) if rx.search(i.name)]
    ok = [(a, i) for a, i in cands if a is not None and a >= amps_required]
    if not ok:
        return None
    ok.sort(key=lambda x: (x[0], landed_cost(x[1], catalog, cfg).landed))
    return ok[0][1]


def generate_boq(req: BoqRequest, catalog: Catalog, cfg: PricingConfig) -> BoqResult:
    w, r = cfg.wiring, cfg.roles
    lines: list[BomLine] = []
    warnings: list[dict] = []
    choices: dict = {}

    panel = catalog.get(req.panel_code)
    if panel is None:
        raise ValueError(f"Panel {req.panel_code} is not in the materials database.")
    lines.append(BomLine(panel.code, req.panel_count, "panel", f"{req.panel_count} x {panel.name}"))

    # inverter: the per-job override, else the default model, else the cheapest hybrid that fits
    inv_options = select_inverter(req.inverter_kw, catalog, cfg)
    inverter: Optional[Item] = None
    units = max(req.inverter_units, 1)
    required = req.inverter_required_kw or req.inverter_kw * units
    if req.inverter_code:
        inverter = catalog.get(req.inverter_code)
    if inverter is None and r.default_inverter_code:
        inverter = catalog.get(r.default_inverter_code)
        if inverter is None:
            warnings.append({"code": "default_inverter", "message": f"Default inverter {r.default_inverter_code} is not in the materials database; the cheapest that fits is used."})
    if inverter is None and inv_options:
        inverter = inv_options[0][0]
    if inverter is None:
        warnings.append({"code": "no_inverter", "message": f"No hybrid inverter of {req.inverter_kw:g} kW or more in the materials database."})
    else:
        if inverter.rating and (inverter.rating_unit or "").lower() == "kw":
            units = max(units, int(math.ceil(required / inverter.rating - 1e-9)))
        note = f"{inverter.rating:g} kW hybrid" + (f", {units} in parallel for {required:g} kW" if units > 1 else "")
        lines.append(BomLine(inverter.code, units, "inverter", note))
    opts = [{"code": i.code, "name": i.name, "rating_kw": i.rating, "supplier": i.supplier, "landed": c} for i, n, c in inv_options[:6]]
    if inverter and inverter.code not in [o["code"] for o in opts]:
        opts.insert(0, {"code": inverter.code, "name": inverter.name, "rating_kw": inverter.rating, "supplier": inverter.supplier, "landed": landed_cost(inverter, catalog, cfg).landed * units})
    choices["inverter_options"] = opts
    choices["inverter_units"] = units
    inv_kw = float(inverter.rating) if inverter and inverter.rating else req.inverter_kw

    # battery
    battery_units = 0
    battery: Optional[Item] = None
    if req.battery_kwh > 0:
        bat_options = select_battery(req.battery_kwh, catalog, cfg)
        if req.battery_code:
            battery = catalog.get(req.battery_code)
            battery_units = int(math.ceil(req.battery_kwh / battery.rating - 1e-9)) if battery and battery.rating else 0
        elif bat_options:
            battery, battery_units, _ = bat_options[0]
        if battery is None:
            warnings.append({"code": "no_battery", "message": "No battery in the materials database fits the required kWh."})
        else:
            lines.append(BomLine(battery.code, battery_units, "battery", f"{battery_units} x {battery.rating:g} kWh = {battery_units * battery.rating:g} kWh"))
        choices["battery_options"] = [{"code": i.code, "name": i.name, "rating_kwh": i.rating, "units": n, "total_kwh": n * i.rating, "supplier": i.supplier, "landed": c} for i, n, c in bat_options[:8]]

    # mounting per row
    rails = splices = end_clamps = mid_clamps = 0
    for row in req.rows:
        per_line = int(math.ceil(row.length_m / r.rail_length_m - 1e-9)) if row.panels > 0 else 0
        rails += 2 * per_line
        splices += 2 * max(per_line - 1, 0)
        end_clamps += 4 if row.panels > 0 else 0
        mid_clamps += 2 * max(row.panels - 1, 0)
    lines += [
        BomLine(r.rail, rails, "rail", f"{len(req.rows)} rows, 2 lines each, {r.rail_length_m:g} m rails"),
        BomLine(r.l_foot, rails * r.l_feet_per_rail, "l_foot", f"{r.l_feet_per_rail} per rail"),
        BomLine(r.end_clamp, end_clamps, "end_clamp", "4 per row"),
        BomLine(r.mid_clamp, mid_clamps, "mid_clamp", "2 per panel gap"),
    ]
    if splices > 0:
        lines.append(BomLine(r.splice, splices, "splice", "1 per rail joint"))

    # strings and PV cable
    strings = req.strings_override or int(math.ceil(req.panel_count / max(r.max_panels_per_string, 1) - 1e-9))
    strings = max(strings, 1)
    per_string = int(math.ceil(req.panel_count / strings))
    panel_w = float(panel.rating or 0) if (panel.rating_unit or "").upper() == "W" else 0.0
    i_string = panel_w / w.panel_vmp_v if panel_w else 0.0
    v_string = per_string * w.panel_vmp_v
    pv_run = req.pv_run_m if req.pv_run_m is not None else w.pv_run_m
    pv_gauge, pv_drop, pv_ok = pick_gauge(i_string, pv_run, v_string, w.dc_drop_limit, w.pv_cable_ampacity, cfg)
    if not pv_ok:
        warnings.append({"code": "pv_cable", "message": f"PV cable: {pv_drop:.1%} drop at {pv_run:g} m even with {pv_gauge} mm2; shorten the run or use a larger cable."})
    lines += [
        BomLine(r.pv_cable_red.get(pv_gauge, r.pv_cable_red["4"]), strings * pv_run, "pv_cable_red", f"{strings} strings x {pv_run:g} m, {pv_gauge} mm2, {pv_drop:.1%} drop"),
        BomLine(r.pv_cable_black.get(pv_gauge, r.pv_cable_black["4"]), strings * pv_run, "pv_cable_black", f"{strings} strings x {pv_run:g} m"),
        BomLine(r.mc4_pair, strings * r.mc4_pairs_per_string, "mc4_pair", f"{r.mc4_pairs_per_string} per string"),
    ]

    # AC wiring and grounding
    i_ac = inv_kw * 1000.0 / w.ac_voltage
    ac_run = req.ac_run_m if req.ac_run_m is not None else w.ac_run_m
    gnd_run = req.grounding_run_m if req.grounding_run_m is not None else w.grounding_run_m
    ac_gauge, ac_drop, ac_ok = pick_gauge(i_ac, ac_run, w.ac_voltage, w.ac_drop_limit, w.thhn_ampacity, cfg)
    if not ac_ok:
        warnings.append({"code": "ac_cable", "message": f"AC circuit: {i_ac:.0f} A needs more than {ac_gauge} mm2 THHN at {ac_run:g} m."})
    thhn_code = r.thhn.get(ac_gauge) or next(iter(r.thhn.values()))
    lines.append(BomLine(thhn_code, units * (ac_run + gnd_run), "thhn", f"{ac_run:g} m circuits + {gnd_run:g} m grounding per inverter, {ac_gauge} mm2 for {i_ac:.0f} A, {ac_drop:.1%} drop"))

    # battery cable and breaker
    if battery_units > 0:
        i_bat = inv_kw * 1000.0 / w.battery_voltage
        bat_gauge, _, bat_ok = pick_gauge(i_bat, 1.0, w.battery_voltage, 0.5, w.battery_cable_ampacity, cfg)
        if not bat_ok:
            warnings.append({"code": "battery_cable", "message": f"Battery cable: {i_bat:.0f} A exceeds the largest lug pair in the DB."})
        lines.append(BomLine(r.battery_cable_pair.get(bat_gauge, r.battery_cable_pair["35"]), w.battery_pairs_per_battery * battery_units, "battery_cable", f"{bat_gauge} mm2 lug pairs for {i_bat:.0f} A"))
        amps_req = i_bat * w.continuous_factor
        bb = _by_amps(r.battery_breaker_pattern, amps_req, catalog, cfg) or catalog.get(r.battery_breaker_fallback)
        if bb:
            lines.append(BomLine(bb.code, units, "battery_breaker", f"for {amps_req:.0f} A continuous"))

    # protection
    lines.append(BomLine(r.dc_breaker, strings, "dc_breaker", "1 per string"))
    lines.append(BomLine(r.dc_spd, units, "dc_spd", "1 per inverter"))
    i_ac_req = i_ac * w.continuous_factor
    ats = catalog.get(r.ats)
    if r.ats_amps < i_ac_req:
        alt = _by_amps(r"ATS", i_ac_req, catalog, cfg)
        if alt:
            ats = alt
        else:
            warnings.append({"code": "ats", "message": f"No ATS rated for {i_ac_req:.0f} A in the materials database."})
    if ats:
        lines.append(BomLine(ats.code, units, "ats", f"transfer switch, {i_ac_req:.0f} A continuous"))
    if r.ac_breaker_amps < i_ac_req:
        warnings.append({"code": "ac_breaker", "message": f"Default AC breaker ({r.ac_breaker_amps:g} A) is below the {i_ac_req:.0f} A required; choose a larger breaker."})
    lines.append(BomLine(r.ac_breaker, units * r.ac_breakers_per_inverter, "ac_breaker", "DU disconnect, grid-inverter, inverter-load, grid-load"))
    lines.append(BomLine(r.ac_spd, units * r.ac_spds_per_inverter, "ac_spd", "one per AC breaker"))

    # enclosures, raceways, grounding, consumables
    conduit = req.conduit_m if req.conduit_m is not None else w.conduit_m
    lines += [
        BomLine(r.enclosure, r.enclosures * units, "enclosure", "DC box and AC box"),
        BomLine(r.cable_tray, r.cable_trays, "cable_tray", ""),
        BomLine(r.conduit, conduit, "conduit", "allowance"),
        BomLine(r.ground_rod, r.ground_rods, "ground_rod", ""),
        BomLine(r.earth_lug, r.earth_lugs, "earth_lug", ""),
        BomLine(r.sealant, r.sealants, "sealant", ""),
    ]
    for l in lines:
        if catalog.get(l.code) is None:
            warnings.append({"code": "missing_item", "message": f"Role {l.role}: code {l.code} is not in the materials database."})
    choices.update({
        "strings": strings, "panels_per_string": per_string, "string_current_a": i_string, "string_voltage_v": v_string,
        "pv_gauge": pv_gauge, "pv_drop": pv_drop, "ac_current_a": i_ac, "ac_gauge": ac_gauge, "ac_drop": ac_drop,
        "inverter_code": inverter.code if inverter else None, "battery_code": battery.code if battery else None, "battery_units": battery_units,
        "rows": [{"panels": x.panels, "length_m": x.length_m} for x in req.rows],
    })
    return BoqResult([l for l in lines if l.qty > 0], choices, warnings)
