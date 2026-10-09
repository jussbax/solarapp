"""The customer's story on the documents (round 3, marketing batch): the proposal's "In short" block, the battery
sentence from the hourly balance, the corrected move-house answer, installation day, the two coverage measures with
two names, the estimate-to-proposal bridge, rounded savings, no town-centre pin, the card's ratio at the meter, and
the website estimate's battery note. Unit tests on the builders; the PDF text is checked in test_documents."""
from copy import deepcopy

import pytest

from solarapp.core.quick import GOAL_LABEL, battery_note
from solarapp.reports.card import estimate_line, roof_vs_bill_line
from solarapp.reports.customer_pdf import panel_line, pin_is_the_house
from solarapp.reports.quotation_pdf import (
    KIND_LABEL, aircon_at_night, battery_backup_line, battery_carries, battery_row, coverage_row, in_short, installation_day_lines,
    lead_estimate_sentence, move_house_answer, night_kwh, php_about, production_row, years_about,
)
from solarapp.schemas import AssessmentDoc

# a reconciled day: 0.5 kW by day, 1.0 kW at night (6 pm to 6 am = 12 kWh), the same every month
NIGHT_LOAD = [1.0] * 6 + [0.5] * 12 + [1.0] * 6


def _sizing(kind="combination", night_kw=1.0, coverage=92.2, dod=0.85, hours=0):
    load = [night_kw] * 6 + [0.5] * 12 + [night_kw] * 6
    return {
        "kind": kind, "coverage_pct": coverage, "annual_production_kwh": 5966.3, "annual_consumption_kwh": 5376.6,
        "battery": {"depth_of_discharge": dod, "days_of_autonomy": 1.0 if kind != "net_metering" else None},
        "profiles": {str(m): {"load": load} for m in range(1, 13)},
        "hourly_year": {"available": True, "loss_of_load_hours": hours, "loss_of_load_days": max(1, hours // 4) if hours else 0},
    }


def _doc(aircon_window=None, future=False):
    apps = [{"id": "ref", "name": "Refrigerator", "category": "refrigerator", "input_power_w": 150, "windows": [{"start": "06:00", "end": "06:00"}]}]
    if aircon_window:
        apps.append({"id": "ac", "name": "Aircon", "category": "aircon_inverter", "input_power_w": 1300, "status": "future" if future else "existing", "windows": [aircon_window]})
    return AssessmentDoc.model_validate({"customer_name": "Maria Santos", "audit": {"appliances": apps}})


def _results(kind="combination", bill_after=290.69, payback=5.03, future=True, total=314600.0, tax=33698.12, **kw):
    return {
        "sizing": _sizing(kind, **kw),
        "economics": {"available": True, "bill_today_monthly": 4058.0, "bill_today_kwh": 338.0, "includes_future_loads": future,
                      "bill_before_monthly": 5379.22 if future else 4058.0, "bill_after_monthly": bill_after, "payback_years": payback},
        "pricing": {"customer": {"total": total, "sections": [{"key": "materials", "amount": 253555.08}, {"key": "labor", "amount": 27346.79}, {"key": "tax", "amount": tax}]}},
    }


# ---- figures as a person says them

def test_savings_and_payback_round_as_a_person_says_them():
    assert php_about(1414229.20) == "about PHP 1.41 million"
    assert php_about(1025889) == "about PHP 1.03 million"
    assert php_about(1400000) == "about PHP 1.4 million"
    assert php_about(61062.36) == "about PHP 61,000"
    assert php_about(3767.31) == "about PHP 3,800"
    assert php_about(-12000) == "about -PHP 12,000"
    assert years_about(5.03) == "about 5 years" and years_about(3.57) == "about 3½ years" and years_about(1.1) == "about 1 year"
    assert years_about(0.4) == "under a year" and years_about(3.3) == "about 3½ years" and years_about(3.2) == "about 3 years"


# ---- the battery sentence, from the hourly balance already in the results

def test_night_kwh_comes_from_the_balance_and_the_aircon_window_is_read():
    assert night_kwh(_sizing()) == pytest.approx(12.0)
    assert night_kwh({"profiles": {}}) is None and night_kwh({}) is None
    assert aircon_at_night(_doc({"start": "21:00", "end": "05:00"})) is True   # crosses midnight
    assert aircon_at_night(_doc({"start": "13:00", "end": "17:00"})) is False   # an afternoon aircon is outside the night figure
    assert aircon_at_night(_doc({"start": "13:00", "end": "17:00"}, future=True)) is False
    assert aircon_at_night(_doc({"start": "20:00", "end": "20:00"})) is True    # 24 h
    assert aircon_at_night(_doc()) is False


def test_battery_holds_the_whole_night_or_says_how_many_hours():
    doc = _doc({"start": "21:00", "end": "05:00"})
    # 15 kWh at 85% = 12.75 kWh usable against 12 kWh used from 6 pm to 6 am: the whole night, aircon included
    clause, whole = battery_carries(doc, _sizing(), 15.0)
    assert whole and clause == "enough for a whole night of your usual use (about 12 kWh from 6 pm to 6 am, aircon included, against 13 kWh usable)"
    assert battery_row(doc, _sizing(), 15.0) == (
        "15 kWh lithium battery (LiFePO4), enough for a whole night of your usual use (about 12 kWh from 6 pm to 6 am, aircon included, against 13 kWh usable), "
        "recharged by the panels the next day; in the rainy season the grid covers the rest.")
    # 10 kWh at 85% = 8.5 kWh usable against 12 kWh: 8.5 / (12 / 12 h) = 8.5 hours of the evening's average draw
    clause, whole = battery_carries(doc, _sizing(), 10.0)
    assert not whole and clause == "about 8 hours of your evening use, aircon included, from 8 kWh usable against about 12 kWh used from 6 pm to 6 am"
    # no aircon in the night window: the loads are named and the aircon caveat stays
    clause, _ = battery_carries(_doc(), _sizing(), 10.0)
    assert clause.startswith("about 8 hours of your evening use (lights, fans, refrigerator, TV, Wi-Fi; aircon shortens that)")
    # the battery-first kind ends without the rainy-season clause; no battery or no balance prints the unit alone
    assert battery_row(doc, _sizing("off_grid"), 15.0).endswith("recharged by the panels the next day.")
    assert battery_carries(doc, _sizing("net_metering"), 15.0) == ("", False) and battery_carries(doc, {"kind": "combination"}, 15.0) == ("", False)
    assert battery_row(doc, {"kind": "combination"}, 15.0) == "15 kWh lithium battery (LiFePO4)"


def test_battery_backup_line_is_the_battery_first_kinds_only_and_says_one_evening():
    assert battery_backup_line(_sizing("combination")) == ""   # the hybrid's line is the Battery row
    line = battery_backup_line(_sizing("off_grid", hours=286))
    assert line.startswith("Designed to carry one evening without sun;") and "about 286 hours on 71 days" in line
    assert "1 evening" not in line
    assert battery_backup_line(_sizing("net_metering")) == ""


# ---- in short

def test_in_short_states_the_situation_and_the_solution_from_the_results():
    doc = _doc({"start": "21:00", "end": "05:00"})
    text = in_short(doc, _results(), 7, 4.095, 15.0)
    assert text == (
        "Your bill today is PHP 4,058 a month for 338 kWh; with the appliances you plan to add it would be about PHP 5,379. "
        "7 panels (4.09 kWp) and a 15 kWh battery cover 92% of what the house uses: the bill comes down to about PHP 291 a month, "
        "and the battery carries your whole night when the grid drops. "
        "PHP 280,902 before VAT and PHP 33,698 VAT: PHP 314,600 installed, permits and VAT included; it pays for itself in about 5 years.")
    # the kind sentence per kind; a smaller battery carries "your evening"
    assert "and the battery carries your evening when the grid drops" in in_short(doc, _results(), 7, 4.095, 10.0)
    nm = in_short(doc, _results("net_metering", bill_after=1422.75, payback=3.7, coverage=29.4), 7, 4.095, 0.0)
    assert "7 panels (4.09 kWp) cover 29% of what the house uses: the bill comes down to about PHP 1,423 a month; there is no battery, so the house runs on the grid at night and in a brownout." in nm
    assert "battery" not in nm.split("there is no battery")[0]
    og = in_short(doc, _results("off_grid", bill_after=158.0, payback=5.57, coverage=97.1, hours=286), 8, 4.68, 13.0)
    assert "the battery carries the house at night, nothing is sold back, and the grid steps in only in long rainy spells (about 286 hours a year)." in og
    assert "it pays for itself in about 5½ years" in og
    # a missing figure drops its sentence, never invents one
    r = _results(future=False)
    assert "with the appliances" not in in_short(doc, r, 7, 4.095, 15.0) and "Your bill today is PHP 4,058 a month for 338 kWh." in in_short(doc, r, 7, 4.095, 15.0)
    r["economics"] = {"available": False}
    text = in_short(doc, r, 7, 4.095, 15.0)
    assert text.startswith("7 panels (4.09 kWp) and a 15 kWh battery cover 92% of what the house uses, and the battery") and "bill" not in text and "pays for itself" not in text
    assert text.endswith("PHP 280,902 before VAT and PHP 33,698 VAT: PHP 314,600 installed, permits and VAT included.")
    r["pricing"] = {"customer": {}}
    r["sizing"]["coverage_pct"] = None
    assert in_short(doc, r, 7, 4.095, 15.0) == ""
    assert in_short(doc, _results(payback=None), 7, 4.095, 15.0).endswith("PHP 314,600 installed, permits and VAT included.")


# ---- the other answers

def test_move_house_answer_claims_no_value_and_no_transfer():
    for kind in ("net_metering", "combination"):
        assert move_house_answer(kind) == "The system stays with the house. Net metering is tied to the service connection, so the new owner continues it with the electric company; we help with the paperwork."
    assert move_house_answer("off_grid") == "The system stays with the house, and the new owner keeps using it. We hand over the plans and the papers."
    for kind in ("net_metering", "combination", "off_grid"):
        assert "value" not in move_house_answer(kind) and "transfers" not in move_house_answer(kind)


def test_two_measures_get_two_names():
    assert coverage_row(_sizing("net_metering", coverage=29.4)) == ["Used straight from the panels", "29% of your usage; the rest of the day's solar goes to the grid and is credited on your bill"]
    assert coverage_row(_sizing("combination", coverage=92.2)) == ["Covered by solar, by day and from the battery", "92% of your usage"]
    assert coverage_row(_sizing("off_grid", coverage=97.1)) == ["Covered by the panels and the battery", "97% of your usage"]
    assert coverage_row({"kind": "combination"}) is None
    assert production_row(_sizing(), None) == ["Solar power made", "about 5,966 kWh a year at your meter, 111% of what you use"]
    assert production_row({"annual_production_kwh": 5000.0}, None) == ["Solar power made", "about 5,000 kWh a year at your meter"]
    assert production_row({}, {"annual_kwh_ac": 4100.4}) == ["Solar power made", "about 4,100 kWh a year at your meter"]
    assert production_row({}, None) is None


def test_installation_day_comes_from_the_program_and_the_owners_setting():
    prog = {"available": True, "install": {"days": 1, "crew": {"persons": 6}, "frame": {"arrive": "06:15", "pack_up_end": "14:45"}}}
    lines = installation_day_lines(prog, "combination", True, 2.0)
    assert lines == [
        "Our crew of 6 arrives about 6:15 am and is usually done by about 2:45 pm. We need someone at home, the gate open for the materials, and access to the roof, the panel board and the wall where the inverter and the battery go.",
        "Your power is off for about 2 hours while we connect the inverter to your panel board; we tell you before we switch it off.",
        "What we need from you: a copy of your latest electric bill and your signature on the net metering forms we prepare. If your electric company asks for anything more, we confirm the list with you.",
    ]
    # blank setting: the length is not stated; no battery: the inverter alone; battery first: no net metering papers
    lines = installation_day_lines(prog, "net_metering", False, 0)
    assert lines[0].endswith("the wall where the inverter goes.") and lines[1] == "Your power is off while we connect the inverter to your panel board; we tell you before we switch it off."
    assert installation_day_lines(prog, "off_grid", True, 1)[1] == "Your power is off for about 1 hour while we connect the inverter to your panel board; we tell you before we switch it off."
    assert len(installation_day_lines(prog, "off_grid", True, None)) == 2
    two = {"available": True, "install": {"days": 2, "crew": {"persons": 6}, "frame": {"arrive": "06:15", "pack_up_end": "14:45"}}}
    assert installation_day_lines(two, "combination", True, None)[0].startswith("Our crew of 6 arrives about 6:15 am on each of the 2 days and is usually done by about 2:45 pm on the last day.")
    assert installation_day_lines({"available": False}, "combination", True, 2) == []


def test_bridge_says_what_changed_and_the_card_names_the_panels():
    doc = AssessmentDoc.model_validate({"customer_name": "Maria", "lead": {"created_at": "2026-10-09T04:31:37", "estimate": {"goal": "combination", "panels": 5, "kwp": 2.93, "battery_kwh": 10, "price": 263000}},
                                        "audit": {"appliances": [{"id": "ac2", "name": "Second aircon", "category": "aircon_inverter", "status": "future", "windows": [{"start": "13:00", "end": "17:00"}]}]}})
    assert lead_estimate_sentence(doc, {"includes_future_loads": True}, 7, 15.0, 314600.0) == (
        "Your website estimate on 9 Oct 2026 was PHP 263,000 for 5 panels and a 10 kWh battery. "
        "Measured on your roof and with the appliances you plan to add, it is 7 panels and a 15 kWh battery at PHP 314,600.")
    plain = deepcopy(doc)
    plain.audit.appliances = []
    assert lead_estimate_sentence(plain, {"includes_future_loads": False}, 7, 0.0, 181000.0).endswith("Measured on your roof, it is 7 panels at PHP 181,000.")
    assert lead_estimate_sentence(doc, None).endswith("This proposal is measured on your roof and includes the appliances you plan to add.")
    assert lead_estimate_sentence(AssessmentDoc(), None, 7, 15.0, 314600.0) == ""
    assert estimate_line(doc) == "Your estimate said about 5 panels and PHP 263,000; the visit settles the exact figure."
    doc.lead.estimate.panels = 0
    assert estimate_line(doc) == "Your estimate said about PHP 263,000; the visit settles the exact figure."
    assert estimate_line(AssessmentDoc()) == ""


def test_card_ratio_uses_the_at_meter_figure():
    # 2,110 kWh at the meter against a 338 kWh bill is 6.2 times, the figure the roof check PDF prints; never the at-panels 6.9
    line = roof_vs_bill_line(2110, 338)
    assert line.startswith("Your bill shows 338 kWh a month. Your roof can make about 2,110 kWh, around 6.2 times what your house uses.")
    assert roof_vs_bill_line(300, 338) == "Your bill shows 338 kWh a month. Your roof can make about 300 kWh, about 89% of what your house uses."


def test_roof_check_panel_name_and_the_town_centre_pin():
    panel = {"name": "585W Monofacial solar panel", "watt_peak": 585.0}
    assert panel_line(panel, {"lines": [{"category": "Solar Panel", "supplier": "Blue Carbon"}]}) == "585 W panel (Blue Carbon)"
    assert panel_line(panel, None) == "585 W panel" and "Monofacial" not in panel_line(panel, {"lines": []})
    from solarapp.core.towns import find_town
    pila = find_town("Pila", "Laguna")
    assert pin_is_the_house(pila[2], pila[3]) is False      # the listed town centre: the hand-off's default pin
    assert pin_is_the_house(pila[2] + 0.003, pila[3]) is True   # a pin placed on a house about 300 m away
    assert pin_is_the_house(None, None) is False


def test_one_customer_name_for_the_third_kind():
    assert KIND_LABEL["off_grid"] == "Battery first, nothing sold back (the grid as backup)"
    assert GOAL_LABEL["off_grid"] == "battery first, nothing sold back (the grid as backup)"
    for label in (KIND_LABEL["off_grid"], GOAL_LABEL["off_grid"]):
        assert "bigger" not in label and "Independent" not in label


# ---- the website estimate's battery note, from the pattern shape

def test_website_battery_note_from_the_pattern_shape():
    # Pila, 333 kWh a month, all day: the shape's night share (6 pm to 6 am) of 10.95 kWh a day is about 5.0 kWh against 8.5 kWh usable
    n = battery_note(10.0, 333, "balanced", 0.85)
    assert n["night_kwh"] == pytest.approx(5.0, abs=0.1) and n["usable_kwh"] == pytest.approx(8.5) and n["hours"] is None
    assert n["text"] == "enough for a typical night of your use when the grid is down"
    # a bigger evening house with the same battery: hours of the evening's average draw
    n = battery_note(10.0, 1200, "evening", 0.85)
    assert n["night_kwh"] > n["usable_kwh"] and n["hours"] == pytest.approx(n["usable_kwh"] / (n["night_kwh"] / 12))
    assert n["text"] == f"about {n['hours']:.0f} hours of your evening use when the grid is down"
    assert battery_note(0.0, 333, "balanced", 0.85)["text"] == ""


def test_quick_estimate_carries_the_battery_note_and_its_assumption():
    from pathlib import Path

    from solarapp.core.dataset import PvgisDataset
    from solarapp.core.quick import quick_estimate
    from solarapp.data_download.cli import write_synthetic
    from solarapp.pricing.importer import read_workbook
    from solarapp.pricing.job import PricingContext
    from solarapp.schemas import QuickRequest
    import tempfile

    imp = read_workbook(Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx")
    ctx = PricingContext(imp.catalog, imp.config)
    with tempfile.TemporaryDirectory() as d:
        write_synthetic(Path(d), (14.0, 14.5, 121.0, 121.5), 0.25)
        pvgis = PvgisDataset(Path(d))
        q = quick_estimate(QuickRequest(goal="combination", town="Pila", province="Laguna", monthly_kwh=333, pattern="balanced"), pvgis, ctx)
        og = quick_estimate(QuickRequest(goal="off_grid", town="Pila", province="Laguna", monthly_kwh=333, pattern="balanced"), pvgis, ctx)
    sy = q["system"]
    assert sy["battery_kwh"] >= 0.5
    assert sy["battery_note"] == "enough for a typical night of your use when the grid is down" or sy["battery_note"].startswith("about ")
    assert sy["battery_usable_kwh"] == pytest.approx(sy["battery_kwh"] * 0.85) and sy["battery_night_kwh"] > 0
    assert q["alternative"]["system"]["battery_note"] == "" and q["alternative"]["system"]["battery_night_kwh"] == 0.0
    assert any(a.startswith("What the battery carries assumes your evening follows the pattern you chose (spread through the day) and that 85% of the battery's rating is usable each night") for a in q["assumptions"])
    # the third kind carries its one customer name into the assumptions line the lead notice quotes
    assert any(a.endswith(": battery first, nothing sold back (the grid as backup).") for a in og["assumptions"])
    assert og["system"]["battery_note"] and og["goal_label"] == "battery first, nothing sold back (the grid as backup)"
