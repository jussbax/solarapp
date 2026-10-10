"""The design analysis (round 13, docs/audits/round-13/engineer-brief.md, section 2): the derating engine, the overcurrent
protection check per circuit against the derated ampacity, the conduit fill, the equipment and electrode grounding
conductor sizes and the short-circuit note, written onto the `pricing.choices.circuits` records the BOQ built (step 1)
and into one job-level block `pricing.choices.design_analysis` the design analysis sheet prints.

Nothing invented: every table value here is a cited stand-in in the settings (`config.DeratingRules`,
`config.GroundingRules`, the 75 and 90 °C THHN columns of `config.WiringRules`) with its source line and a `_verified`
flag the sheet prints with "verify" until the owner or the PEE ticks it; every default temperature and the insulation
rating of a wire item that has none are ASSUMPTIONS and print as such. A check that needs a figure not on file (the
conductor's area, the conduit's inside diameter, the breaker's rating without Isc) reads "not checked" with the reason,
never a silent default, and so does a BOM role the bill lacks (the battery rack's EGC, the round-13 review's finding 12);
a table the app does not hold for a conductor type at all (the cable's 75 °C column) is a "verify" qualifier, never a
pass on its own.

The computation (2.3):
    T_conductor = T_ambient (+ the rooftop adder for a raceway on the roof)
    F_temp = sqrt((T_insul − T_conductor) / (T_insul − 30))            NEC 310.15(B)(2) formula; PEC verify
    F_fill = the bundling factor by current-carrying conductors         NEC 310.15(B)(3)(a); PEC verify
    ampacity_derated = ampacity_base(T_insul column) × F_temp × F_fill
    OCPD at or below ampacity_derated, else the next standard size above it when the rating is ≤ 800 A and the conductor still
        carries the continuous current (NEC 240.4(B); PEC 2.40 verify) → "next size up", still a pass
    ampacity_terminal (the 75 °C column, uncorrected) at or above i_design and OCPD   NEC 110.14(C); verify
    fill % = Σ A_conductor / (π/4 × d_inner²) against 53 / 31 / 40 %        NEC Chapter 9 Table 1; PEC Chapter 10 verify
    EGC required by the OCPD rating                                          NEC 250.122; PEC Table 2.50.1.122 verify

Severity (the coordinator's decision): a conductor the breaker does not protect at temperature (`conductor_derated`),
a terminal-ampacity failure (`terminal_ampacity`) and a breaker whose interrupting rating is below the DU's fault level
at the service (`aic_below_fault`, the round-13 review's finding 1) are hard and block the customer documents, as the
round-3 AC coordination does; the conduit fill (`conduit_fill`) and an undersized EGC (`egc_undersized`) are hard and
print without blocking; a figure missing (`derating_not_checked`) and the fault level unknown (`fault_level_unknown`)
are ordinary.
"""
from __future__ import annotations

import math
from typing import Any, Optional

from .catalog import Catalog, Item
from .config import PricingConfig
from .design_checks import NOT_YET_DERATED

# the conductor's BOM role per circuit kind (the record carries no conductor code: the role line names the item)
CONDUCTOR_ROLE = {"dc_pv": "pv_cable_red", "dc_battery": "battery_cable", "ac_inverter_output": "thhn", "ac_grid_feed": "thhn_grid", "ac_bypass": "thhn_grid", "egc": "thhn"}
# the kinds whose breaker comes from a standard-size list (the next-size-up rule needs one); the battery breaker is picked
# from the catalogue's "BATTERY BREAKER" ratings, not a list, so the rule is not applied there
STANDARD_SIZES_OF = {"dc_pv": "dc", "dc_combined": "dc", "ac_inverter_output": "ac", "ac_grid_feed": "ac", "ac_bypass": "ac"}
NOT_YET_EGC = "the sizes required per OCPD and the grounding electrode conductor: not computed yet (the design analysis is a later step)"


# ---------------------------------------------------------------- the pure pieces (hand-worked in the tests, 2.6)

def cite(source: str, verified: bool) -> str:
    """A table's source line with its flag: "verify" until the owner or the PEE ticks the table confirmed in Settings."""
    return f"{source}; {'confirmed in Settings' if verified else 'verify'}"


def temperature_factor(t_insulation_c: float, t_conductor_c: float) -> Optional[float]:
    """F_temp = sqrt((T_insul − T_cond) / (T_insul − 30)); None when the conductor reaches its insulation rating."""
    if t_insulation_c <= 30 or t_conductor_c >= t_insulation_c:
        return None
    return math.sqrt((t_insulation_c - t_conductor_c) / (t_insulation_c - 30.0))


def band_value(table: dict[str, float], x: float) -> Optional[float]:
    """The value of the band whose lower bound is the largest key at or below x (the rooftop adder by height, the bundling
    factor by conductor count); None when x is below the first band or the table is empty."""
    best: Optional[tuple[float, float]] = None
    for k, v in table.items():
        try:
            lo = float(k)
        except (TypeError, ValueError):
            continue
        if lo <= x + 1e-9 and (best is None or lo > best[0]):
            best = (lo, float(v))
    return None if best is None else best[1]


def step_value(table: dict[str, float], x: float) -> Optional[tuple[float, float]]:
    """(key, value) of the smallest key at or above x (the EGC by OCPD rating, the fill limit by conductor count: the count
    at or above is the row); None above the largest key."""
    best: Optional[tuple[float, float]] = None
    for k, v in table.items():
        try:
            hi = float(k)
        except (TypeError, ValueError):
            continue
        if hi >= x - 1e-9 and (best is None or hi < best[0]):
            best = (hi, float(v))
    return best


def bundling_factor(n_current_carrying: int, table_pct: dict[str, float]) -> Optional[float]:
    v = band_value(table_pct, max(int(n_current_carrying), 1))
    return None if v is None else v / 100.0


def rooftop_adder(height_mm: float, table: dict[str, float]) -> Optional[float]:
    return band_value(table, max(float(height_mm), 0.0))


def next_standard_size(amps: float, sizes: list[float]) -> Optional[float]:
    for s in sorted(float(x) for x in sizes):
        if s >= amps - 1e-9:
            return s
    return None


def conduit_fill_pct(areas_mm2: list[float], inner_diameter_mm: float) -> Optional[float]:
    """Σ A_conductor / (π/4 × d_inner²), in percent; None without a diameter."""
    if not inner_diameter_mm or inner_diameter_mm <= 0:
        return None
    return sum(areas_mm2) / (math.pi / 4.0 * float(inner_diameter_mm) ** 2) * 100.0


def fill_limit_pct(n_conductors: int, table: dict[str, float]) -> Optional[float]:
    """53 % for one conductor, 31 % for two, 40 % for three or more: the band is the largest key at or below the count."""
    return band_value(table, max(int(n_conductors), 1))


def egc_required_mm2(ocpd_a: float, table: dict[str, float]) -> Optional[tuple[float, float]]:
    """(the table row's OCPD rating, the EGC size) for the smallest rating at or above the breaker; None above the table."""
    return step_value(table, float(ocpd_a))


def ambient_for(placement: Optional[str], cfg: PricingConfig, tmy_max_air_c: Optional[float]) -> dict:
    """Outdoors (a rooftop placement) the higher of the setting and ceil(the project cell's typical-year air maximum);
    indoors the setting. Both settings are assumptions; the sheet says which figure was used and why."""
    d = cfg.derating
    outdoor = str(placement or "").startswith("rooftop")
    if outdoor:
        setting = float(d.ambient_outdoor_c)
        cell = float(math.ceil(float(tmy_max_air_c))) if tmy_max_air_c is not None else None
        if cell is not None and cell > setting:
            return {"ambient_c": cell, "source": "tmy", "assumed": False, "outdoor": True,
                    "basis": f"the project cell's typical-year air maximum {float(tmy_max_air_c):.1f} °C ceiled to {cell:g} °C, above the {setting:g} °C setting"}
        return {"ambient_c": setting, "source": "setting", "assumed": True, "outdoor": True,
                "basis": f"the derating setting's outdoor ambient {setting:g} °C (an assumption"
                         + (f"; the project cell's typical-year maximum is {float(tmy_max_air_c):.1f} °C" if tmy_max_air_c is not None else "; no project weather") + ")"}
    setting = float(d.ambient_indoor_c)
    return {"ambient_c": setting, "source": "setting", "assumed": True, "outdoor": False, "basis": f"the derating setting's indoor ambient {setting:g} °C (an assumption)"}


# ---------------------------------------------------------------- one circuit

def _size_key(size: Optional[float], table: dict[str, float]) -> Optional[str]:
    """The table key that names a conductor size (8.0 and "8.0", 14 and "14")."""
    if size is None:
        return None
    for k in table:
        try:
            if abs(float(k) - float(size)) < 1e-9:
                return k
        except (TypeError, ValueError):
            continue
    return None


def base_ampacity(row: dict, conductor: Optional[Item], cfg: PricingConfig) -> dict:
    """The conductor's ampacity at its insulation rating: THHN from the column of the insulation rating (the 60, 75 or 90 °C
    THHN tables); PV wire and battery cable from the maker's figure typed on the item, else the wiring rules' cable table as
    the base at 90 °C with "verify the cable's rating". The insulation rating is the item's, else the setting's 90 °C said as
    an assumption."""
    w, d = cfg.wiring, cfg.derating
    size = row["conductors"].get("size_mm2")
    ctype = row["conductors"].get("type")
    out: dict = {"insulation_c": None, "insulation_assumed": False, "base_a": None, "column": None, "verify": [], "reason": None}
    if conductor is not None and conductor.insulation_c:
        out["insulation_c"] = float(conductor.insulation_c)
    else:
        out["insulation_c"], out["insulation_assumed"] = float(d.default_insulation_c), True
    t_ins = out["insulation_c"]
    if ctype == "THHN":
        col = {60.0: (w.thhn_ampacity, "THHN 60 °C column"), 75.0: (w.thhn_ampacity_75c, "THHN 75 °C column"), 90.0: (w.thhn_ampacity_90c, "THHN 90 °C column")}.get(t_ins)
        if col is None:
            out["reason"] = f"no THHN ampacity table for a {t_ins:g} °C insulation rating (the wiring rules hold 60, 75 and 90 °C columns)"
            return out
        table, name = col
        key = _size_key(size, table)
        if key is None:
            out["reason"] = f"the {size:g} mm² size is not in the {name} (Pricing settings › Wiring rules)" if size is not None else "the conductor's size is not on the record"
            return out
        out["base_a"], out["column"] = float(table[key]), name
        if not w.thhn_ampacity_verified:
            out["verify"].append("THHN columns")
        return out
    if ctype in ("PV wire", "battery cable"):
        if conductor is not None and conductor.ampacity_a:
            out["base_a"], out["column"] = float(conductor.ampacity_a), f"the maker's ampacity typed on {conductor.code} at {t_ins:g} °C"
            return out
        table = w.pv_cable_ampacity if ctype == "PV wire" else w.battery_cable_ampacity
        key = _size_key(size, table)
        if key is None:
            out["reason"] = f"the {size:g} mm² size is not in the wiring rules' {ctype} table" if size is not None else "the conductor's size is not on the record"
            return out
        out["base_a"], out["column"] = float(table[key]), f"the wiring rules' {ctype} table as the base at {t_ins:g} °C"
        out["verify"].append("the cable's rating")
        return out
    out["reason"] = "no conductor on the BOM for this circuit" if ctype is None else f"no ampacity table for a {ctype}"
    return out


def terminal_ampacity(row: dict, cfg: PricingConfig) -> tuple[Optional[float], Optional[str]]:
    """The conductor's ampacity in the terminal's column, uncorrected: the THHN column of the terminal rating; None for a
    cable type the app holds no such column for (the PV and battery cables), said so."""
    w, d = cfg.wiring, cfg.derating
    if row["conductors"].get("type") != "THHN":
        return None, f"no {float(d.terminal_rating_c):g} °C column on file for the {row['conductors'].get('type') or 'conductor'}: verify the terminal rating"
    col = {60.0: w.thhn_ampacity, 75.0: w.thhn_ampacity_75c, 90.0: w.thhn_ampacity_90c}.get(float(d.terminal_rating_c))
    if col is None:
        return None, f"no THHN column for a {float(d.terminal_rating_c):g} °C terminal rating"
    key = _size_key(row["conductors"].get("size_mm2"), col)
    if key is None:
        return None, "the conductor's size is not in the terminal column"
    return float(col[key]), None


def derate_circuit(row: dict, cfg: PricingConfig, conductor: Optional[Item], conduit: Optional[Item], *, tmy_max_air_c: Optional[float] = None,
                   ambient_c: Optional[float] = None, egc_sizes_served: Optional[list[float]] = None) -> dict:
    """Fills one circuit record in place (the ambient, the adder, the factors, the base, terminal and derated figures, the
    fill, the EGC sizes, the five derated checks, the status and the notes) and returns {"warnings": [...], "not_checked":
    [...reasons], "qualifiers": [...]}. `ambient_c` overrides the placement's ambient (the hand-worked tests); the C7 row takes
    `egc_sizes_served`, the sizes the grounding run must cover."""
    d, g = cfg.derating, cfg.grounding
    checks, notes = row["checks"], row["notes"]
    warnings: list[dict] = []
    not_checked: list[str] = []
    qualifiers: list[str] = []
    notes[:] = [n for n in notes if n not in (NOT_YET_DERATED, NOT_YET_EGC)]
    cid, kind = row["id"], row["kind"]
    label = f"{cid} {row['name']}"

    if kind == "egc":
        # the grounding run: no derating (it carries no current); its size against the largest EGC the circuits it serves need
        provided = row.get("egc_provided_mm2")
        served = [s for s in (egc_sizes_served or []) if s is not None]
        if served:
            row["egc_required_mm2"] = max(served)
            notes.append(f"EGC required: the largest the AC circuits it serves need, {max(served):g} mm² ({cite(g.egc_source, g.egc_verified)})")
        if row["egc_required_mm2"] is not None and provided is not None:
            checks["egc_ok"] = float(provided) >= float(row["egc_required_mm2"]) - 1e-9
            if not checks["egc_ok"]:
                warnings.append({"code": "egc_undersized", "hard": True, "message": (
                    f"{label}: the grounding run is on the {float(provided):g} mm² THHN line and the circuits it serves need {float(row['egc_required_mm2']):g} mm² "
                    f"({cite(g.egc_source, g.egc_verified)}). Put the grounding run on a larger line (Pricing settings › BOM item roles).")})
        elif provided is None:
            not_checked.append("the grounding run's size is not on the record")
        else:
            not_checked.append("no AC circuit on the job names the EGC it needs")
        if not g.egc_verified:
            qualifiers.append("EGC table: verify")
        row["status"] = "fail" if any(v is False for v in checks.values()) else ("not checked" if not_checked else "pass")
        row["qualifiers"], row["not_checked"] = qualifiers, not_checked
        return {"warnings": warnings, "not_checked": not_checked, "qualifiers": qualifiers}

    # 1. the ambient and the conductor's temperature
    amb = ambient_for(row.get("placement"), cfg, tmy_max_air_c)
    if ambient_c is not None:
        amb = {"ambient_c": float(ambient_c), "source": "given", "assumed": False, "outdoor": amb["outdoor"], "basis": f"ambient {float(ambient_c):g} °C as given"}
    row["ambient_c"] = amb["ambient_c"]
    adder = 0.0
    if row.get("placement") == "rooftop_conduit":
        band = rooftop_adder(float(d.conduit_height_above_roof_mm), d.rooftop_adder_c)
        if band is None:
            not_checked.append("no rooftop adder band covers the conduit's height above the roof (Pricing settings › Design analysis)")
        else:
            adder = band
            notes.append(f"rooftop adder +{adder:g} °C for a raceway {float(d.conduit_height_above_roof_mm):g} mm above the roof (the height is an assumption: a conduit on the rails; "
                         f"{cite(d.rooftop_adder_source, d.rooftop_adder_verified)})")
            qualifiers.append(f"rooftop adder +{adder:g} °C at an assumed {float(d.conduit_height_above_roof_mm):g} mm")
    row["rooftop_adder_c"] = adder
    row["t_conductor_c"] = amb["ambient_c"] + adder
    notes.append(f"ambient: {amb['basis']}" + (f"; the conductor's temperature {row['t_conductor_c']:g} °C with the adder" if adder else ""))
    if amb["assumed"]:
        qualifiers.append(f"ambient assumed {amb['ambient_c']:g} °C")

    # 2. the base ampacity at the insulation rating, the terminal figure
    conductor_code = conductor.code if conductor is not None else None
    base = base_ampacity(row, conductor, cfg)
    row["conductors"]["insulation_c"] = base["insulation_c"]
    row["ampacity_base_a"], row["ampacity_base_column"] = base["base_a"], base["column"]
    row["conductor_code"] = conductor_code
    if base["insulation_assumed"]:
        qualifiers.append(f"insulation assumed {base['insulation_c']:g} °C")
        notes.append(f"insulation {base['insulation_c']:g} °C: the derating setting's default (an assumption; "
                     + (f"type the rating on {conductor_code} on the Materials page)" if conductor_code else "no conductor item to type it on)"))
    for v in base["verify"]:
        qualifiers.append(f"{v}: verify")
    if base["base_a"] is None:
        not_checked.append(base["reason"] or "no base ampacity")
    else:
        notes.append(f"base ampacity {base['base_a']:g} A: {base['column']}")
    term_a, term_reason = terminal_ampacity(row, cfg)
    row["ampacity_terminal_a"] = term_a
    if term_reason:
        qualifiers.append(term_reason)

    # 3. the factors and the derated figure
    f_temp = temperature_factor(base["insulation_c"], row["t_conductor_c"])
    n_cc = int(row["conductors"].get("n_current_carrying") or 0)
    f_fill = bundling_factor(n_cc, d.bundling_factor_pct) if n_cc else None
    row["f_temp"], row["f_fill"] = f_temp, f_fill
    if f_temp is None:
        checks["ocpd_le_derated"] = False
        row["ampacity_derated_a"] = 0.0
        warnings.append({"code": "conductor_derated", "hard": True, "blocks_documents": True, "message": (
            f"{label}: the conductor runs at {row['t_conductor_c']:g} °C, at or above its {base['insulation_c']:g} °C insulation rating: it has no ampacity there. "
            "Move the run or use a conductor rated higher. The proposal, roof check, card and plans are held.")})
    elif f_fill is None:
        not_checked.append("no bundling band covers the conductor count (Pricing settings › Design analysis)")
    if f_temp is not None:
        notes.append(f"F_temp {f_temp:.3f} = sqrt(({base['insulation_c']:g} − {row['t_conductor_c']:g}) / ({base['insulation_c']:g} − 30)) ({cite(d.temperature_correction_source, d.temperature_correction_verified)})")
    if f_fill is not None:
        notes.append(f"F_fill {f_fill:.2f} for {n_cc} current-carrying conductors ({cite(d.bundling_factor_source, d.bundling_factor_verified)})")
    if base["base_a"] is not None and f_temp is not None and f_fill is not None:
        row["ampacity_derated_a"] = base["base_a"] * f_temp * f_fill

    # 4. the overcurrent device against the derated ampacity, the next-size-up rule, the terminal rule
    ocpd = row.get("ocpd_a")
    derated = row.get("ampacity_derated_a")
    if ocpd is None:
        not_checked.append("the breaker's rating is not checked without Isc on file" if kind == "dc_pv" else "no breaker rating on the record")
    elif derated is not None and f_temp is not None:
        ocpd, derated = float(ocpd), float(derated)
        checks["ocpd_le_derated"] = ocpd <= derated + 1e-9
        if checks["ocpd_le_derated"]:
            checks["next_size_up_used"] = False
            notes.append(f"OCPD {ocpd:g} A at or below the derated {derated:.1f} A")
        else:
            sizes_of = STANDARD_SIZES_OF.get(kind)
            sizes = (cfg.string_design.dc_breaker_sizes_a if sizes_of == "dc" else cfg.wiring.ac_breaker_sizes_a) if sizes_of else []
            nxt = next_standard_size(derated, sizes) if sizes else None
            i_cont = row.get("i_continuous_a")
            carries = i_cont is not None and derated >= float(i_cont) - 1e-9
            if nxt is not None and abs(nxt - ocpd) < 1e-9 and ocpd <= float(d.next_size_up_max_a) + 1e-9 and carries:
                checks["next_size_up_used"] = True
                notes.append(f"OCPD {ocpd:g} A is above the derated {derated:.1f} A but is the next standard size above it, at or below {float(d.next_size_up_max_a):g} A, "
                             f"on a single-load circuit whose conductor still carries the {float(i_cont):.2f} A continuous current: allowed ({cite(d.next_size_up_source, d.next_size_up_verified)})")
                qualifiers.append("next size up")
            else:
                checks["next_size_up_used"] = False
                why = (f"the next standard size above {derated:.1f} A is {nxt:g} A" if nxt is not None else ("no standard-size list applies to this breaker" if not sizes else f"no standard size at or above {derated:.1f} A"))
                if not carries and i_cont is not None:
                    why += f"; the derated ampacity is below the {float(i_cont):.2f} A continuous current"
                size = row["conductors"].get("size_mm2")
                warnings.append({"code": "conductor_derated", "hard": True, "blocks_documents": True, "message": (
                    f"{label}: the {ocpd:g} A breaker is above the {derated:.1f} A the {f'{size:g} mm² ' if size else ''}{row['conductors'].get('type') or 'conductor'} carries at "
                    f"{row['t_conductor_c']:g} °C ({base['base_a']:g} A × F_temp {f_temp:.3f} × F_fill {f_fill:.2f}), and the next-size-up rule does not apply ({why}): "
                    "the breaker does not protect the conductor at temperature. Use a larger conductor or move the run. The proposal, roof check, card and plans are held.")})
    if term_a is not None and ocpd is not None and row.get("i_design_a") is not None:
        checks["terminal_ge_design"] = term_a >= float(row["i_design_a"]) - 1e-9 and term_a >= float(ocpd) - 1e-9
        notes.append(f"terminal {term_a:g} A ({float(d.terminal_rating_c):g} °C column, uncorrected) against the design current {float(row['i_design_a']):.1f} A and the {float(ocpd):g} A breaker "
                     f"({cite(d.terminal_rule_source, d.terminal_rule_verified)})")
        if not checks["terminal_ge_design"]:
            warnings.append({"code": "terminal_ampacity", "hard": True, "blocks_documents": True, "message": (
                f"{label}: the conductor's {float(d.terminal_rating_c):g} °C ampacity {term_a:g} A is below the {float(row['i_design_a']):.1f} A design current or the {float(ocpd):g} A breaker "
                f"({cite(d.terminal_rule_source, d.terminal_rule_verified)}): the terminals are rated below the load. Use a larger conductor. The proposal, roof check, card and plans are held.")})
    elif term_a is not None and ocpd is None:
        pass   # the breaker is not checked: said above

    # 5. the conduit fill
    placement = str(row.get("placement") or "")
    if placement.endswith("_conduit"):
        n_total = int(row["conductors"].get("n_total") or 0)
        with_egc = kind in ("ac_inverter_output", "ac_grid_feed", "ac_bypass")   # the grounding run shares the AC circuits' raceway (the same THHN line)
        n_in = n_total + (1 if with_egc else 0)
        area = float(conductor.overall_area_mm2) if conductor is not None and conductor.overall_area_mm2 else None
        dia = float(conduit.inner_diameter_mm) if conduit is not None and conduit.inner_diameter_mm else None
        row["conduit_inner_diameter_mm"] = dia
        row["conductor_area_mm2"] = area
        missing = []
        if area is None:
            missing.append(f"the conductor's area is not on the item{f' ({conductor_code})' if conductor_code else ''}")
        if dia is None:
            missing.append(f"the conduit's inside diameter is not on the item{f' ({row.get('conduit_code')})' if row.get('conduit_code') else ' (no conduit on the BOM)'}")
        limit = fill_limit_pct(n_in, d.conduit_fill_limit_pct)
        row["fill_limit_pct"] = limit
        if missing or limit is None or n_in <= 0:
            reason = "fill: " + "; ".join(missing or ["no fill limit band covers the conductor count"])
            notes.append("fill: not checked (" + reason[6:] + ")")
            not_checked.append(reason)
        else:
            row["fill_pct"] = conduit_fill_pct([area] * n_in, dia)
            checks["fill_ok"] = row["fill_pct"] <= limit + 1e-9
            notes.append(f"fill {row['fill_pct']:.1f} % = {n_in} × {area:g} mm² / (π/4 × {dia:g}²) against {limit:g} % for {n_in} conductors"
                         + (" (line, neutral and the grounding run in one raceway; each circuit in its own run by the rule's placement, verify the raceway)" if with_egc else "")
                         + f" ({cite(d.conduit_fill_source, d.conduit_fill_verified)})")
            if not checks["fill_ok"]:
                warnings.append({"code": "conduit_fill", "hard": True, "message": (
                    f"{label}: {n_in} × {area:g} mm² conductors fill {row['fill_pct']:.1f} % of the {dia:g} mm conduit, above the {limit:g} % limit for {n_in} conductors "
                    f"({cite(d.conduit_fill_source, d.conduit_fill_verified)}). Use a larger conduit (Pricing settings › BOM item roles).")})
    else:
        notes.append("fill: not applicable (free air)")

    # 6. the equipment grounding conductor by the breaker rating
    provided = row.get("egc_provided_mm2")
    if ocpd is not None:
        req = egc_required_mm2(float(ocpd), g.egc_by_ocpd)
        if req is None:
            not_checked.append(f"the EGC table stops below the {float(ocpd):g} A breaker (Pricing settings › Design analysis)")
        else:
            row["egc_required_mm2"] = req[1]
            notes.append(f"EGC required {req[1]:g} mm² for a breaker up to {req[0]:g} A ({cite(g.egc_source, g.egc_verified)})")
            if not g.egc_verified:
                qualifiers.append("EGC table: verify")
            if provided is not None:
                checks["egc_ok"] = float(provided) >= req[1] - 1e-9
                if not checks["egc_ok"]:
                    what = "the array bonding conductor" if kind == "dc_pv" else "the grounding run"
                    warnings.append({"code": "egc_undersized", "hard": True, "message": (
                        f"{label}: {what} is {float(provided):g} mm² and the {float(ocpd):g} A breaker needs {req[1]:g} mm² ({cite(g.egc_source, g.egc_verified)}). "
                        "Set a larger conductor for the role under Pricing settings › BOM item roles.")})
            elif kind == "dc_battery":
                # review finding 12: a blank "provided" is a missing BOM role, a real omission on site, not a table the app lacks
                not_checked.append("EGC: no battery-rack EGC role on the BOM (Pricing settings › BOM item roles)")
            else:
                not_checked.append("the EGC provided is not on the record (no item for the role)")
    elif kind != "dc_combined":
        notes.append("EGC required: not computed without the breaker's rating")

    # 7. the status: a failed check fails the row (the OCPD check passes by the next size up); a figure missing leaves it "not
    # checked"; else a pass, qualified by every assumption and every table still to verify (the sheet prints them beside it)
    failed = any(v is False for k, v in checks.items() if k not in ("ocpd_le_derated", "next_size_up_used")) or (checks["ocpd_le_derated"] is False and checks["next_size_up_used"] is not True)
    row["status"] = "fail" if failed else ("not checked" if not_checked else "pass")
    row["qualifiers"] = qualifiers
    row["not_checked"] = not_checked
    return {"warnings": warnings, "not_checked": not_checked, "qualifiers": qualifiers}


# ---------------------------------------------------------------- the short-circuit note (2.3)

def short_circuit_note(service: dict, inverter: Optional[Item], battery: Optional[Item], units: int, ac_current_a: Optional[float], breakers: list[Item], cfg: PricingConfig) -> dict:
    """Three lines and the breakers' interrupting ratings: the DU's available fault current from the service block the office
    types ("from the DU, verify" when blank), the inverter's contribution from its item (else the labelled 1.5 × assumption),
    the battery's from its item (else the BMS's trip, verify), and the AIC of each breaker item against the DU figure when
    both are typed."""
    d = cfg.derating
    du = str(service.get("du_name") or "").strip()
    utility = service.get("fault_level_ka")
    out: dict = {"utility_ka": float(utility) if utility is not None else None, "du_name": du or None, "inverter": None, "battery": None, "aic": [], "unknown": []}
    out["utility_text"] = (f"{float(utility):g} kA at the service, as the office typed from {du or 'the DU'} (verify)" if utility is not None
                           else f"BLANK kA (from {du or 'the DU'}; verify)")
    if utility is None:
        out["unknown"].append("the DU's available fault current at the service (Site step › Service entrance)")
    if inverter is not None:
        if inverter.fault_current_a:
            amps = float(inverter.fault_current_a) * max(units, 1)
            out["inverter"] = {"amps": amps, "assumed": False, "text": f"{amps:g} A ({inverter.code}: maximum output fault current on the item" + (f", × {units} units" if units > 1 else "") + ")"}
        elif ac_current_a:
            amps = float(d.inverter_fault_factor) * float(ac_current_a) * max(units, 1)
            out["inverter"] = {"amps": amps, "assumed": True, "text": (f"assumption: {float(d.inverter_fault_factor):g} × rated output current for one cycle, {amps:.0f} A"
                                                                        + (f" over {units} units" if units > 1 else "") + " — a grid-interactive inverter is current-limited; verify on the datasheet")}
            out["unknown"].append(f"the inverter's maximum output fault current ({inverter.code}, Materials page)")
    if battery is not None:
        if battery.fault_current_a:
            out["battery"] = {"amps": float(battery.fault_current_a), "assumed": False, "text": f"{float(battery.fault_current_a):g} A ({battery.code}: the BMS's short-circuit trip on the item)"}
        else:
            out["battery"] = {"amps": None, "assumed": False, "text": f"BLANK A (the BMS's short-circuit trip of {battery.code}: not on the item; verify with the maker)"}
            out["unknown"].append(f"the battery's short-circuit trip ({battery.code}, Materials page)")
    seen: set[str] = set()
    for b in breakers:
        if b is None or b.code in seen:
            continue
        seen.add(b.code)
        if b.aic_ka:
            ok = None if utility is None else float(b.aic_ka) >= float(utility) - 1e-9
            out["aic"].append({"code": b.code, "name": b.name, "aic_ka": float(b.aic_ka), "ok": ok})
        else:
            out["aic"].append({"code": b.code, "name": b.name, "aic_ka": None, "ok": None})
            out["unknown"].append(f"the interrupting rating of {b.code} (Materials page)")
    typed = [a for a in out["aic"] if a["aic_ka"] is not None]
    if not typed:
        out["aic_text"] = "breaker interrupting ratings (AIC) at or above the fault level at each point: BLANK — the AIC is not on the breaker items; verify"
    else:
        parts = []
        for a in out["aic"]:
            if a["aic_ka"] is None:
                parts.append(f"{a['code']} BLANK")
            else:
                parts.append(f"{a['code']} {a['aic_ka']:g} kA" + ("" if a["ok"] is None else (" at or above the DU's figure: holds" if a["ok"]
                                                                                                else " below the DU's figure: does NOT hold (aic_below_fault, holds the customer documents)")))
        out["aic_text"] = "breaker interrupting ratings (AIC) against the fault level at the service: " + "; ".join(parts) + ("; the DU's figure is blank, so nothing is compared" if utility is None else "") + " (verify)"
    return out


# ---------------------------------------------------------------- the job

def analyse_design(choices: dict, lines: list, catalog: Catalog, cfg: PricingConfig, *, inverter: Optional[Item], battery: Optional[Item], units: int,
                   tmy_max_air_c: Optional[float] = None, service: Optional[dict] = None) -> dict:
    """Derates every circuit record of `choices["circuits"]` in place, writes `choices["design_analysis"]` (the ambient, the
    assumptions, the tables with their sources and flags, the short-circuit note, the GEC line, the rows not checked) and
    returns the warnings for `pricing.warnings`."""
    w, d, g = cfg.wiring, cfg.derating, cfg.grounding
    by_role: dict[str, Any] = {}
    for l in lines:
        by_role.setdefault(l.role, l)

    def item_of(role: Optional[str]) -> Optional[Item]:
        l = by_role.get(role or "")
        return catalog.get(l.code) if l is not None else None

    rows: list[dict] = list(choices.get("circuits") or [])
    warnings: list[dict] = []
    not_checked: list[dict] = []
    qualifiers: dict[str, list[str]] = {}
    served: list[float] = []
    for row in rows:
        if row["kind"] == "egc":
            continue
        if not row.get("applies"):
            row["notes"][:] = [n for n in row["notes"] if n not in (NOT_YET_DERATED, NOT_YET_EGC)]
            row["qualifiers"], row["not_checked"] = [], []
            continue
        role = CONDUCTOR_ROLE.get(row["kind"])
        conductor = item_of(role) or (item_of("thhn") if role == "thhn_grid" else None)
        conduit = item_of("conduit") if str(row.get("placement") or "").endswith("_conduit") else None
        res = derate_circuit(row, cfg, conductor, conduit, tmy_max_air_c=tmy_max_air_c)
        warnings += res["warnings"]
        if res["not_checked"]:
            not_checked.append({"id": row["id"], "name": row["name"], "reasons": res["not_checked"]})
        qualifiers[row["id"]] = res["qualifiers"]
        if row["kind"] in ("ac_inverter_output", "ac_grid_feed", "ac_bypass") and row.get("egc_required_mm2") is not None:
            served.append(float(row["egc_required_mm2"]))
    for row in rows:
        if row["kind"] != "egc":
            continue
        if not row.get("applies"):
            row["notes"][:] = [n for n in row["notes"] if n not in (NOT_YET_DERATED, NOT_YET_EGC)]
            continue
        res = derate_circuit(row, cfg, None, None, egc_sizes_served=served)
        warnings += res["warnings"]
        if res["not_checked"]:
            not_checked.append({"id": row["id"], "name": row["name"], "reasons": res["not_checked"]})
        qualifiers[row["id"]] = res["qualifiers"]
    if not_checked:
        listed = "; ".join(f"{n['id']}: " + ", ".join(n["reasons"]) for n in not_checked)
        warnings.append({"code": "derating_not_checked", "message": (
            f"Design analysis: a figure is missing, so the row reads \"not checked\" on the plans — {listed}. Type the conductor's area and insulation and the "
            "conduit's inside diameter on the Materials page (the items the BOM uses) and the panel's Isc for the string breaker.")})

    # the short-circuit note and the grounding electrode conductor
    service = service or {}
    breakers = [b for b in (item_of("dc_breaker"), item_of("ac_breaker"), item_of("battery_breaker")) if b is not None]
    sc = short_circuit_note(service, inverter, battery, units, choices.get("ac_current_a"), breakers, cfg)
    # round 13 review, finding 1: a breaker whose typed interrupting rating is below the typed fault level cannot clear the
    # fault at the service; the comparison on the sheet is not enough, so it is hard and holds the customer documents
    for a in sc["aic"]:
        if a["ok"] is False:
            warnings.append({"code": "aic_below_fault", "hard": True, "blocks_documents": True, "message": (
                f"{a['code']}: interrupting rating {float(a['aic_ka']):g} kA is below the DU's {float(sc['utility_ka']):g} kA at the service: change the breaker role under "
                "Pricing settings › BOM item roles (verify the DU's figure). The proposal, roof check, card and plans are held.")})
    if sc["unknown"]:
        warnings.append({"code": "fault_level_unknown", "message": (
            "Design analysis, the short-circuit note: not on file — " + "; ".join(sc["unknown"]) + ". The sheet prints the figure as a blank line with "
            "\"verify\" and the labelled assumption for the inverter until they are typed.")})
    gnd_gauge = choices.get("ac_gauge")
    gec = {"gauge_mm2": float(gnd_gauge) if gnd_gauge else None, "max_mm2": float(g.gec_rod_max_mm2), "source": g.gec_source, "verified": bool(g.gec_verified),
           "rod_code": (by_role.get("ground_rod").code if by_role.get("ground_rod") is not None else None)}
    gec["text"] = (f"GEC: {gec['gauge_mm2']:g} mm² (the grounding run's gauge on the THHN line) to the rod" if gec["gauge_mm2"] else "GEC: BLANK (no grounding run on the BOM) to the rod") \
        + f"; required at most {gec['max_mm2']:g} mm² for a rod electrode ({cite(g.gec_source, g.gec_verified)})" \
        + (f"; the rod: {gec['rod_code']}" if gec["rod_code"] else "; no ground rod on the BOM")
    gec["ok"] = None if gec["gauge_mm2"] is None else True   # a rod's GEC need not exceed the maximum: a smaller run is never undersized by this rule alone

    # the tables used, with their sources and flags (printed on the sheet with "verify" until ticked)
    tables = [
        {"key": "wiring.thhn_ampacity", "label": "THHN ampacity columns (60, 75 and 90 °C)", "source": w.thhn_ampacity_source, "verified": bool(w.thhn_ampacity_verified),
         "values": {"60 °C": dict(w.thhn_ampacity), "75 °C": dict(w.thhn_ampacity_75c), "90 °C": dict(w.thhn_ampacity_90c)}},
        {"key": "wiring.pv_cable_ampacity", "label": "PV cable and battery cable tables (the base at 90 °C)", "source": "the wiring rules' tables; verify the cable's rating (the maker's figure on the item replaces it)", "verified": False,
         "values": {"PV cable": dict(w.pv_cable_ampacity), "battery cable": dict(w.battery_cable_ampacity)}},
        {"key": "derating.temperature_correction", "label": "Temperature correction", "source": d.temperature_correction_source, "verified": bool(d.temperature_correction_verified), "values": None},
        {"key": "derating.rooftop_adder_c", "label": "Rooftop adder bands", "source": d.rooftop_adder_source, "verified": bool(d.rooftop_adder_verified), "values": dict(d.rooftop_adder_c)},
        {"key": "derating.bundling_factor_pct", "label": "Bundling factors", "source": d.bundling_factor_source, "verified": bool(d.bundling_factor_verified), "values": dict(d.bundling_factor_pct)},
        {"key": "derating.conduit_fill_limit_pct", "label": "Conduit fill limits", "source": d.conduit_fill_source, "verified": bool(d.conduit_fill_verified), "values": dict(d.conduit_fill_limit_pct)},
        {"key": "derating.next_size_up", "label": "Next-size-up rule", "source": d.next_size_up_source, "verified": bool(d.next_size_up_verified), "values": {"up to": float(d.next_size_up_max_a)}},
        {"key": "derating.terminal_rule", "label": "Terminal rule", "source": d.terminal_rule_source, "verified": bool(d.terminal_rule_verified), "values": {"column": float(d.terminal_rating_c)}},
        {"key": "grounding.egc_by_ocpd", "label": "EGC by overcurrent device", "source": g.egc_source, "verified": bool(g.egc_verified), "values": dict(g.egc_by_ocpd)},
        {"key": "grounding.gec_rod_max_mm2", "label": "GEC to a rod electrode", "source": g.gec_source, "verified": bool(g.gec_verified), "values": {"maximum": float(g.gec_rod_max_mm2)}},
    ]
    outdoor = ambient_for("rooftop_free_air", cfg, tmy_max_air_c)
    assumptions = [
        f"outdoor ambient {outdoor['ambient_c']:g} °C: " + outdoor["basis"],
        f"indoor ambient {float(d.ambient_indoor_c):g} °C: the derating setting (an assumption)",
        f"a raceway on the roof sits {float(d.conduit_height_above_roof_mm):g} mm above it (a conduit on the rails; an assumption that picks the adder band); the string home runs are in free air under the array until the BOM carries a rooftop conduit",
        f"insulation {float(d.default_insulation_c):g} °C for a wire item without a rating on it (THHN and PV wire are 90 °C types; verify the items)",
    ]
    if sc.get("inverter") and sc["inverter"].get("assumed"):
        assumptions.append(f"the inverter's fault contribution {float(d.inverter_fault_factor):g} × its rated output current for one cycle (verify on the datasheet)")
    assumptions.append("each AC circuit runs line, neutral and the grounding run in its own raceway (the rule's placement until the survey records the run)")
    blocking = sorted({x["code"] for x in warnings if x.get("blocks_documents")})
    choices["design_analysis"] = {
        "ambient": {"outdoor_c": outdoor["ambient_c"], "outdoor_source": outdoor["source"], "outdoor_basis": outdoor["basis"], "indoor_c": float(d.ambient_indoor_c),
                    "tmy_max_air_c": None if tmy_max_air_c is None else float(tmy_max_air_c)},
        "assumptions": assumptions, "tables": tables, "short_circuit": sc, "gec": gec, "not_checked": not_checked, "qualifiers": qualifiers, "blocking": blocking,
        "statuses": {r["id"]: r["status"] for r in rows},
    }
    return {"warnings": warnings, "block": choices["design_analysis"]}
