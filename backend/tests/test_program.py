from datetime import date
from pathlib import Path

import pytest

from solarapp.pricing.boq import BoqRequest, generate_boq, rows_for
from solarapp.pricing.config import PaymentMilestone, PaymentPlan
from solarapp.pricing.engine import JobInputs, price_job
from solarapp.pricing.importer import read_workbook
from solarapp.pricing.program import _hhmm, build_program, day_windows, plan_install_days
from solarapp.schemas import AssessmentDoc

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"


@pytest.fixture(scope="module")
def priced():
    imp = read_workbook(WB)
    cat, cfg = imp.catalog, imp.config
    req = BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=9.9)
    boq = generate_boq(req, cat, cfg)
    pr = price_job(boq.lines, cat, cfg, JobInputs(extra_km=26.7, net_metering=True))
    from solarapp.pricing.engine import landed_cost
    cash = {}
    for l in boq.lines:
        it = cat.get(l.code)
        lc = landed_cost(it, cat, cfg)
        cash[it.supplier] = cash.get(it.supplier, 0.0) + (lc.net_price + lc.payment_fee) * l.qty
    pr["available"] = True
    pr["cash_by_supplier"] = cash
    return cfg, pr


def test_day_windows_default_site_day(priced):
    cfg, _ = priced
    doc = AssessmentDoc()
    windows, frame = day_windows(cfg, doc, 1, 0.0)
    assert frame["depart"] == "06:00" and frame["lunch_start"] == "12:00" and frame["lunch_end"] == "13:00"
    assert sum(w.end - w.start for w in windows) == 390  # 6.5 productive hours
    assert frame["work_end"] == "14:15" and frame["back_at_base"] == "15:00"
    doc.program.depart_time = "07:00"
    doc.program.lunch_minutes = 30
    w2, f2 = day_windows(cfg, doc, 1, 40.0)   # 40 extra km at 40 km/h = 1 h more travel each way
    assert f2["arrive"] == "08:15" and f2["lunch_end"] == "12:30" and sum(w.end - w.start for w in w2) == 390


def test_install_plan_parallel_streams(priced):
    cfg, pr = priced
    plan = plan_install_days(pr, cfg, AssessmentDoc())
    assert plan["days"] == 1 and plan["crew"]["persons"] == 4 and plan["crew"]["roof_pairs"] == 1
    roof = [s for s in plan["segments"] if s["stream"] == "roof"]
    ground = [s for s in plan["segments"] if s["stream"] == "ground"]
    assert roof[0]["task"].startswith("Set up rails") and ground[0]["task"].startswith("Unload")
    assert roof[0]["start_time"] == plan["frame"]["work_start"] == ground[0]["start_time"]  # both streams start when work starts
    assert plan["frame"]["work_start"] == "07:25"  # 26.7 extra km adds 40 min of travel each way
    energize = [s for s in ground if s["task"].startswith("Energize")]
    assert energize and energize[0]["start"] >= roof[-1]["end"]  # commissioning waits for the roof strings
    assert energize[-1]["end"] <= _hhmm(plan["frame"]["work_end"])
    assert any(w["code"] == "early_finish" for w in plan["warnings"])  # 15.9 man-hours for a crew of four
    assert not any(s["task"] == "Lunch" for s in plan["segments"])    # home before lunch on this small job
    hours = plan["hourly"][0]["rows"]
    assert hours[0]["time"] == "06:00" and hours[0]["roof"].startswith("Travel from base")
    assert any("Mount panels" in r["roof"] for r in hours) and any("Travel back" in r["ground"] for r in hours)
    assert all(r["roof"].count("→") <= 2 for r in hours)
    # the roof crew joins the ground tasks once the roof is done
    assert any(s["crew"] == 4 for s in ground)


def test_program_schedule_payments_and_cashflow(priced):
    cfg, pr = priced
    doc = AssessmentDoc()
    doc.program.signing_date = "2026-10-12"
    results = {"pricing": pr, "sizing": {"kind": "combination"}}
    prog = build_program(doc, results, cfg)
    assert prog["available"]
    ev = {e["key"]: e for e in prog["events"]}
    assert ev["signing"]["date"] == "2026-10-12"
    assert ev["permit_approved"]["date"] == "2026-10-21"          # 2 days prep + 7 days approval
    assert prog["install_start"] == "2026-10-22" and ev["sourcing"]["date"] == "2026-10-21"
    assert ev["commissioning"]["date"] == prog["install_end"] == "2026-10-22"
    assert ev["netmeter_application"]["date"] == "2026-10-13" and ev["meter_installed"]["date"] == "2026-11-27"  # agreement 12 Nov + 15 days
    assert prog["completion"] == "2026-11-27"
    contract = pr["totals"]["contract_rounded"]
    pays = prog["payments"]
    assert [round(p["share"], 2) for p in pays] == [0.5, 0.4, 0.1]
    assert abs(sum(p["amount"] for p in pays) - contract) < 0.01
    assert pays[1]["date"] == prog["install_start"] and pays[2]["date"] == ev["commissioning"]["date"]
    cf = prog["cashflow"]
    assert abs(cf["total_in"] - contract) < 0.01
    out = {o["key"]: o for o in prog["outflows"]}
    assert out["labour"]["date"] == prog["install_end"] and out["commission"]["amount"] == pytest.approx(pr["totals"]["commission"])
    assert out["commission"]["amount"] == pytest.approx(pr["totals"]["direct"] * 0.05)
    assert out["vat"]["amount"] == pytest.approx(pr["totals"]["vat"])
    supplier_cash = sum(o["amount"] for k, o in out.items() if k.startswith("supplier_"))
    assert supplier_cash == pytest.approx(sum(pr["cash_by_supplier"].values()))
    assert supplier_cash < pr["totals"]["materials_landed"]  # landed adds handling, wastage and storage
    assert cf["cash_margin"] == pytest.approx(cf["total_in"] - cf["total_out"])
    assert cf["cash_margin"] > pr["totals"]["op"]  # non-cash allocations stay in the company
    assert cf["lowest_balance"] < 0 and cf["lowest_balance_date"] == ev["sourcing"]["date"]  # the company carries part of the supplier cash until delivery
    assert cf["flows"][-1]["balance"] == pytest.approx(cf["cash_margin"])
    assert all(e["customer"] for e in prog["events"] if e["kind"] == "payment_in")
    assert not any("Pickup run" in c["label"] for c in prog["customer_schedule"])

    # instalments: 30% down, 20% on delivery, balance in 6 monthly instalments
    doc.program.payment = PaymentPlan(
        milestones=[PaymentMilestone(key="down", label="Down", share=0.3), PaymentMilestone(key="deliv", label="Delivery", share=0.2, event="materials_on_site")],
        installments=6, installment_share=0.5,
    ).model_dump()
    prog2 = build_program(doc, results, cfg)
    pays2 = prog2["payments"]
    assert len(pays2) == 8 and abs(sum(p["amount"] for p in pays2) - contract) < 0.01
    assert pays2[2]["date"] == "2026-11-21" and pays2[3]["date"] == "2026-12-21"
    assert prog2["cashflow"]["lowest_balance"] < 0  # the company carries the supplier cash
    # off-grid: no net metering steps
    prog3 = build_program(doc, {"pricing": pr, "sizing": {"kind": "off_grid"}}, cfg)
    assert "meter_installed" not in {e["key"] for e in prog3["events"]} and prog3["completion"] == "2026-10-27"


def test_two_day_job_hourly_plan(priced):
    cfg, _ = priced
    imp = read_workbook(WB)
    cat = imp.catalog
    req = BoqRequest("BC-PNL-001", 40, rows_for(40, 10, 1.134), inverter_kw=12, battery_kwh=10)
    boq = generate_boq(req, cat, cfg)
    pr = price_job(boq.lines, cat, cfg, JobInputs(net_metering=True, max_pairs=1, roof_closed_days=2))
    pr["available"] = True
    plan = plan_install_days(pr, cfg, AssessmentDoc())
    assert plan["days"] >= 2 and len(plan["hourly"]) == plan["days"]
    assert plan["segments"][-1]["day"] == plan["days"] - 1
    assert any(s["task"] == "Lunch" and s["day"] == 0 for s in plan["segments"])
    assert pr["labor"]["days"] == 2 and plan["days"] == 2
