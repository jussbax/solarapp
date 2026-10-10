"""The checks on the service entrance as surveyed (round 13, docs/audits/round-13/engineer-brief.md, 1.3): the 120 %
busbar rule at the point of interconnection. A plain function the job pricing calls after the BOQ and the plan
sheets call again when they print the figures, so the warning and the sheet always agree; nothing here moves a
price or a BOM line.

The rule, for a backfeed breaker on the load side of the existing panelboard (the usual residential arrangement):

    grid-side breaker × inverter units + the panelboard's main breaker  ≤  1.2 × the busbar rating

NEC 705.12(B)(2)(3)(b); the PEC 2017 equivalent: verify (the clause is printed with "verify" on the sheets). A
failure is a hard warning that prints, never a block: the fix is a supply-side tap or a larger panel, the PEE's call.
A blank rating or another point of interconnection leaves the rule unchecked, and the block says why."""
from __future__ import annotations

from typing import Any, Optional

BUSBAR_FACTOR = 1.2
RULE_SOURCE = "NEC 705.12(B)(2)(3)(b); the PEC 2017 equivalent: verify"
INTERCONNECTION_LABEL = {
    "load_side_breaker": "a backfeed breaker on the load side of the existing panelboard",
    "supply_side_tap": "a supply-side tap between the meter and the main breaker",
    "line_side_of_main": "the line side of the main breaker",
}


def _get(obj: Any, key: str) -> Any:
    """A field of the service block whether it comes as the pydantic model or as its dict."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _num(v: Any) -> Optional[float]:
    try:
        return None if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return None


def poi_busbar_check(service: Any, choices: dict) -> tuple[dict, list[dict]]:
    """The block the sheets print and the warnings the job collects. `service` is `AssessmentDoc.service` (or its dict);
    `choices` the BOQ's (`ac_grid_breaker_a`, `inverter_units`). The block carries every figure of the inequality, so a
    sheet prints the arithmetic rather than a verdict alone:

        {"interconnection", "kind", "checked", "reason", "grid_breaker_a", "units", "backfeed_a", "main_breaker_a", "busbar_a",
         "factor", "limit_a", "sum_a", "ok", "source"}

    `kind` is the job's (`choices["kind"]`): on a no-export job the sheets say the rule is applied conservatively (review finding 10)."""
    inter = str(_get(service, "interconnection") or "")
    main_a, bus_a = _num(_get(service, "main_breaker_a")), _num(_get(service, "busbar_a"))
    grid_a = _num((choices or {}).get("ac_grid_breaker_a"))
    units = max(int((choices or {}).get("inverter_units") or 1), 1)
    block: dict = {
        "interconnection": inter, "kind": str((choices or {}).get("kind") or ""), "checked": False, "reason": None,
        "grid_breaker_a": grid_a, "units": units, "backfeed_a": grid_a * units if grid_a is not None else None,
        "main_breaker_a": main_a, "busbar_a": bus_a, "factor": BUSBAR_FACTOR,
        "limit_a": bus_a * BUSBAR_FACTOR if bus_a is not None else None, "sum_a": None, "ok": None, "source": RULE_SOURCE,
    }
    # the reason is the cause alone; the sheets print it after "120 % rule: not checked —"
    if inter == "":
        block["reason"] = "the point of interconnection is not chosen (Site step)"
        return block, []
    if inter != "load_side_breaker":
        block["reason"] = f"the rule applies to a load-side breaker; this job connects at {INTERCONNECTION_LABEL.get(inter, inter)} (verify the DU's rule for it)"
        return block, []
    if main_a is None or bus_a is None:
        block["reason"] = "busbar and main breaker not surveyed"
        return block, []
    if grid_a is None:
        block["reason"] = "no grid-side breaker was sized (the hard ac_circuit warning)"
        return block, []
    block["checked"] = True
    block["sum_a"] = grid_a * units + main_a
    block["ok"] = block["sum_a"] <= block["limit_a"] + 1e-9
    warnings: list[dict] = []
    if not block["ok"]:
        warnings.append({"code": "poi_busbar", "hard": True, "message": (
            f"Point of interconnection: the {grid_a:g} A backfeed breaker{' × ' + str(units) if units > 1 else ''} plus the {main_a:g} A main breaker is "
            f"{block['sum_a']:g} A, above {BUSBAR_FACTOR:g} × the {bus_a:g} A busbar ({block['limit_a']:g} A): the 120 % rule fails ({RULE_SOURCE}). "
            "A supply-side tap or a larger panelboard is the signing engineer's call; the plans print FAIL beside the point of interconnection.")})
    return block, warnings
