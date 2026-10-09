"""Customer economics: bill before and after, savings, payback, NPV, IRR over the analysis period.

Built from the sizing's month-by-month balance (what solar serves directly, what the battery
serves, what is exported and imported) and the priced contract. The tariff is the effective
rate from the latest bill (amount over kWh) when there is one.
"""
from __future__ import annotations

import re
from typing import Optional

from ..profile import PROFILE_DEFAULTS
from ..schemas import AssessmentDoc
from .config import PricingConfig


def _years(text: object) -> Optional[int]:
    """A warranty field from the company profile ("5", "5 years", blank) as whole years, else None."""
    m = re.search(r"\d+", str(text or ""))
    return int(m.group()) if m and int(m.group()) > 0 else None


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


def build_economics(doc: AssessmentDoc, results: dict, cfg: PricingConfig, profile: Optional[dict] = None) -> dict:
    """`profile` is the company profile (Settings › Company): its battery warranty is the battery life unless overridden."""
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
    # export credit: the job's own figure, else the generation charge the assessor read off the latest bill (the DU credits
    # exported energy at its generation rate, not the retail rate), else the settings' figure
    export_rate, export_source = e.export_rate_php_per_kwh, "setting"
    gen_bills = [b for b in doc.audit.bills if b.generation_rate_php_per_kwh]
    if gen_bills:
        gb = sorted(gen_bills, key=lambda x: x.billing_month)[-1]
        export_rate, export_source = float(gb.generation_rate_php_per_kwh), f"bill {gb.billing_month}"
    if j.export_rate_php_per_kwh is not None:
        export_rate, export_source = j.export_rate_php_per_kwh, "entered"
    esc = j.tariff_escalation if j.tariff_escalation is not None else e.tariff_escalation
    deg = j.degradation if j.degradation is not None else e.degradation
    years = j.analysis_years or e.analysis_years
    disc = j.discount_rate if j.discount_rate is not None else e.discount_rate
    # Battery life: the job's own figure, else the settings override, else the battery warranty in the company
    # profile. The supplier notes say the datasheets give 5 years (the price list says 10 for one line), so the
    # warranty the owner stands behind is the honest replacement interval; the inverter life setting is a service
    # life, not its warranty.
    warranty = _years((profile or {}).get("warranty_battery_years"))
    if j.battery_life_years:
        bat_life, bat_life_source = j.battery_life_years, "entered"
    elif e.battery_life_years_override > 0:
        bat_life, bat_life_source = e.battery_life_years_override, "setting"
    elif warranty:
        bat_life, bat_life_source = warranty, "battery warranty"
    else:
        bat_life, bat_life_source = _years(PROFILE_DEFAULTS["warranty_battery_years"]) or 5, "assumed"
        warnings.append({"code": "battery_life_verify", "message": f"The battery warranty is blank in the company profile, so the savings view replaces the battery every {bat_life} years (verify). Fill in the warranty under Settings."})
    inv_life = j.inverter_life_years or e.inverter_life_years
    contract = float(pricing["totals"]["contract_rounded"])
    om = j.om_per_year if j.om_per_year is not None else contract * e.om_share_per_year
    off_grid = sizing["kind"] == "off_grid"
    if not off_grid and export_source == "setting":
        warnings.append({"code": "export_rate_default", "message": (
            f"The export credit uses the settings' figure of ₱{export_rate:.2f} per kWh. Type the generation charge from the customer's bill "
            "(Energy audit › Electricity bill) so the net metering credit is the electric company's own rate.")})
    if off_grid:
        export_rate = 0.0

    # year-1 months from the sizing balance
    cust_items = {i["key"]: i for s in pricing["customer"]["sections"] for i in s.get("items", [])}
    # Replacements cost the customer what the proposal's line costs today: the ex-VAT customer amount plus VAT, as
    # they will pay it, plus the replacement-labor setting (0 by default).
    vat = cfg.job.vat
    repl_labor = float(e.replacement_labor_php or 0)
    battery_cost = (float(cust_items["Battery"]["amount"]) * (1 + vat) + repl_labor) if "Battery" in cust_items else 0.0
    inverter_cost = (float(cust_items["Inverter"]["amount"]) * (1 + vat) + repl_labor) if "Inverter" in cust_items else 0.0
    monthly = []
    for m in sizing["monthly"]:
        cons = float(m["consumption_kwh"])
        used = float(m["direct_kwh"]) + float(m["battery_kwh"])
        exp = 0.0 if off_grid else float(m["export_kwh"])   # no export means no credit; the grid still bills what it supplies
        imp = float(m["import_kwh"])
        before = cons * tariff
        after = max(imp * tariff - exp * export_rate, 0.0)
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
    if off_grid and y1_import > 0:
        warnings.append({"code": "grid_backup", "message": f"No export: the grid supplies about {y1_import:,.0f} kWh a year when the panels and the battery fall short, billed at the tariff; surplus beyond the battery earns nothing."})

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
            "tariff_php_per_kwh": tariff, "tariff_source": tariff_source, "export_rate_php_per_kwh": export_rate, "export_rate_source": export_source, "tariff_escalation": esc,
            "degradation": deg, "analysis_years": years, "discount_rate": disc, "battery_life_years": bat_life, "battery_life_source": bat_life_source,
            "inverter_life_years": inv_life, "om_per_year": om, "battery_replacement_cost": battery_cost, "inverter_replacement_cost": inverter_cost,
            "replacement_labor_php": repl_labor, "replacement_vat": vat, "co2_kg_per_kwh": e.co2_kg_per_kwh,
            # the sizing's balance is at the meter (system losses applied), so savings and production here are too
            "loss_factor": float(sizing.get("loss_factor") or 1.0),
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
