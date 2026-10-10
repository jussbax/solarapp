"""The checks the datasheet figures unlock (round 12, docs/audits/round-12/engineer-brief.md, section 3): plain
functions the BOQ generator calls, each falling back to today's behaviour when a figure is absent. Every rule
carries its source as the brief gives it; every default is an assumption and says so in its warning.

The order the brief builds them in: 3.5 the battery circuit on the sheet's figures, 3.7 the voltage match, 3.6 the
charge check, 3.8 Ah-to-kWh, then 3.1 to 3.4 (strings from the cold Voc, the string current from Imp, the PV
conductor and the DC breaker from Isc with the 1.25 and 1.56 factors, parallel strings per MPPT).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .catalog import Item
from .config import PricingConfig, StringDesign


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


def _label(item: Optional[Item]) -> str:
    return f"{item.code} {item.name}" if item else "the inverter"


# ---------------------------------------------------------------- 3.5 the battery circuit

def inverter_battery_current(inverter: Optional[Item], inv_kw: float, battery_voltage: float) -> dict:
    """I_inv = max(the inverter's battery_max_a, its charge_a_max): the same conductor carries both directions, and on
    the Felicity 1P hybrids the charge column is the larger (3.5). Without either figure, the rated output over the
    battery voltage, as before."""
    figs = {k: float(getattr(inverter, k)) for k in ("battery_max_a", "charge_a_max") if inverter is not None and getattr(inverter, k, None)}
    if figs:
        amps = max(figs.values())
        both = len(figs) == 2
        return {"amps": amps, "source": "datasheet" if both else "item",
                "basis": (f"the larger of discharge {figs['battery_max_a']:g} A and charge {figs['charge_a_max']:g} A" if both
                          else f"the inverter's {'discharge' if 'battery_max_a' in figs else 'charge'} figure {amps:g} A")}
    return {"amps": inv_kw * 1000.0 / battery_voltage, "source": "rule", "basis": f"{inv_kw:g} kW over {battery_voltage:g} V (no battery current on the item)"}


def battery_soft_checks(battery: Item, units: int, inverter: Optional[Item], inverter_units: int, i_inv: float) -> list[dict]:
    """The ordinary checks beside the hard bank check: the recommended continuous rate (3.5), two battery inputs on the
    inverter (3.5), the inverter's charge current against what the bank accepts (3.6), and Ah against kWh (3.8)."""
    warnings: list[dict] = []
    need = i_inv * max(inverter_units, 1)
    rec = float(battery.discharge_a_recommended) if battery.discharge_a_recommended else None
    cont = float(battery.continuous_a) if battery.continuous_a else None
    if rec is not None and units > 0 and units * rec < need - 1e-9 and (cont is None or units * cont >= need - 1e-9):
        warnings.append({"code": "battery_discharge_recommended", "message": (
            f"{units} × {battery.code} deliver {units * rec:g} A at the recommended continuous rate and the inverter draws up to {need:.0f} A: "
            + (f"within the BMS maximum ({units * cont:g} A) but " if cont is not None else "")
            + "above the recommended rate; the battery runs warm at full power. Verify the warranty condition with the maker.")})
    if inverter is not None and (inverter.battery_inputs or 1) >= 2:
        each = f" ({float(inverter.battery_max_a):g} A each)" if inverter.battery_max_a else ""   # the page lets the owner set two inputs with no figure
        warnings.append({"code": "battery_inputs_verify", "message": (
            f"{_label(inverter)} has two battery inputs on the datasheet{each}; the second circuit is not priced; verify.")})
    charge = charge_check(inverter, battery, units)
    if charge and charge.get("ok") is False:
        warnings.append({"code": "battery_charge_current", "message": (
            f"The inverter can charge at {charge['inverter_a']:g} A and the bank accepts {charge['accept_a']:g} A ({units} × {charge['per_unit_a']:g} A): set the inverter's "
            f"maximum charge current to {charge['accept_a']:g} A, or the BMS limits or trips. Units needed for the full rate: {charge['units_for_full_rate']}.")})
    ah = ah_kwh_check(battery)
    if ah and ah.get("ok") is False:
        warnings.append({"code": "battery_ah_kwh", "message": (
            f"{battery.code}: {ah['nominal_v']:g} V × {ah['capacity_ah']:g} Ah = {ah['kwh_calc']:.2f} kWh against the {ah['rating_kwh']:g} kWh on file "
            f"({ah['deviation_pct']:.1f} %): one of the three figures is wrong; verify.")})
    return warnings


# ---------------------------------------------------------------- 3.6 the charge check

def charge_check(inverter: Optional[Item], battery: Optional[Item], units: int) -> Optional[dict]:
    """accept = units × the battery's charge_a_max; the inverter's charge_a_max above it is an ordinary warning: the
    charge current is an inverter setting (the commissioning report should print the value to set)."""
    if inverter is None or battery is None or not inverter.charge_a_max or not battery.charge_a_max or units <= 0:
        return None
    inv, per = float(inverter.charge_a_max), float(battery.charge_a_max)
    accept = units * per
    return {"inverter_a": inv, "per_unit_a": per, "units": units, "accept_a": accept, "ok": inv <= accept + 1e-9,
            "units_for_full_rate": int(math.ceil(inv / per - 1e-9))}


# ---------------------------------------------------------------- 3.7 the voltage match

def voltage_class(v: Optional[float]):
    """12 if V ≤ 16, 24 if ≤ 32, 48 if ≤ 64, else HV; applied to a nominal voltage and to a charge ceiling alike."""
    if v is None:
        return None
    v = float(v)
    return 12 if v <= 16 else 24 if v <= 32 else 48 if v <= 64 else "HV"


def voltage_match(inverter: Optional[Item], battery: Optional[Item]) -> tuple[Optional[dict], list[dict]]:
    """V1: the battery's nominal class is the inverter port's (from its max charge voltage), and the two battery
    classes agree when both are on file: else a hard warning that holds the documents (a wrong purchase, a unit that
    will not start). V2: the inverter charges no higher than the battery's ceiling: else an ordinary warning to set
    the charge voltage (a closed-loop BMS connection normally does; verify)."""
    if inverter is None or battery is None:
        return None, []
    bat_class, inv_class = voltage_class(battery.nominal_v), voltage_class(inverter.charge_v_max)
    bat_text, inv_text = (battery.battery_class or "").upper(), (inverter.battery_class or "").upper()
    block = {"battery_nominal_v": battery.nominal_v, "battery_class": bat_class, "battery_class_text": bat_text or None,
             "inverter_charge_v_max": inverter.charge_v_max, "inverter_class": inv_class, "inverter_class_text": inv_text or None,
             "battery_ceiling_v": battery.charge_v_max, "class_ok": None, "ceiling_ok": None}
    warnings: list[dict] = []
    checked = False
    ok = True
    if bat_class is not None and inv_class is not None:
        checked = True
        ok = ok and bat_class == inv_class
    if bat_text in ("LV", "HV") and inv_text in ("LV", "HV"):
        checked = True
        ok = ok and bat_text == inv_text
    if checked:
        block["class_ok"] = ok
        if not ok:
            warnings.append({"code": "battery_voltage_class", "hard": True, "blocks_documents": True, "message": (
                f"{battery.code} is a {('%s V' % bat_class) if bat_class != 'HV' else 'high-voltage'} pack"
                + (f" ({bat_text})" if bat_text else "")
                + f" and the battery port of {_label(inverter)} is a {('%s V' % inv_class) if inv_class != 'HV' else 'high-voltage'} port"
                + (f" ({inv_text})" if inv_text else "")
                + f" (it charges to {inverter.charge_v_max:g} V): a wrong purchase and a unit that will not start. Pick a battery of the port's class under Pricing inputs › Battery. "
                "The proposal, roof check, card and plans are held until this is fixed.")})
    if inverter.charge_v_max and battery.charge_v_max:
        block["ceiling_ok"] = float(inverter.charge_v_max) <= float(battery.charge_v_max) + 1e-9
        if not block["ceiling_ok"]:
            warnings.append({"code": "battery_charge_voltage", "message": (
                f"{_label(inverter)} charges to {inverter.charge_v_max:g} V and the ceiling of {battery.code} is {battery.charge_v_max:g} V: set the charge voltage to "
                f"{battery.charge_v_max:g} V or lower (a closed-loop BMS connection normally does this; verify).")})
    return block, warnings


# ---------------------------------------------------------------- 3.8 Ah against kWh

def ah_kwh_check(battery: Optional[Item]) -> Optional[dict]:
    """kWh_calc = nominal_v × capacity_ah / 1000 against the item's kWh rating; more than 2 % apart is an ordinary
    warning on a job that prices the unit (the import raised the same notice). Without a voltage it is skipped."""
    if battery is None or not battery.nominal_v or not battery.capacity_ah or not battery.rating or (battery.rating_unit or "").lower() != "kwh":
        return None
    calc = float(battery.nominal_v) * float(battery.capacity_ah) / 1000.0
    dev = abs(calc - float(battery.rating)) / float(battery.rating) * 100.0
    return {"nominal_v": float(battery.nominal_v), "capacity_ah": float(battery.capacity_ah), "kwh_calc": calc, "rating_kwh": float(battery.rating),
            "deviation_pct": dev, "ok": dev <= 2.0}


# ---------------------------------------------------------------- 3.1 strings from the cold Voc

@dataclass
class Coefficient:
    value: float
    default: bool


def coefficients(panel: Item, sd: StringDesign) -> dict[str, Coefficient]:
    """The panel's own temperature coefficients, else the settings' defaults flagged as such. No item field holds a
    Pmax coefficient yet (brief 6.5), so the Vmp term is always the default until the owner's sheet carries one."""
    return {
        "voc": Coefficient(float(panel.temp_coeff_voc_pct), False) if panel.temp_coeff_voc_pct is not None else Coefficient(float(sd.temp_coeff_voc_default_pct), True),
        "pmax": Coefficient(float(sd.temp_coeff_pmax_default_pct), True),
        "isc": Coefficient(float(panel.temp_coeff_isc_pct), False) if panel.temp_coeff_isc_pct is not None else Coefficient(float(sd.temp_coeff_isc_default_pct), True),
    }


@dataclass
class StringPlan:
    available: bool
    reason: str = ""
    t_cold_c: float = 0.0
    t_hot_c: float = 0.0
    voc_v: Optional[float] = None
    vmp_v: Optional[float] = None
    voc_cold_v: Optional[float] = None
    vmp_cold_v: Optional[float] = None
    vmp_hot_v: Optional[float] = None
    v_limit_v: Optional[float] = None
    limit_source: str = ""              # inverter or panel: which of the two maxima binds
    inverter_max_pv_v: Optional[float] = None
    panel_max_system_v: Optional[float] = None
    mppt_min_v: Optional[float] = None
    mppt_max_v: Optional[float] = None
    n_max: Optional[int] = None
    n_max_voltage: Optional[int] = None  # floor(V_limit / Voc_cold)
    n_max_window: Optional[int] = None   # floor(mppt_max_v / Vmp_cold) when the window is on file
    n_min: int = 1
    owner_cap: int = 0
    per_string_cap: int = 0
    strings: int = 0
    per_string: int = 0
    forced: bool = False
    coefficients: dict = field(default_factory=dict)
    warnings: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k not in ("warnings", "coefficients")}
        d["coefficients"] = {k: {"value": c.value, "default": c.default} for k, c in self.coefficients.items()}
        return d


def string_plan(panel: Item, inverter: Optional[Item], sd: StringDesign, t_cold: float, t_hot: float, panel_count: int,
                strings_override: Optional[int], owner_cap: int) -> StringPlan:
    """IEC 60891's linear temperature term, which IEC 62548 applies to array design (verify the editions):
        Voc_cold = Voc × (1 + β_Voc/100 × (T_cold − 25)); Vmp_cold and Vmp_hot likewise with β_Pmax
        V_limit = min(inverter max_pv_voltage_v, panel max_system_voltage_v)
        n_max = floor(V_limit / Voc_cold), also floor(mppt_max_v / Vmp_cold) when the window is on file
        n_min = ceil(mppt_min_v / Vmp_hot) when the window is on file, else 1
        per_string_cap = min(n_max, the owner's max_panels_per_string); strings = override or ceil(panels / cap)
    STC Voc is the base (the conservative side); the irradiance term of IEC 60891 is dropped (assumption). Without
    Voc on the panel or a maximum PV voltage on the inverter the fixed rule stands, said by string_rule_fallback."""
    plan = StringPlan(available=False, t_cold_c=t_cold, t_hot_c=t_hot, owner_cap=owner_cap, voc_v=panel.voc_v, vmp_v=panel.vmp_v,
                      inverter_max_pv_v=inverter.max_pv_voltage_v if inverter else None, panel_max_system_v=panel.max_system_voltage_v,
                      mppt_min_v=inverter.mppt_min_v if inverter else None, mppt_max_v=inverter.mppt_max_v if inverter else None)
    missing = []
    if not panel.voc_v:
        missing.append(f"{panel.code} has no Voc on file")
    if inverter is None or not inverter.max_pv_voltage_v:
        missing.append(f"{_label(inverter)} has no maximum PV voltage on file")
    cap = max(int(owner_cap), 1)
    if missing:
        plan.reason = " and ".join(missing)
        plan.per_string_cap = cap
        plan.strings = max(strings_override or int(math.ceil(panel_count / cap - 1e-9)), 1)
        plan.per_string = int(math.ceil(panel_count / plan.strings))
        plan.forced = bool(strings_override)
        plan.warnings.append({"code": "string_rule_fallback", "message": (
            f"{plan.reason}: the strings follow the fixed rule of {cap} per string. Type the datasheet figures (Materials page) before the plans are sealed.")})
        return plan
    assert inverter is not None
    co = coefficients(panel, sd)
    plan.coefficients = co
    voc = float(panel.voc_v)
    plan.voc_cold_v = voc * (1.0 + co["voc"].value / 100.0 * (t_cold - 25.0))
    if panel.vmp_v:
        vmp = float(panel.vmp_v)
        plan.vmp_cold_v = vmp * (1.0 + co["pmax"].value / 100.0 * (t_cold - 25.0))
        plan.vmp_hot_v = vmp * (1.0 + co["pmax"].value / 100.0 * (t_hot - 25.0))
    inv_max = float(inverter.max_pv_voltage_v)
    if panel.max_system_voltage_v and float(panel.max_system_voltage_v) < inv_max:
        plan.v_limit_v, plan.limit_source = float(panel.max_system_voltage_v), "panel"
    else:
        plan.v_limit_v, plan.limit_source = inv_max, "inverter"
    plan.n_max_voltage = int(math.floor(plan.v_limit_v / plan.voc_cold_v + 1e-9))
    n_max = plan.n_max_voltage
    if inverter.mppt_max_v and plan.vmp_cold_v:
        plan.n_max_window = int(math.floor(float(inverter.mppt_max_v) / plan.vmp_cold_v + 1e-9))
        n_max = min(n_max, plan.n_max_window)
    plan.n_max = max(n_max, 1)
    if inverter.mppt_min_v and plan.vmp_hot_v:
        plan.n_min = max(int(math.ceil(float(inverter.mppt_min_v) / plan.vmp_hot_v - 1e-9)), 1)
    plan.per_string_cap = max(min(plan.n_max, cap), 1)
    plan.strings = max(strings_override or int(math.ceil(panel_count / plan.per_string_cap - 1e-9)), 1)
    plan.per_string = int(math.ceil(panel_count / plan.strings))
    plan.forced = bool(strings_override)
    plan.available = True
    default_txt = ", a default" if co["voc"].default else ""
    if plan.per_string > plan.n_max:
        v = plan.per_string * plan.voc_cold_v
        over = (f"above the inverter's {inv_max:g} V maximum PV voltage" if plan.limit_source == "inverter"
                else f"above the panel's {plan.v_limit_v:g} V system voltage (the inverter takes {inv_max:g} V)")
        plan.warnings.append({"code": "string_voltage_cold", "hard": True, "blocks_documents": True, "message": (
            f"A string of {plan.per_string} × {panel.code} reaches {v:.1f} V at {t_cold:g} °C (Voc {voc:g} V, coefficient {co['voc'].value:g} %/°C{default_txt}), {over}. "
            f"The generator uses {plan.n_max} per string; this job forces {plan.per_string} (strings override or panels per string). "
            "The proposal, roof check, card and plans are held.")})
    if plan.per_string < plan.n_min and plan.vmp_hot_v:
        plan.warnings.append({"code": "string_voltage_hot", "message": (
            f"{plan.per_string} panels per string give {plan.per_string * plan.vmp_hot_v:.1f} V at {t_hot:g} °C, below the MPPT window's low end {float(inverter.mppt_min_v):g} V: "
            f"the inverter stops tracking on hot afternoons. Use at least {plan.n_min} per string or another inverter.")})
    if co["voc"].default:
        plan.warnings.append({"code": "temp_coeff_default", "message": (
            f"The string design used the default temperature coefficient {co['voc'].value:g} %/°C for Voc ({panel.code} has none on file; an assumption). "
            "Type the datasheet's figure on the Materials page before the plans are sealed.")})
    return plan


# ---------------------------------------------------------------- 3.2 the string current, the PV conductor and the DC breaker

def next_size(amps: float, sizes: list[float]) -> Optional[float]:
    for s in sorted(float(x) for x in sizes):
        if s >= amps - 1e-9:
            return s
    return None


def string_current(panel: Item, per_string: int, cfg: PricingConfig, t_hot: float) -> dict:
    """I_string = Imp (replaces panel watts over the wiring rules' Vmp); V_string = per_string × Vmp; I_design =
    Isc × the PV-circuit factor (1.25, the PEC PV article's circuit current, verify); I_cond = I_design × the
    continuous factor (1.25) = 1.5625 × Isc, the conductor's ampacity before derating and the breaker's minimum;
    the OCPD the next standard DC size at or above it. The temperature term on Isc is informational only: the code
    method is irradiance × continuous, and stacking would double-count (3.2, 3.3)."""
    w, sd = cfg.wiring, cfg.string_design
    panel_w = float(panel.rating or 0) if (panel.rating_unit or "").upper() == "W" else 0.0
    out: dict = {"source": "rule", "imp_a": panel.imp_a, "vmp_v": panel.vmp_v, "isc_a": panel.isc_a, "isc_factor": float(sd.isc_irradiance_factor),
                 "continuous_factor": float(w.continuous_factor), "i_design_a": None, "i_cond_a": None, "ocpd_a": None, "isc_hot_a": None, "isc_coeff_pct": None}
    out["i_string_a"] = float(panel.imp_a) if panel.imp_a else (panel_w / w.panel_vmp_v if panel_w else 0.0)
    out["v_string_v"] = per_string * (float(panel.vmp_v) if panel.vmp_v else w.panel_vmp_v)
    out["current_source"] = "datasheet" if panel.imp_a else "rule"
    out["voltage_source"] = "datasheet" if panel.vmp_v else "rule"
    if panel.isc_a:
        isc = float(panel.isc_a)
        out["i_design_a"] = isc * float(sd.isc_irradiance_factor)
        out["i_cond_a"] = out["i_design_a"] * float(w.continuous_factor)
        out["ocpd_a"] = next_size(out["i_cond_a"], sd.dc_breaker_sizes_a)
        alpha = float(panel.temp_coeff_isc_pct) if panel.temp_coeff_isc_pct is not None else float(sd.temp_coeff_isc_default_pct)
        out["isc_hot_a"] = isc * (1.0 + alpha / 100.0 * (t_hot - 25.0))
        out["isc_coeff_pct"] = alpha
        out["isc_coeff_default"] = panel.temp_coeff_isc_pct is None
        out["source"] = "datasheet"
    return out


# ---------------------------------------------------------------- 3.4 parallel strings per MPPT

def mppt_inputs(inverter: Optional[Item]) -> list[float]:
    """The inverter's inputs by current rating: the per-input figures when the sheet gave them ("18/36/36"), else the
    single maximum repeated over the MPPT count; empty when neither is on file."""
    if inverter is None:
        return []
    text = (inverter.mppt_currents_a or "").strip()
    if text:
        try:
            return [float(x) for x in text.split("/") if x.strip()]
        except ValueError:
            pass
    if inverter.mppt_count and inverter.mppt_max_a:
        return [float(inverter.mppt_max_a)] * int(inverter.mppt_count)
    return []


def mppt_assignment(inverter: Optional[Item], strings: int, per_string: int, panel_count: int, imp: Optional[float], units: int = 1) -> tuple[list[dict], list[dict]]:
    """Inputs sorted by their current rating, largest first; strings go one per input, then the extra strings double up
    on the largest inputs. For each input with p strings: p × Imp ≤ I_input, else the ordinary warning mppt_current.
    Strings in parallel on one input must be the same length; a strings override that leaves one string short adds
    the mismatch sentence. The input's short-circuit rating is on no sheet, so the warning says to verify it."""
    per_unit = mppt_inputs(inverter)
    if not per_unit or strings <= 0 or not imp:
        return [], []
    inputs = sorted(per_unit * max(units, 1), reverse=True)
    counts = [0] * len(inputs)
    for k in range(strings):
        counts[k % len(inputs)] += 1
    short = panel_count - per_string * (strings - 1) if strings > 1 else per_string   # the last string's length when the count does not divide
    per_mppt: list[dict] = []
    warnings: list[dict] = []
    for k, (limit, p) in enumerate(zip(inputs, counts), start=1):
        amps = p * float(imp)
        ok = amps <= limit + 1e-9
        per_mppt.append({"input": k, "limit_a": limit, "strings": p, "amps_at_imp": amps, "ok": ok if p else None})
        if p and not ok:
            msg = (f"{p} strings in parallel on MPPT {k} draw {amps:.2f} A at Imp, above the input's {limit:g} A: the inverter clips or the input overheats. "
                   "Use more inputs, fewer panels per input or another unit; verify the input's short-circuit rating (not on the sheet).")
            if p > 1 and short != per_string:
                msg += " Unequal strings on one input mismatch at Vmp."
            warnings.append({"code": "mppt_current", "message": msg})
    return per_mppt, warnings
