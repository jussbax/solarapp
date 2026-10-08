"""Customer economics: bill before and after, savings, payback, NPV, IRR over the analysis period.

Built from the sizing's month-by-month balance (what solar serves directly, what the battery
serves, what is exported and imported) and the priced contract. The tariff is the effective
rate from the latest bill (amount over kWh) when there is one.
"""
from __future__ import annotations

from typing import Optional

from ..schemas import AssessmentDoc
from .config import PricingConfig


def _npv(rate: float, flows: list[float]) -> float:
    return sum(f / (1 + rate) ** i for i, f in enumerate(flows))


def _irr(flows: list[float]) -> Optional[float]:
    if not flows or flows[0] >= 0 or sum(flows) <= 0:
        return None
    lo, hi = -0.99, 10.0
    f_lo, f_hi = _npv(lo, flows), _npv(hi, flows)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = _npv(mid, flows)
        if abs(f_mid) < 1e-6:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def _payback(cumulative: list[float]) -> Optional[float]:
    """Years until the cumulative net turns positive, interpolated within the year; cumulative[0] is year 0."""
    for y in range(1, len(cumulative)):
        if cumulative[y] >= 0:
            prev, cur = cumulative[y - 1], cumulative[y]
            return (y - 1) + (-prev / (cur - prev) if cur != prev else 0.0)
    return None


def build_economics(doc: AssessmentDoc, results: dict, cfg: PricingConfig) -> dict:
    sizing = results.get("sizing")
    pricing = results.get("pricing") or {}
    if not sizing:
        return {"available": False, "reason": "Economics need the energy audit and sizing.", "warnings": []}
    if not pricing.get("available"):
        return {"available": False, "reason": "Economics need the priced job for the payback.", "warnings": []}
    e, j = cfg.economics, doc.economics
    warnings: list[dict] = []

    # tariff: the effective rate of the latest bill with an amount, else the setting
    tariff_source = "setting"
    tariff = e.tariff_php_per_kwh
    bills = [b for b in doc.audit.bills if b.kwh > 0 and b.amount_php]
    if bills:
        b = sorted(bills, key=lambda x: x.billing_month)[-1]
        tariff = b.amount_php / b.kwh
        tariff_source = f"bill {b.billing_month}"
    if j.tariff_php_per_kwh:
        tariff, tariff_source = j.tariff_php_per_kwh, "entered"
    export_rate = j.export_rate_php_per_kwh if j.export_rate_php_per_kwh is not None else e.export_rate_php_per_kwh
    esc = j.tariff_escalation if j.tariff_escalation is not None else e.tariff_escalation
    deg = j.degradation if j.degradation is not None else e.degradation
    years = j.analysis_years or e.analysis_years
    disc = j.discount_rate if j.discount_rate is not None else e.discount_rate
    bat_life = j.battery_life_years or e.battery_life_years
    inv_life = j.inverter_life_years or e.inverter_life_years
    contract = float(pricing["totals"]["contract_rounded"])
    om = j.om_per_year if j.om_per_year is not None else contract * e.om_share_per_year
    off_grid = sizing["kind"] == "off_grid"
    if off_grid:
        export_rate = 0.0

    # year-1 months from the sizing balance
    cust_items = {i["key"]: i for s in pricing["customer"]["sections"] for i in s.get("items", [])}
    battery_cost = float(cust_items["Battery"]["amount"]) if "Battery" in cust_items else 0.0
    inverter_cost = float(cust_items["Inverter"]["amount"]) if "Inverter" in cust_items else 0.0
    monthly = []
    for m in sizing["monthly"]:
        cons = float(m["consumption_kwh"])
        used = float(m["direct_kwh"]) + float(m["battery_kwh"])
        exp = 0.0 if off_grid else float(m["export_kwh"])
        imp = 0.0 if off_grid else float(m["import_kwh"])
        before = cons * tariff
        after = 0.0 if off_grid else max(imp * tariff - exp * export_rate, 0.0)
        monthly.append({
            "month": m["month"], "consumption_kwh": cons, "solar_used_kwh": used, "export_kwh": exp, "import_kwh": imp,
            "unserved_kwh": float(m.get("unserved_kwh", 0)), "bill_before": before, "bill_after": after, "savings": before - after,
        })
    # the bill the customer pays today versus the consumption the system is sized for (planned appliances included)
    audit = results.get("audit") or {}
    future_daily = float(audit.get("future_daily_kwh") or 0)
    includes_future = future_daily > 0
    if bills:
        bill_today = sum(b.amount_php for b in bills[-1:])
        bill_today_kwh = bills[-1].kwh
    else:
        existing_daily = audit.get("daily_kwh_by_month") or []
        bill_today_kwh = (sum(existing_daily) / len(existing_daily) * 30.4) if existing_daily else sum(x["consumption_kwh"] for x in monthly) / 12
        bill_today = bill_today_kwh * tariff
    y1_savings = sum(x["savings"] for x in monthly)
    y1_used = sum(x["solar_used_kwh"] for x in monthly)
    y1_export = sum(x["export_kwh"] for x in monthly)
    y1_import = sum(x["import_kwh"] for x in monthly)
    production_y1 = float(sizing["annual_production_kwh"])
    if y1_savings <= 0:
        warnings.append({"code": "no_savings", "message": "The sized system saves nothing on the bill; check the audit and tariff."})
    if not off_grid and any(x["import_kwh"] * tariff < x["export_kwh"] * export_rate for x in monthly):
        warnings.append({"code": "export_credit_capped", "message": "In some months the export credit is bigger than the bill. The extra credit is not carried over, so savings are slightly understated."})
    if off_grid and sum(x["unserved_kwh"] for x in monthly) > 0:
        warnings.append({"code": "unserved", "message": f"Off-grid: about {sum(x['unserved_kwh'] for x in monthly):,.0f} kWh a year would go unserved; savings count only the energy served."})

    # year series
    flows = [-contract]
    rows = []
    cum = -contract
    cum_rows = [cum]
    disc_cum = -contract
    lifetime_prod = 0.0
    for y in range(1, years + 1):
        f_deg = (1 - deg) ** (y - 1)
        f_esc = (1 + esc) ** (y - 1)
        savings = y1_savings * f_deg * f_esc
        costs = om * f_esc
        notes = []
        if battery_cost > 0 and bat_life < years and y % bat_life == 0 and y < years:
            costs += battery_cost
            notes.append("battery replacement")
        if inverter_cost > 0 and inv_life < years and y % inv_life == 0 and y < years:
            costs += inverter_cost
            notes.append("inverter replacement")
        net = savings - costs
        cum += net
        disc_cum += net / (1 + disc) ** y
        flows.append(net)
        cum_rows.append(cum)
        lifetime_prod += production_y1 * f_deg
        rows.append({"year": y, "production_kwh": production_y1 * f_deg, "savings": savings, "costs": costs, "net": net, "cumulative": cum, "discounted_cumulative": disc_cum, "note": ", ".join(notes)})
    npv = _npv(disc, flows)
    irr = _irr(flows)
    payback = _payback(cum_rows)
    disc_rows = [-contract] + [r["discounted_cumulative"] for r in rows]
    lifetime_savings = sum(r["savings"] for r in rows)
    lifetime_costs = contract + sum(r["costs"] for r in rows)
    return {
        "available": True,
        "warnings": warnings,
        "assumptions": {
            "tariff_php_per_kwh": tariff, "tariff_source": tariff_source, "export_rate_php_per_kwh": export_rate, "tariff_escalation": esc,
            "degradation": deg, "analysis_years": years, "discount_rate": disc, "battery_life_years": bat_life, "inverter_life_years": inv_life,
            "om_per_year": om, "battery_replacement_cost": battery_cost, "inverter_replacement_cost": inverter_cost, "co2_kg_per_kwh": e.co2_kg_per_kwh,
        },
        "contract": contract,
        "kind": sizing["kind"],
        "monthly": monthly,
        "bill_today_monthly": bill_today,
        "bill_today_kwh": bill_today_kwh,
        "includes_future_loads": includes_future,
        "bill_before_monthly": sum(x["bill_before"] for x in monthly) / 12,
        "bill_after_monthly": sum(x["bill_after"] for x in monthly) / 12,
        "savings_monthly": y1_savings / 12,
        "year1": {"savings": y1_savings, "solar_used_kwh": y1_used, "export_kwh": y1_export, "export_credit": y1_export * export_rate, "import_kwh": y1_import, "production_kwh": production_y1},
        "years": rows,
        "payback_years": payback,
        "discounted_payback_years": _payback(disc_rows),
        "npv": npv,
        "irr": irr,
        "lifetime_savings": lifetime_savings,
        "lifetime_costs": lifetime_costs,
        "lifetime_net": lifetime_savings - lifetime_costs,
        "lifetime_production_kwh": lifetime_prod,
        "lcoe_php_per_kwh": (lifetime_costs / lifetime_prod) if lifetime_prod > 0 else None,
        "co2_t_per_year": production_y1 * e.co2_kg_per_kwh / 1000.0,
    }
