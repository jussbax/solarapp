"""The schedule of loads in the permit's format (round 13, docs/audits/round-13/engineer-brief.md, item 5): the table a
sealed Philippine electrical plan carries per panelboard, filled from the energy audit's appliances grouped as the
format groups them (lighting, convenience outlets, equipment), the PV system as a source, and the point of
interconnection from the survey's service block.

Nothing invented: the watts are the audit's nameplates, the VA follow a power factor the settings hold and the sheet
labels "assumption", the volts are the surveyed service voltage or the wiring rules' with the assumption label; the
circuit numbers, wires, conduits and breakers of the existing panelboard are blank unless the office typed the
existing circuits on the Site step (printed verbatim, first); the demand factors, the demand load, the main breaker's
adequacy and "fed from" are the signing engineer's and print as blank lines with the reason. The column order is the
usual one and is flagged to verify against the LGU's sample.

`loads_sheet` is the one hook `plans_pdf.build_plans_pdf` calls: it returns the sheet's name and its flowables."""
from __future__ import annotations

from typing import Any, Optional
from xml.sax.saxutils import escape

from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from ..pricing.service_checks import INTERCONNECTION_LABEL, poi_busbar_check
from . import brand
from .plans_pdf import BLANK, _f, _g, _line, _lines_by_role
from .plans_sld import poi_lines

SHEET_NAME = "Schedule of loads"
COLUMNS = ["Circuit No.", "Description of load (count × type)", "Load (W)", "Load (VA)", "Volts", "Amperes", "Wire (mm² THHN)", "Conduit (mm)", "OCPD (AT/AF, poles)", "Remarks"]
COL_WIDTHS = [24, 86, 22, 24, 18, 22, 34, 26, 44, 62]        # mm, 362 of the frame's 392
VERIFY_COLUMNS = "the usual column order of a sealed plan's schedule of loads: verify against the LGU's sample (a past sealed plan)"
GROUPS = (("lighting", "Lighting"), ("outlets", "Convenience outlets"), ("equipment", "Equipment"))
ENGINEERS = "the engineer's, from the existing panelboard"


def _group_of(category: str, equipment: set[str]) -> str:
    if category == "lighting":
        return "lighting"
    return "equipment" if category in equipment else "outlets"


def load_groups(appliances: list[dict], loads_cfg: dict, volts: Optional[float]) -> dict:
    """The audit's appliances grouped and totalled: per group its lines (W, VA, A), the subtotal and the power factor
    used; the planned loads (status "future") apart and outside the existing total; retiring appliances left out.
    Every figure a number or None (a power factor missing from the settings leaves VA and A None)."""
    pf_map = loads_cfg.get("power_factor") or {}
    equipment = set(loads_cfg.get("equipment_categories") or [])
    groups: dict[str, dict] = {g: {"label": label, "pf": pf_map.get(g), "lines": [], "w": 0.0, "va": 0.0, "a": 0.0, "va_known": True} for g, label in GROUPS}
    planned: dict = {"label": "Planned loads", "pf": None, "lines": [], "w": 0.0, "va": 0.0, "a": 0.0, "va_known": True}
    retiring = 0
    for a in appliances:
        status = str(a.get("status") or "existing")
        if status == "retiring":
            retiring += 1
            continue
        g = _group_of(str(a.get("category") or "other"), equipment)
        qty = float(a.get("quantity") or 1)
        w_each = float(a.get("input_power_w") or 0)
        w = qty * w_each
        pf = pf_map.get(g)
        va = w / float(pf) if pf else None
        amps = va / float(volts) if (va is not None and volts) else None
        line = {"name": str(a.get("name") or ""), "qty": qty, "w_each": w_each, "w": w, "va": va, "a": amps, "group": g, "pf": pf, "status": status}
        target = planned if status == "future" else groups[g]
        target["lines"].append(line)
        target["w"] += w
        if va is None:
            target["va_known"] = False
        else:
            target["va"] += va
            target["a"] += amps or 0.0
    existing_w = sum(g["w"] for g in groups.values())
    va_known = all(g["va_known"] for g in groups.values()) and bool(volts)
    existing_va = sum(g["va"] for g in groups.values()) if va_known else None
    return {"groups": groups, "planned": planned, "retiring": retiring, "existing_w": existing_w, "existing_va": existing_va,
            "existing_a": existing_va / float(volts) if (existing_va is not None and volts) else None}


def loads_sheet(doc: Any, results: dict, items: dict[str, dict], cfg: dict, st: dict) -> tuple[str, list]:
    """The hook `plans_pdf` calls: (the sheet's name, its flowables)."""
    pricing = results.get("pricing") or {}
    sizing = results.get("sizing") or {}
    audit = results.get("audit") or {}
    choices = pricing.get("choices") or {}
    wiring = cfg.get("wiring") or {}
    loads_cfg = cfg.get("loads") or {}
    by_role = _lines_by_role(pricing)
    kind = str(sizing.get("kind") or choices.get("kind") or "")
    service = getattr(doc, "service", None)
    svc = service.model_dump() if hasattr(service, "model_dump") else dict(service or {})
    poi = choices.get("poi_busbar") or poi_busbar_check(svc, choices)[0]
    P = lambda t, style=None: Paragraph(t, style or st["cell"])  # noqa: E731
    cell, cellb = st["cell"], st["cellb"]

    # the voltage: the surveyed service voltage, else the wiring rules' with the assumption label
    volts = svc.get("voltage_v") or wiring.get("ac_voltage")
    volts_txt = _g(svc.get("voltage_v"), "V") if svc.get("voltage_v") else f"{_g(wiring.get('ac_voltage'), 'V')} (assumption)"
    phase = svc.get("phase")
    phase_txt = "1Ø 2W" if phase == 1 else f"3Ø, {BLANK} W (verify)" if phase == 3 else f"{BLANK} Ø (not surveyed)"
    apps = list(audit.get("appliances") or [])
    grouped = load_groups(apps, loads_cfg, float(volts) if volts else None)

    flows: list = [Paragraph(SHEET_NAME, st["h1"])]
    flows.append(Paragraph(f"The energy audit's appliances in the permit's table, grouped as the format groups them, with the PV system as a source and the point of interconnection; "
                           f"{escape(VERIFY_COLUMNS)}. Circuit numbers, wires, conduits and breakers of the existing panelboard are {ENGINEERS} unless typed on the Site step; "
                           "a blank line is a figure the app does not hold, with its reason.", st["body"]))
    head = (f"<b>Panelboard {escape(str(svc.get('panelboard') or BLANK))}</b>: {volts_txt}, {phase_txt}, main breaker {_g(svc.get('main_breaker_a'), 'AT') if svc.get('main_breaker_a') else BLANK + ' AT'} / {BLANK} AF "
            f"(the frame rating is not surveyed), bus {_g(svc.get('busbar_a'), 'A')}, fed from {BLANK} (the engineer's)")
    flows.append(Paragraph(head, st["body"]))

    rows: list[list] = []
    span_rows: list[int] = []           # the rows that are one cell across (group headings)

    def heading(text: str) -> None:
        span_rows.append(len(rows) + 1)
        rows.append([P(text, cellb)] + [""] * (len(COLUMNS) - 1))

    def app_row(ln: dict) -> list:
        return ["", P(f"{_g(ln['qty'])} × {escape(ln['name'])}, {_g(ln['w_each'], 'W')} each" if ln["qty"] != 1 else f"1 × {escape(ln['name'])}, {_g(ln['w_each'], 'W')}"),
                _f(ln["w"], 0), _f(ln["va"], 0), _g(volts), _f(ln["a"], 2), BLANK, BLANK, BLANK, "planned" if ln["status"] == "future" else "existing"]

    def subtotal(label: str, g: dict) -> list:
        return ["", P(f"{escape(label)} subtotal", cellb), P(_f(g["w"], 0), cellb), P(_f(g["va"], 0) if g["va_known"] and g["lines"] else BLANK, cellb), _g(volts),
                P(_f(g["a"], 2) if g["va_known"] and g["lines"] and volts else BLANK, cellb), "", "", "", ""]

    # the existing circuits as typed on the Site step, first and verbatim
    typed = list(svc.get("circuits") or [])
    if typed:
        heading("Existing circuits as typed on the Site step (the load figures are the engineer's)")
        for c in typed:
            ocpd = (f"{_g(c.get('breaker_a'))} AT / {BLANK} AF" if c.get("breaker_a") else BLANK) + (f", {_g(c.get('poles'))}P" if c.get("poles") else "")
            rows.append([escape(str(c.get("no") or BLANK)), P(escape(str(c.get("description") or BLANK))), BLANK, BLANK, _g(volts), BLANK,
                         _g(c.get("wire_mm2")) if c.get("wire_mm2") else BLANK, _g(c.get("conduit_mm")) if c.get("conduit_mm") else BLANK, ocpd, "existing, as typed"])
    # the audit's loads by group
    if apps and any(g["lines"] for g in grouped["groups"].values()):
        for key, label in GROUPS:
            g = grouped["groups"][key]
            if not g["lines"]:
                continue
            pf_txt = f"PF {float(g['pf']):.2f}, assumption (Settings › System design)" if g["pf"] else "PF not set in Settings: VA and A blank"
            heading(f"{label} ({pf_txt})")
            rows += [app_row(ln) for ln in g["lines"]]
            rows.append(subtotal(label, g))
        rows.append(["", P("Connected load, existing", cellb), P(_f(grouped["existing_w"], 0), cellb), P(_f(grouped["existing_va"], 0) if grouped["existing_va"] is not None else BLANK, cellb), _g(volts),
                     P(_f(grouped["existing_a"], 2) if grouped["existing_a"] is not None else BLANK, cellb), "", "", "", "the audit's nameplates × quantity"])
    else:
        heading("The energy audit has no appliances yet, so there is no schedule of loads to table.")
    planned = grouped["planned"]
    if planned["lines"]:
        heading("Planned loads (status \"future\" on the audit; not in the existing total)")
        rows += [app_row(ln) for ln in planned["lines"]]
        rows.append(subtotal("Planned", planned))
    peak = (sizing.get("inverter") or {}).get("peak_load_kw")
    rows.append(["", P("Demand load", cellb), BLANK, BLANK, "", BLANK, "", "", "", P(f"the demand factors of PEC 2.20 (verify) are the engineer's; the hourly profile's coincident peak is {_f(peak, 2, 'kW')} (the audit's own figure)")])
    rows.append(["", P("Main breaker", cellb), "", "", "", "", "", "", (_g(svc.get("main_breaker_a"), "AT") + f" / {BLANK} AF") if svc.get("main_breaker_a") else f"{BLANK} (not surveyed)",
                 P("its adequacy with the PV source: the engineer's")])
    if grouped["retiring"]:
        rows.append(["", P(f"{grouped['retiring']} retiring appliance{'s' if grouped['retiring'] > 1 else ''} on the audit not listed (to be removed)"), "", "", "", "", "", "", "", ""])
    data = [[P(c, cellb) for c in COLUMNS]] + [[c if isinstance(c, Paragraph) else P(str(c)) for c in r] for r in rows]
    t = Table(data, colWidths=[w * mm for w in COL_WIDTHS], hAlign="LEFT", repeatRows=1)
    style = list(st["grid"].getCommands())
    for r in span_rows:                                 # a group heading is one cell across, shaded like the header
        style.append(("SPAN", (0, r), (-1, r)))
        style.append(("BACKGROUND", (0, r), (-1, r), brand.OFF_WHITE))
    t.setStyle(TableStyle(style))
    flows.append(t)

    # the PV system as a source
    panel_l, inv_l, bat_l = _line(by_role, "panel"), _line(by_role, "inverter"), _line(by_role, "battery")
    inv_item = items.get(str((inv_l or {}).get("code") or "")) or {}
    bat_item = items.get(str((bat_l or {}).get("code") or "")) or {}
    conduit_l = _line(by_role, "conduit")
    kwp = float((pricing.get("totals") or {}).get("kwp") or sizing.get("kwp") or 0)
    strings, per = int(choices.get("strings") or 0), int(choices.get("panels_per_string") or 0)
    units = int(choices.get("inverter_units") or 1)
    inv_phase = f"{_g(inv_item.get('phase'))}Ø" if inv_item.get("phase") else "1Ø (the wiring rules')"
    pv_rows = [
        ("PV array", f"{int(sizing.get('panels') or 0)} × {_g((panel_l or {}).get('rating'), 'W')} = {kwp:.2f} kWp DC, {strings} string{'s' if strings != 1 else ''} of {per}"),
        ("Inverter", f"{units} × {_g((inv_l or {}).get('rating'), 'kW')} AC ({escape(str((inv_l or {}).get('code') or BLANK))}), {_f(choices.get('ac_current_a'), 1, 'A')} at {_g(wiring.get('ac_voltage'), 'V')}, {inv_phase}"),
        ("PV backfeed breaker", f"{_f(choices.get('ac_grid_breaker_a'), 0, 'A')} 2P (C5, {escape(str((_line(by_role, 'ac_breaker') or {}).get('code') or 'no item'))}); the inverter-output breaker {_f(choices.get('ac_breaker_a'), 0, 'A')} 2P (C4)"),
        ("Wire", f"{escape(str(choices.get('ac_grid_gauge') or BLANK))} mm² THHN, 2 conductors × {_g(choices.get('ac_run_m'), 'm')}; the ground on the grounding run (C7)"),
        ("Conduit", (f"{escape(str(conduit_l.get('name') or ''))} ({escape(str(conduit_l.get('code')))}), {_g(conduit_l.get('qty'), 'm')} allowance; its inside diameter is not on the item" if conduit_l and not str(conduit_l.get("code", "")).startswith("NO-ITEM-")
                     else "conduit: no item in the materials list")),
        ("Energy storage", "none (net metering)" if kind == "net_metering" else
         f"{_g(choices.get('battery_units') or (bat_l or {}).get('qty'))} × {_g((bat_l or {}).get('rating'), 'kWh')} = {_f(choices.get('battery_nominal_kwh'), 2, 'kWh')}, {_f(bat_item.get('nominal_v'), 1, 'V')}, "
         f"max discharge {_f(bat_item.get('continuous_a'), 0, 'A')} per unit; battery breaker {_f((choices.get('battery_circuit') or {}).get('breaker_a'), 0, 'A')} (C3)"),
        ("DC side", "the strings, the DC breakers and the SPDs are on the single-line diagram and the circuit schedule"),
    ]
    pv_t = Table([[P(k, cellb), P(v)] for k, v in pv_rows], colWidths=[40 * mm, 150 * mm], hAlign="LEFT")
    pv_t.setStyle(st["kv_style"])

    # the point of interconnection
    inter = str(svc.get("interconnection") or "")
    two_way = kind in ("net_metering", "combination")
    poi_rows = [
        ("Point of interconnection", (escape(INTERCONNECTION_LABEL.get(inter, inter)) if inter else "not chosen (Site step)") + (f"; {escape(str(svc['interconnection_note']))}" if svc.get("interconnection_note") else "")),
        ("Existing main breaker, busbar", f"{_g(svc.get('main_breaker_a'), 'A')}, {_g(svc.get('busbar_a'), 'A')}" + ("" if svc.get("main_breaker_a") and svc.get("busbar_a") else " (not surveyed)")),
        ("120 % rule", "; ".join(escape(x) for x in poi_lines(poi)) + f" ({escape(str(poi.get('source') or ''))})"),
        ("Meter", ("two-way meter: installed by the DU after the CFEI" if two_way else "existing meter; nothing exported") + f"; meter number {escape(str(svc.get('meter_no') or BLANK))}"),
        ("DU, account", f"{escape(str(svc.get('du_name') or BLANK))}, account {escape(str(svc.get('account_no') or BLANK))}; fault level at the service {_f(svc.get('fault_level_ka'), 1, 'kA') if svc.get('fault_level_ka') not in (None, '') else BLANK} (from the DU, verify)"),
    ]
    poi_t = Table([[P(k, cellb), P(v)] for k, v in poi_rows], colWidths=[44 * mm, 146 * mm], hAlign="LEFT")
    poi_t.setStyle(st["kv_style"])
    left = [Paragraph("The PV system as a source", st["h2"]), pv_t]
    right = [Paragraph("The point of interconnection", st["h2"]), poi_t]
    both = Table([[left, right]], colWidths=[196 * mm, 194 * mm], hAlign="LEFT")
    both.setStyle(st["two_col"])
    flows.append(both)
    flows.append(Spacer(1, 3))
    flows.append(Paragraph("Filled by the signing engineer: the circuit numbers and the branch-circuit split of the existing panelboard (unless typed on the Site step, in which case the typed rows print first), "
                           "the demand factors and the demand load, the main breaker's adequacy with the PV source, and the panel schedule's \"fed from\". "
                           "The power factors are assumptions from Settings › System design; the audit's watts are nameplates × quantity, not measured loads.", st["small"]))
    return SHEET_NAME, flows
