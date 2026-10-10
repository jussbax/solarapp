"""Bill of quantities from the sized system.

Rules agreed with the owner: panels from the materials DB; the default inverter per system kind (one unit when it
covers the requirement, else the parallel rule of round 3: a small overshoot within a settable tolerance keeps one
unit, otherwise the cheapest single unit that fits (the default's brand on ties) before parallel units); the
battery on continuous current first (the inverter's battery current at or below the bank's continuous discharge
rating), then the cheapest kWh; mounting per row (two rail lines, three L-feet per rail, four end clamps per row,
two mid clamps per panel gap, one splice per rail joint); wire runs priced at a standard allowance with the gauge
checked against the voltage-drop limit; strings from a maximum panels per string; one breaker per AC circuit at
1.25 x the circuit current rounded up to the next standard size with the conductor sized from the breaker; the
battery breaker at 1.25 x the inverter's battery current with the battery cable's ampacity at or above the breaker
(a failed coordination blocks the customer documents); one AC SPD per board, one DC SPD per MPPT input in use, one
enclosure per inverter, no ATS on an inverter that carries its own transfer switch; array bonding, L-foot fasteners,
a visible AC disconnect and (on net metering) an export limiter as roles. A role without an
item in the materials list still puts its line on the BOM with the quantity and no price, and a warning says so.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional

from .catalog import Catalog, Item
from .config import PricingConfig
from .engine import BomLine, landed_cost

NO_ITEM_PREFIX = "NO-ITEM-"   # the code of a BOM line whose role has no item in the materials list yet


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
    kind: str = "combination"                      # off_grid, net_metering or combination: grid kinds need a grid-interactive inverter
    strings_override: Optional[int] = None
    inverter_code: Optional[str] = None
    battery_code: Optional[str] = None
    pv_run_m: Optional[float] = None
    ac_run_m: Optional[float] = None
    grounding_run_m: Optional[float] = None
    conduit_m: Optional[float] = None
    peak_load_kw: Optional[float] = None           # the house peak, for the pass-through check on a net-metering job
    # round 12: the string design's temperatures for this job (compute.py's results["site"]); None = the settings alone (the website estimate)
    t_cold_c: Optional[float] = None
    t_hot_c: Optional[float] = None


@dataclass
class BoqResult:
    lines: list[BomLine]
    choices: dict = field(default_factory=dict)
    warnings: list[dict] = field(default_factory=list)


def _plural(n: float, word: str, plural: Optional[str] = None) -> str:
    """"1 row", "3 rows": counts in BOM notes read as a crew reads them."""
    n_txt = f"{int(n)}" if float(n).is_integer() else f"{n:g}"
    return f"{n_txt} {word if abs(n - 1) < 1e-9 else (plural or word + 's')}"


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


def select_inverter(kw: float, catalog: Catalog, cfg: PricingConfig, kind: str = "combination") -> list[tuple[Item, int, float]]:
    """Hybrid inverters at or above kw, cheapest first. Anything with net metering (every kind but off_grid) wants a
    unit marked grid-interactive; a unit marked unable to export is never offered there. When nothing in the list
    is marked yet (a database imported before the flag existed), the unmarked units are offered with the
    certificate note, so a job is never priced without an inverter."""
    grid = kind != "off_grid"
    fits = [
        i for i in catalog.by_category("Inverter")
        if i.is_hybrid_inverter and (i.rating_unit or "").lower() == "kw" and i.rating and i.rating >= kw - 1e-9
        and not _excluded(i, cfg.roles.inverter_exclude_words)
    ]
    if grid:
        marked = [i for i in fits if i.grid_interactive is True]
        fits = marked or [i for i in fits if i.grid_interactive is None]
    return _cheapest(fits, catalog, cfg)


def _grid_flag(item: Item) -> str:
    return "yes" if item.grid_interactive is True else "no" if item.grid_interactive is False else "unknown"


def battery_current_ok(battery: Item, units: int, current_a: Optional[float]) -> Optional[bool]:
    """Whether `units` of the battery deliver the inverter's battery current continuously; None when the item has no
    continuous rating (unknown) or no current is asked."""
    if current_a is None or not battery.continuous_a:
        return None
    return units * float(battery.continuous_a) >= current_a - 1e-9


def select_battery(kwh: float, catalog: Catalog, cfg: PricingConfig, current_a: Optional[float] = None) -> list[tuple[Item, int, float]]:
    """Batteries whose units cover the kWh, cheapest first. With the inverter's battery current given (round 3,
    E-03) the continuous rating comes first: the combinations that deliver it, then the ones whose rating is blank
    (unknown), then the ones that fall short, each group cheapest first."""
    cands = [
        i for i in catalog.by_category("Battery")
        if (i.rating_unit or "").lower() == "kwh" and i.rating and i.rating >= 1.0 and not _excluded(i, cfg.roles.battery_exclude_words)
    ]
    ranked = []
    for it, n, cost in _cheapest(cands, catalog, cfg, units_fn=lambda i: int(math.ceil(kwh / i.rating - 1e-9))):
        ok = battery_current_ok(it, n, current_a)
        rank = 0 if (current_a is None or ok) else (1 if ok is None else 2)
        ranked.append((rank, cost, n, it))
    ranked.sort(key=lambda x: (x[0], x[1], x[2]))
    return [(it, n, cost) for rank, cost, n, it in ranked]


def pick_gauge(current_a: float, run_m: float, voltage: float, drop_limit: float, ampacity: dict[str, float], cfg: PricingConfig,
               min_ampacity: float = 0.0) -> tuple[str, float, bool]:
    """Smallest gauge whose ampacity covers the continuous current (and `min_ampacity`, the breaker that protects
    it) and whose drop at run_m is within the limit."""
    rho = cfg.wiring.copper_resistivity
    needed = max(current_a * cfg.wiring.continuous_factor, float(min_ampacity or 0.0))
    best: Optional[tuple[str, float]] = None
    for g, amps in sorted(ampacity.items(), key=lambda kv: float(kv[0])):
        area = float(g)
        drop = 2 * run_m * current_a * rho / area / voltage if voltage > 0 else 0.0
        if amps >= needed and drop <= drop_limit:
            return g, drop, True
        best = (g, drop)
    g, drop = best if best else ("", 0.0)
    return g, drop, False


def next_standard_size(amps: float, sizes: list[float]) -> Optional[float]:
    """The next standard breaker rating at or above amps; None when the list has nothing that large."""
    for s in sorted(float(x) for x in sizes):
        if s >= amps - 1e-9:
            return s
    return None


def _by_amps(pattern: str, amps_required: float, catalog: Catalog, cfg: PricingConfig, category: str = "Protective Devices") -> Optional[Item]:
    rx = re.compile(pattern, re.I)
    cands = [(i.amps_in_name(), i) for i in catalog.by_category(category) if rx.search(i.name)]
    ok = [(a, i) for a, i in cands if a is not None and a >= amps_required]
    if not ok:
        return None
    ok.sort(key=lambda x: (x[0], landed_cost(x[1], catalog, cfg).landed))
    return ok[0][1]


def battery_current_check(battery: Item, units: int, inverter: Optional[Item], inverter_units: int, i_required: float) -> tuple[int, list[dict]]:
    """E-03: the battery bank's continuous discharge current against the inverter's battery current (its own
    maximum when the item carries it, else the current at rated output). Below it the BMS cuts out on the first
    evening the house asks for full power, which is the brownout the battery was sold for: a hard warning that
    holds the customer documents until the owner picks a unit rated for it or more units in parallel (never a
    silent extra pack). Without a continuous rating on the item, a reminder to type it."""
    warnings: list[dict] = []
    if units <= 0 or battery.rating is None:
        return units, warnings
    need = i_required * max(inverter_units, 1)
    if not battery.continuous_a:
        warnings.append({"code": "battery_current_unknown", "message": (
            f"{battery.code} {battery.name} has no continuous discharge current on its item; the inverter draws up to {need:.0f} A from the battery. "
            f"Type the battery's continuous current on the Materials page to check it before the proposal goes out.")})
        return units, warnings
    cont_total = units * float(battery.continuous_a)
    over = f" over {units} units" if units > 1 else ""
    if cont_total < need - 1e-9:
        needed = int(math.ceil(need / float(battery.continuous_a) - 1e-9))
        warnings.append({"code": "battery_current", "hard": True, "blocks_documents": True, "message": (
            f"{battery.code} delivers {cont_total:.0f} A continuous{over} (about {cont_total * 51.2 / 1000:.1f} kW) and the inverter draws up to {need:.0f} A from the battery, "
            f"so the battery cuts out when the house asks for full power. Use a battery rated at least {need:.0f} A continuous, or {needed} units in parallel "
            f"({needed * float(battery.rating):g} kWh); set it under Pricing inputs › Battery. The proposal, roof check and card are held until this is fixed.")})
    return units, warnings


def choose_inverter_units(inverter: Item, required: float, override: bool, catalog: Catalog, cfg: PricingConfig, kind: str) -> tuple[Item, int, list[dict]]:
    """E-01: the units of the chosen inverter for the requirement. One unit when it covers it; one unit with a
    warning when the overshoot is within the tolerance (the owner's unit stays on the job); else, unless the owner
    picked the unit per job, the cheapest single unit that fits the kind (the default's brand on ties) with a
    warning that names the parallel alternative; else parallel units with a warning."""
    warnings: list[dict] = []
    rating = float(inverter.rating) if inverter.rating and (inverter.rating_unit or "").lower() == "kw" else 0.0
    if rating <= 0 or required <= rating + 1e-9:
        return inverter, 1, warnings
    tol = max(float(cfg.roles.inverter_parallel_tolerance_pct), 0.0) / 100.0
    over_pct = (required / rating - 1.0) * 100.0
    units = int(math.ceil(required / rating - 1e-9))
    if required <= rating * (1.0 + tol) + 1e-9:
        warnings.append({"code": "inverter_overshoot_tolerated", "message": (
            f"The sizing asks for {required:.1f} kW and {inverter.code} is {rating:g} kW: {over_pct:.0f}% over, within the {tol * 100:g}% tolerance under "
            f"Pricing settings › BOM item roles, so one unit is used rather than {units} in parallel. Verify the unit's overload rating on the datasheet, "
            f"or set the tolerance to 0 to step up.")})
        return inverter, 1, warnings
    if not override:
        singles = select_inverter(required, catalog, cfg, kind)
        if singles:
            cheapest, _, cheapest_cost = singles[0]
            brand = sorted((x for x in singles if x[0].supplier == inverter.supplier and x[0].code != inverter.code), key=lambda x: (float(x[0].rating), x[2]))
            pick, cost, how = cheapest, cheapest_cost, "the cheapest unit that fits"
            if brand and brand[0][2] <= cheapest_cost + 1e-6:
                pick, cost, how = brand[0][0], brand[0][2], "the next rating of the same brand"
            parallel_cost = units * landed_cost(inverter, catalog, cfg).landed
            warnings.append({"code": "inverter_stepped_up", "message": (
                f"The sizing asks for {required:.1f} kW, {over_pct:.0f}% above the default {inverter.code} ({rating:g} kW): {pick.code} {pick.name} "
                f"({float(pick.rating):g} kW, {how}, about ₱{cost:,.0f} landed) is used instead of {units} × {inverter.code} in parallel "
                f"(about ₱{parallel_cost:,.0f}). Pick another under Pricing inputs › Inverter.")})
            return pick, 1, warnings
    what = "the unit you picked" if override else "single unit in the materials list"
    warnings.append({"code": "inverter_parallel", "message": (
        f"The sizing asks for {required:.1f} kW and {what} ({inverter.code}, {rating:g} kW) does not cover it, so {units} × {inverter.code} in parallel are used. "
        f"Confirm parallel operation with the maker, or pick a larger unit under Pricing inputs › Inverter.")})
    return inverter, units, warnings


def pass_through_check(inverter: Optional[Item], units: int, peak_kw: Optional[float], ac_voltage: float) -> tuple[Optional[dict], list[dict]]:
    """E-01: on a net-metering job the grid carries the house peak through the inverter's AC input (bypass), so the
    peak is compared with the unit's AC input rating when the item carries one; unknown or exceeded is a warning."""
    if inverter is None or not peak_kw or peak_kw <= 0:
        return None, []
    peak_a = float(peak_kw) * 1000.0 / ac_voltage
    rating = float(inverter.ac_input_a) if inverter.ac_input_a else None
    block = {"house_peak_kw": float(peak_kw), "house_peak_a": peak_a, "ac_input_a": rating, "units": units, "ok": None}
    warnings: list[dict] = []
    if rating is None:
        warnings.append({"code": "inverter_pass_through_unknown", "message": (
            f"The house peak is {float(peak_kw):.1f} kW ({peak_a:.0f} A at {ac_voltage:g} V) and {inverter.code} {inverter.name} has no AC input rating on its item: "
            f"verify the inverter's grid pass-through rating against it and type it on the Materials page (AC input).")})
    elif rating * units < peak_a - 1e-9:
        block["ok"] = False
        warnings.append({"code": "inverter_pass_through", "message": (
            f"The house peak of {float(peak_kw):.1f} kW ({peak_a:.0f} A) is above the grid pass-through rating of {inverter.code} ({rating:g} A"
            f"{' × ' + str(units) if units > 1 else ''}): the whole house cannot run through the inverter's AC input. Keep the heavy loads on the "
            f"house panel ahead of the inverter, or choose a unit rated for it.")})
    else:
        block["ok"] = True
    return block, warnings


def _role_line(code: str, qty: float, role: str, note: str, warnings: list[dict], label: str) -> BomLine:
    """A BOM line for a role: the item's code when the role has one, else a NO-ITEM line with the quantity and no
    price plus the warning to add the item (never an invented price)."""
    if code:
        return BomLine(code, qty, role, note)
    warnings.append({"code": "role_without_item", "message": (
        f"{label}: no item in the materials list for this role; add one on the Materials page and set it under Pricing settings › BOM item roles. "
        f"The BOM carries the line with its quantity and no price until then.")})
    return BomLine(f"{NO_ITEM_PREFIX}{role.upper().replace('_', '-')}", qty, role, f"{note} (no item in the materials list for this role)")


def generate_boq(req: BoqRequest, catalog: Catalog, cfg: PricingConfig) -> BoqResult:
    w, r = cfg.wiring, cfg.roles
    lines: list[BomLine] = []
    warnings: list[dict] = []
    choices: dict = {}

    panel = catalog.get(req.panel_code)
    if panel is None:
        raise ValueError(f"Panel {req.panel_code} is not in the materials database.")
    lines.append(BomLine(panel.code, req.panel_count, "panel", f"{req.panel_count} x {panel.name}"))

    # inverter: the per-job override, else the default model for this system kind, else the cheapest hybrid that
    # fits. A grid job (net metering, with or without a battery) takes only a grid-interactive unit.
    grid_job = req.kind != "off_grid"
    inv_options = select_inverter(req.inverter_kw, catalog, cfg, req.kind)
    inverter: Optional[Item] = None
    units = max(req.inverter_units, 1)
    required = req.inverter_required_kw or req.inverter_kw * units
    override = False
    if req.inverter_code:
        inverter = catalog.get(req.inverter_code)
        override = inverter is not None
    default_code = r.default_inverter_for(req.kind)
    if inverter is None and default_code:
        cand = catalog.get(default_code)
        if cand is None:
            warnings.append({"code": "default_inverter", "message": f"Default inverter {default_code} is not in the materials list; the cheapest that fits is used."})
        elif grid_job and cand.grid_interactive is False:
            warnings.append({"code": "default_inverter_not_grid", "message": (
                f"The default inverter {cand.code} {cand.name} is an off-grid type, so it is skipped on this net-metering job and the cheapest grid-interactive "
                f"inverter that fits is used. Set a grid default under Pricing settings › BOM item roles, or mark the inverter grid-interactive on the Materials page.")})
        else:
            inverter = cand
    if inverter is None and inv_options:
        inverter = inv_options[0][0]
    if inverter is None:
        what = "grid-interactive hybrid inverter" if grid_job else "hybrid inverter"
        warnings.append({"code": "no_inverter", "message": f"No {what} of {req.inverter_kw:g} kW or more in the materials list. Add one on the Materials page" + (" and mark it grid-interactive." if grid_job else ".")})
        units = 1
    else:
        inverter, units, unit_warnings = choose_inverter_units(inverter, required, override, catalog, cfg, req.kind)
        warnings += unit_warnings
        if grid_job and inverter.grid_interactive is False:
            warnings.append({"code": "inverter_not_grid_interactive", "hard": True, "message": (
                f"{inverter.code} {inverter.name} is an off-grid type: it cannot export and the electric company will not accept it for net metering. "
                f"Choose a grid-interactive inverter under Pricing inputs, or mark this one on the Materials page if its datasheet says otherwise.")})
        elif grid_job and inverter.grid_interactive is None:
            warnings.append({"code": "inverter_certificate_unknown", "message": (
                f"{inverter.code} {inverter.name} is not marked grid-interactive: confirm its anti-islanding certificate (IEC 62116 or UL 1741; verify what the electric company asks for) "
                f"with the maker before the net-metering application, then set Grid-interactive and its certifications on the Materials page.")})
        elif grid_job and not (inverter.certifications or "").strip():
            # E-05: marked able to export, nothing on file: the DU asks for the listing with the application
            warnings.append({"code": "inverter_certificate_missing", "message": (
                f"{inverter.code} {inverter.name} is marked grid-interactive but no certificate is on file; confirm the listing with the maker before the DU application, "
                f"then type it on the Materials page (Certifications). The proposal says the certificate is to be confirmed until then.")})
        note = f"{inverter.rating:g} kW hybrid" + (f", {units} in parallel for {required:g} kW" if units > 1 else "")
        if grid_job:
            note += f", grid-interactive: {_grid_flag(inverter)}"
        lines.append(BomLine(inverter.code, units, "inverter", note))

    def _opt(i: Item, c: float) -> dict:
        return {"code": i.code, "name": i.name, "rating_kw": i.rating, "supplier": i.supplier, "landed": c,
                "grid_interactive": i.grid_interactive, "certifications": i.certifications or ""}
    opts = [_opt(i, c) for i, n, c in inv_options[:6]]
    if inverter and inverter.code not in [o["code"] for o in opts]:
        opts.insert(0, _opt(inverter, landed_cost(inverter, catalog, cfg).landed * units))
    choices["inverter_options"] = opts
    choices["inverter_units"] = units
    choices["inverter_grid_interactive"] = inverter.grid_interactive if inverter else None
    choices["inverter_certifications"] = (inverter.certifications or "") if inverter else ""
    choices["inverter_battery_max_a"] = inverter.battery_max_a if inverter else None
    choices["inverter_ac_input_a"] = inverter.ac_input_a if inverter else None
    choices["inverter_has_transfer_switch"] = inverter.has_transfer_switch if inverter else None
    inv_kw = float(inverter.rating) if inverter and inverter.rating else req.inverter_kw
    i_bat = inv_kw * 1000.0 / w.battery_voltage            # per inverter, at rated output from the battery
    i_bat_max = float(inverter.battery_max_a) if (inverter and inverter.battery_max_a) else i_bat   # the inverter's own limit when known

    # the pass-through check on a net-metering job (no backup mode: the grid carries the house peak through the unit)
    if req.kind == "net_metering":
        pt, pt_warnings = pass_through_check(inverter, units, req.peak_load_kw, w.ac_voltage)
        choices["pass_through"] = pt
        warnings += pt_warnings

    # battery: on continuous current first (the bank must deliver the inverter's battery current), then the cheapest
    # kWh at or above the requirement; the check is hard when the chosen unit falls short
    battery_units = 0
    battery: Optional[Item] = None
    bat_options: list[tuple[Item, int, float]] = []
    if req.battery_kwh > 0:
        bank_current = i_bat_max * units
        bat_options = select_battery(req.battery_kwh, catalog, cfg, bank_current)
        if req.battery_code:
            battery = catalog.get(req.battery_code)
            battery_units = int(math.ceil(req.battery_kwh / battery.rating - 1e-9)) if battery and battery.rating else 0
        elif bat_options:
            battery, battery_units, _ = bat_options[0]
        if battery is None:
            warnings.append({"code": "no_battery", "message": "No battery in the materials list covers the required kWh. Add one with its kWh rating on the Materials page."})
        else:
            battery_units, bat_warnings = battery_current_check(battery, battery_units, inverter, units, i_bat_max)
            warnings += bat_warnings
            lines.append(BomLine(battery.code, battery_units, "battery", f"{battery_units} x {battery.rating:g} kWh = {battery_units * battery.rating:g} kWh"
                                 + (f", {battery_units * float(battery.continuous_a):g} A continuous against {bank_current:.0f} A from the inverter" if battery.continuous_a else "")))
        choices["battery_options"] = [
            {"code": i.code, "name": i.name, "rating_kwh": i.rating, "units": n, "total_kwh": n * i.rating, "supplier": i.supplier, "landed": c,
             "continuous_a": i.continuous_a, "current_ok": battery_current_ok(i, n, bank_current)}
            for i, n, c in bat_options[:8]
        ]
        choices["battery_continuous_a"] = battery.continuous_a if battery else None
        choices["battery_nominal_kwh"] = battery_units * float(battery.rating) if battery and battery.rating else 0.0   # the priced bank, not the sizing's

    # mounting per row
    rails = splices = end_clamps = mid_clamps = 0
    for row in req.rows:
        per_line = int(math.ceil(row.length_m / r.rail_length_m - 1e-9)) if row.panels > 0 else 0
        rails += 2 * per_line
        splices += 2 * max(per_line - 1, 0)
        end_clamps += 4 if row.panels > 0 else 0
        mid_clamps += 2 * max(row.panels - 1, 0)
    n_rows = len([x for x in req.rows if x.panels > 0])
    lines += [
        BomLine(r.rail, rails, "rail", f"{_plural(n_rows, 'row')}, 2 lines each, {r.rail_length_m:g} m rails"),
        BomLine(r.l_foot, rails * r.l_feet_per_rail, "l_foot", f"{r.l_feet_per_rail} per rail"),
        BomLine(r.end_clamp, end_clamps, "end_clamp", "4 per row"),
        BomLine(r.mid_clamp, mid_clamps, "mid_clamp", "2 per panel gap"),
    ]
    if splices > 0:
        lines.append(BomLine(r.splice, splices, "splice", "1 per rail joint"))

    # strings and PV cable; the design temperatures are the job's (compute.py's results["site"]) or the settings alone (round 12)
    sd = cfg.string_design
    t_cold = float(req.t_cold_c) if req.t_cold_c is not None else float(sd.design_cold_c)
    t_hot = float(req.t_hot_c) if req.t_hot_c is not None else float(sd.design_hot_cell_c)
    choices["string_design"] = {"t_cold_c": t_cold, "t_hot_c": t_hot, "temperatures_from": "project" if req.t_cold_c is not None else "settings"}
    strings = req.strings_override or int(math.ceil(req.panel_count / max(r.max_panels_per_string, 1) - 1e-9))
    strings = max(strings, 1)
    per_string = int(math.ceil(req.panel_count / strings))
    panel_w = float(panel.rating or 0) if (panel.rating_unit or "").upper() == "W" else 0.0
    i_string = panel_w / w.panel_vmp_v if panel_w else 0.0
    v_string = per_string * w.panel_vmp_v
    pv_run = req.pv_run_m if req.pv_run_m is not None else w.pv_run_m
    pv_gauge, pv_drop, pv_ok = pick_gauge(i_string, pv_run, v_string, w.dc_drop_limit, w.pv_cable_ampacity, cfg)
    if not pv_ok:
        warnings.append({"code": "pv_cable", "message": f"PV cable: {pv_drop:.1%} drop at {pv_run:g} m even with {pv_gauge} mm²; shorten the run or use a larger cable."})
    lines += [
        BomLine(r.pv_cable_red.get(pv_gauge, r.pv_cable_red["4"]), strings * pv_run, "pv_cable_red", f"{_plural(strings, 'string')} x {pv_run:g} m, {pv_gauge} mm2, {pv_drop:.1%} drop"),
        BomLine(r.pv_cable_black.get(pv_gauge, r.pv_cable_black["4"]), strings * pv_run, "pv_cable_black", f"{_plural(strings, 'string')} x {pv_run:g} m"),
        BomLine(r.mc4_pair, strings * r.mc4_pairs_per_string, "mc4_pair", f"{r.mc4_pairs_per_string} per string"),
    ]

    # AC side (E-04): per inverter, the inverter-side circuit (output to the loads) and the grid-side circuits (the
    # grid to the inverter's AC input and the maintenance bypass). One breaker per circuit at 1.25 x the circuit
    # current rounded up to the next standard size; each side's conductor sized from its breaker (ampacity at or
    # above it) and checked for drop over the run; line and neutral per circuit, the ground on the grounding run.
    i_ac = inv_kw * 1000.0 / w.ac_voltage
    grid_known = bool(inverter and inverter.ac_input_a)
    i_grid = float(inverter.ac_input_a) if grid_known else i_ac
    sizes = w.ac_breaker_sizes_a
    b_inv = next_standard_size(i_ac * w.continuous_factor, sizes)
    b_grid = next_standard_size(i_grid * w.continuous_factor, sizes)
    ac_run = req.ac_run_m if req.ac_run_m is not None else w.ac_run_m
    gnd_run = req.grounding_run_m if req.grounding_run_m is not None else w.grounding_run_m
    g_inv, drop_inv, ok_inv = pick_gauge(i_ac, ac_run, w.ac_voltage, w.ac_drop_limit, w.thhn_ampacity, cfg, min_ampacity=b_inv or 0.0)
    g_grid, drop_grid, ok_grid = pick_gauge(i_grid, ac_run, w.ac_voltage, w.ac_drop_limit, w.thhn_ampacity, cfg, min_ampacity=b_grid or 0.0)
    amp_inv = float(w.thhn_ampacity.get(g_inv, 0.0))
    amp_grid = float(w.thhn_ampacity.get(g_grid, 0.0))
    for side, b, g, amp, ok, cur in (("inverter output", b_inv, g_inv, amp_inv, ok_inv, i_ac), ("grid side", b_grid, g_grid, amp_grid, ok_grid, i_grid)):
        if b is None:
            warnings.append({"code": "ac_circuit", "hard": True, "blocks_documents": True, "message": (
                f"AC {side}: {cur:.0f} A × 1.25 = {cur * w.continuous_factor:.0f} A is above the largest standard breaker size in Pricing settings › Wiring rules. "
                f"Add the size, or choose a smaller unit. The customer documents are held until the circuit holds.")})
        elif amp < b - 1e-9:
            warnings.append({"code": "ac_circuit", "hard": True, "blocks_documents": True, "message": (
                f"AC {side}: the {b:g} A breaker needs a conductor rated at least {b:g} A and the largest THHN size in Pricing settings › Wiring rules carries {amp:g} A. "
                f"Add a larger THHN size to the list and its code under BOM item roles. The customer documents are held until the circuit holds.")})
        elif not ok:
            warnings.append({"code": "ac_cable", "message": f"AC {side}: {cur:.0f} A at {ac_run:g} m exceeds the {w.ac_drop_limit:.0%} drop limit even with {g} mm² THHN. Shorten the run or add a larger THHN size to the list."})
    if not grid_known:
        warnings.append({"code": "ac_grid_rating_unknown", "message": (
            f"The grid-side breakers and conductors are sized on the inverter's output ({i_ac:.0f} A) because {inverter.code if inverter else 'the inverter'} has no AC input "
            f"(grid pass-through) rating on its item. Type it on the Materials page (AC input) so the grid side is sized on the pass-through current.")})
    n_cond = max(int(w.ac_conductors_per_circuit), 1)
    inv_circuits = max(int(r.ac_breakers_per_inverter), 0)
    grid_circuits = max(int(r.ac_grid_breakers_per_inverter), 0)
    inv_m = units * inv_circuits * n_cond * ac_run
    grid_m = units * grid_circuits * n_cond * ac_run
    gnd_m = units * gnd_run
    inv_txt = f"{_plural(inv_circuits, 'inverter-output circuit')} × {n_cond} conductors × {ac_run:g} m"
    grid_txt = f"{_plural(grid_circuits, 'grid-side circuit')} × {n_cond} conductors × {ac_run:g} m"
    per_inv = " per inverter" if units > 1 else ""
    if g_inv == g_grid:
        thhn_code = r.thhn.get(g_inv) or next(iter(r.thhn.values()))
        lines.append(BomLine(thhn_code, inv_m + grid_m + gnd_m, "thhn", (
            f"{inv_txt} + {grid_txt} + {gnd_run:g} m grounding{per_inv}; {g_inv} mm2 ({amp_inv:g} A) for the {b_inv:g} A breakers, {max(drop_inv, drop_grid):.1%} drop")))
    else:
        lines.append(BomLine(r.thhn.get(g_inv) or next(iter(r.thhn.values())), inv_m + gnd_m, "thhn",
                             f"{inv_txt} + {gnd_run:g} m grounding{per_inv}; {g_inv} mm2 ({amp_inv:g} A) for the {b_inv:g} A breaker, {drop_inv:.1%} drop"))
        lines.append(BomLine(r.thhn.get(g_grid) or next(iter(r.thhn.values())), grid_m, "thhn_grid",
                             f"{grid_txt}{per_inv}; {g_grid} mm2 ({amp_grid:g} A) for the {b_grid:g} A breakers, {drop_grid:.1%} drop"))

    # battery cable and breaker (E-03): the breaker at or above 1.25 x the inverter's battery current (its own
    # maximum when the item carries it, else the rated output over the battery voltage), the cable's ampacity at or
    # above the breaker, so the breaker protects the conductor; a coordination that cannot be met is a hard warning
    battery_circuit: Optional[dict] = None
    if battery_units > 0:
        amps_req = i_bat_max * w.continuous_factor
        bb = _by_amps(r.battery_breaker_pattern, amps_req, catalog, cfg) or catalog.get(r.battery_breaker_fallback)
        bb_amps = bb.amps_in_name() if bb else None
        need_amp = max(amps_req, float(bb_amps or 0.0))
        bat_gauge, _, bat_ok = pick_gauge(i_bat_max, 1.0, w.battery_voltage, 0.5, w.battery_cable_ampacity, cfg, min_ampacity=need_amp)
        cable_amp = float(w.battery_cable_ampacity.get(bat_gauge, 0.0))
        breaker_ok = bb is not None and bb_amps is not None and bb_amps >= amps_req - 1e-9
        cable_ok = bat_ok and cable_amp >= float(bb_amps or 0.0) - 1e-9
        if not breaker_ok:
            warnings.append({"code": "battery_circuit", "hard": True, "blocks_documents": True, "message": (
                f"Battery circuit: the inverter side needs a battery breaker of at least {amps_req:.0f} A (1.25 × {i_bat_max:.0f} A) and "
                + (f"the largest \"{r.battery_breaker_pattern}\" item in the list is {bb_amps:.0f} A" if bb_amps else "no battery breaker in the list carries a rating")
                + ". Add a larger one on the Materials page. The customer documents are held until the circuit holds.")})
        elif not cable_ok:
            warnings.append({"code": "battery_circuit", "hard": True, "blocks_documents": True, "message": (
                f"Battery circuit: the {bb_amps:.0f} A breaker needs a battery cable rated at least {bb_amps:.0f} A and the largest lug pair in "
                f"Pricing settings › Wiring rules carries {cable_amp:.0f} A. Add a larger lug pair to the list and its code under BOM item roles. "
                f"The customer documents are held until the circuit holds.")})
        lines.append(BomLine(r.battery_cable_pair.get(bat_gauge, r.battery_cable_pair["35"]), w.battery_pairs_per_battery * battery_units, "battery_cable",
                             f"{bat_gauge} mm2 lug pairs ({cable_amp:.0f} A) for the {bb_amps:.0f} A breaker; inverter battery current {i_bat_max:.0f} A" if bb_amps
                             else f"{bat_gauge} mm2 lug pairs ({cable_amp:.0f} A) for {i_bat_max:.0f} A"))
        if bb:
            lines.append(BomLine(bb.code, units, "battery_breaker", f"{bb_amps:.0f} A for {amps_req:.0f} A (1.25 × {i_bat_max:.0f} A inverter battery current); cable {cable_amp:.0f} A"
                                 if bb_amps else f"for {amps_req:.0f} A (1.25 × {i_bat_max:.0f} A inverter battery current)"))
        battery_circuit = {"current_a": i_bat_max, "breaker_min_a": amps_req, "breaker_a": bb_amps, "cable_gauge": bat_gauge, "cable_ampacity_a": cable_amp,
                           "ok": bool(breaker_ok and cable_ok)}

    # protection: one DC breaker per string, one DC SPD per MPPT input in use, one AC SPD per board, the breakers
    # per circuit, the transfer switch unless the inverter carries its own, the visible AC disconnect for the DU
    lines.append(BomLine(r.dc_breaker, strings, "dc_breaker", "1 per string"))
    mppt = int(inverter.mppt_count) if inverter and inverter.mppt_count else 0
    dc_spds = min(strings, units * mppt) if mppt else units
    lines.append(BomLine(r.dc_spd, dc_spds, "dc_spd", f"1 per MPPT input in use ({_plural(strings, 'string')} on {units * mppt} MPPT inputs)" if mppt else "1 per inverter (MPPT count not on the item; verify)"))
    i_grid_req = i_grid * w.continuous_factor
    has_ts = inverter.has_transfer_switch if inverter else None
    if has_ts is True:
        choices["ats"] = "built-in"
    else:
        if has_ts is None and inverter is not None:
            warnings.append({"code": "ats_unknown", "message": (
                f"{inverter.code} {inverter.name} does not say whether it has its own transfer switch, so an external ATS is priced. "
                f"If the manual shows a built-in transfer, mark it on the Materials page (Transfer switch) and the ATS drops out.")})
        ats = catalog.get(r.ats)
        if r.ats_amps < i_grid_req:
            alt = _by_amps(r"ATS", i_grid_req, catalog, cfg)
            if alt:
                ats = alt
            else:
                warnings.append({"code": "ats", "message": f"No transfer switch (ATS) rated for {i_grid_req:.0f} A in the materials list. Add one on the Materials page."})
        if ats:
            lines.append(BomLine(ats.code, units, "ats", f"transfer switch, {i_grid_req:.0f} A continuous (grid side)"))
    ac_breaker_item = catalog.get(r.ac_breaker)
    breakers = units * (inv_circuits + grid_circuits)
    b_note = (f"{_plural(inv_circuits, 'inverter-output breaker')} at {b_inv:g} A (1.25 × {i_ac:.0f} A → next standard size); "
              f"{_plural(grid_circuits, 'grid-side breaker')} at {b_grid:g} A (1.25 × {i_grid:.0f} A"
              + (", the inverter's AC input rating" if grid_known else ", the output current: AC input rating unknown") + ")" + per_inv)
    lines.append(BomLine(r.ac_breaker, breakers, "ac_breaker", b_note))
    if ac_breaker_item is not None:
        listed = ac_breaker_item.amps_listed()
        missing = sorted({b for b in (b_inv, b_grid) if b is not None and listed and b not in listed})
        if missing:
            warnings.append({"code": "ac_breaker_size", "message": (
                f"The AC breaker item {ac_breaker_item.code} is listed in {', '.join(f'{x:g}' for x in listed)} A; the circuits need "
                f"{' and '.join(f'{x:g}' for x in missing)} A. Add that size to the materials list and set it under Pricing settings › BOM item roles, "
                f"or confirm the supplier stocks it under the same code.")})
    lines.append(BomLine(r.ac_spd, units * r.ac_spds_per_inverter, "ac_spd", f"{r.ac_spds_per_inverter} Type 2 per AC board" + per_inv))
    disc_note = f"visible, lockable AC disconnect for the electric company at the service, rated at least {b_grid:g} A (verify the DU's requirement)" if b_grid else \
        "visible, lockable AC disconnect for the electric company at the service (verify the DU's requirement)"
    lines.append(_role_line(r.ac_disconnect, r.ac_disconnects, "ac_disconnect", disc_note, warnings, "AC disconnect"))
    disc = catalog.get(r.ac_disconnect) if r.ac_disconnect else None
    if disc is not None and b_grid and disc.amps_in_name() is not None and disc.amps_in_name() < b_grid - 1e-9:
        warnings.append({"code": "ac_disconnect_rating", "message": f"The AC disconnect {disc.code} is rated {disc.amps_in_name():g} A and the grid-side circuit needs {b_grid:g} A. Set a larger one under BOM item roles."})

    # enclosures, raceways, grounding and bonding, consumables, the export limiter (fasteners come with the L-foot set,
    # placards are consumables and monitoring is in the inverter: the owner's rule, round 4)
    conduit = req.conduit_m if req.conduit_m is not None else w.conduit_m
    row_len = sum(x.length_m for x in req.rows if x.panels > 0)
    bonding_m = row_len + r.bonding_extra_m_per_row * n_rows
    lugs = r.earth_lugs + req.panel_count * r.bonding_lugs_per_panel + 2 * n_rows * r.bonding_lugs_per_rail_line
    lines += [
        BomLine(r.enclosure, r.enclosures * units, "enclosure", f"{r.enclosures} per inverter: AC and DC protection in one box" if r.enclosures == 1 else f"{r.enclosures} per inverter"),
        BomLine(r.cable_tray, r.cable_trays, "cable_tray", ""),
        BomLine(r.conduit, conduit, "conduit", "allowance"),
        BomLine(r.ground_rod, r.ground_rods, "ground_rod", ""),
        _role_line(r.array_bonding_wire, round(bonding_m, 1), "array_bonding",
                   f"equipment grounding conductor along the array: {row_len:.1f} m of rail line over {_plural(n_rows, 'row')} + {r.bonding_extra_m_per_row:g} m per row of jumpers (bare copper where the LGU asks; verify the gauge with the PEE)",
                   warnings, "Array bonding conductor"),
        BomLine(r.earth_lug, lugs, "earth_lug", f"{r.earth_lugs} at the boxes and the rod + {r.bonding_lugs_per_panel} per panel + {r.bonding_lugs_per_rail_line} per rail line ({2 * n_rows} lines)"),
        BomLine(r.sealant, r.sealants, "sealant", ""),
    ]
    if grid_job:
        if r.export_limiter:
            lines.append(BomLine(r.export_limiter, 1, "export_limiter", "export limit between switch-on and the two-way meter (verify the DU's rule)"))
        else:
            warnings.append({"code": "export_limiter", "message": (
                "Between switch-on and the two-way meter the power sent to the grid is not credited and the electric company may ask for an export limit "
                "(verify with Meralco or BATELEC II). No export-limiter item is set under Pricing settings › BOM item roles, so none is priced.")})
    for l in lines:
        if catalog.get(l.code) is None and not l.code.startswith(NO_ITEM_PREFIX):
            warnings.append({"code": "missing_item", "message": f"Code {l.code} (used for {l.role}) is not in the materials list. Add it on the Materials page or change the role in Pricing settings."})
    choices.update({
        "strings": strings, "panels_per_string": per_string, "string_current_a": i_string, "string_voltage_v": v_string,
        "pv_gauge": pv_gauge, "pv_drop": pv_drop, "ac_current_a": i_ac, "ac_gauge": g_inv, "ac_drop": drop_inv,
        "ac_breaker_a": b_inv, "ac_grid_current_a": i_grid, "ac_grid_rating_known": grid_known, "ac_grid_breaker_a": b_grid, "ac_grid_gauge": g_grid, "ac_grid_drop": drop_grid,
        "inverter_code": inverter.code if inverter else None, "battery_code": battery.code if battery else None, "battery_units": battery_units,
        "rows": [{"panels": x.panels, "length_m": x.length_m} for x in req.rows],
        "kind": req.kind, "battery_current_a": i_bat_max, "battery_breaker_min_a": i_bat_max * w.continuous_factor, "battery_circuit": battery_circuit,
        "dc_spds": dc_spds,
    })
    return BoqResult([l for l in lines if l.qty > 0], choices, warnings)
