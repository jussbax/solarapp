"""Round 12, the datasheet importer's parser: one case per rule of the brief's section 1.5, asserting the value,
the flag and the notice text (5.4). Nothing on a sheet is corrected; an irregular cell is parsed by its rule and
flagged, and the figure the brief says to hold is held."""
from pathlib import Path

import pytest

from solarapp.pricing.datasheets import (
    battery_class_of_text, class_of_voltage, inverter_type_of, norm, parse_battery_charge_voltage, parse_battery_details, parse_current,
    parse_inverter_charge_voltage, parse_kw, parse_kwh, parse_measure, parse_mppt, parse_system_voltage, phase_from_details,
    read_datasheet_workbook, strip_maker,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "datasheets"
PANELS, INVERTERS, BATTERIES = (FIXTURES / f"ALL_{n}_DATA_SHEET.xlsx" for n in ("SOLAR_PANEL", "INVERTER", "BATTERY"))


def test_norm_drops_everything_but_letters_and_digits():
    assert norm("SMART-BCT-V-48-100 P") == norm("SMART-BCT-V-48-100P") == "SMARTBCTV48100P"
    assert norm("IVEM12048(-II)") == "IVEM12048II"


def test_panel_cells():
    # "~42.10 V" parses to the number and flags the row approximate (1.1, panel sheet row 13)
    p = parse_measure("~42.10 V", "Vmp")
    assert p.value == 42.1 and "approximate" in p.flags and "marked approximate on the datasheet; verify" in p.notices[0]
    assert parse_measure("585W").value == 585 and parse_measure("585 W").value == 585 and not parse_measure("585 W").notices
    # two system-voltage ratings with a slash: the lower is stored, the row says so (row 4)
    sv = parse_system_voltage("600V DC / 1000V DC")
    assert sv.value == 600 and "two_ratings" in sv.flags and "the lower, 600 V, is used; verify which applies to the unit sold" in sv.notices[0]
    assert parse_system_voltage("1500V DC").value == 1500 and parse_system_voltage("1500 V DC").value == 1500 and not parse_system_voltage("1500V DC").notices
    assert parse_measure(None).value is None


def test_maker_words_come_off_the_front_of_a_panel_model_text():
    brands = {"Solar Homes", "JA Solar", "Trina Solar", "IAN Solar", "Aiko", "BLUE CARBON"}
    assert strip_maker("JA Solar JAM66D45 630W", brands) == ("JAM66D45 630W", "JA Solar")
    assert strip_maker("Trina Solar Mono 620W N-Type", brands) == ("Mono 620W N-Type", "Trina Solar")
    assert strip_maker("AIKO Solar ABC 665W Bifacial", brands) == ("ABC 665W Bifacial", "Aiko Solar")
    assert strip_maker("IAN Solar IAN670-132BCDGF 670W", brands) == ("IAN670-132BCDGF 670W", "IAN Solar")
    assert strip_maker("100W 10BB Mono", brands) == ("100W 10BB Mono", "")
    assert strip_maker("585W Monofacial", brands) == ("585W Monofacial", "")


def test_inverter_charge_voltage_rules():
    # "N/A (No Battery Input)" is a fact, not a gap: blank, flagged, no notice
    nb = parse_inverter_charge_voltage("N/A (No Battery Input)")
    assert nb.value is None and "no_battery" in nb.flags and nb.notices == []
    assert parse_inverter_charge_voltage("60V").value == 60 and parse_inverter_charge_voltage("58.4 V").value == 58.4 and parse_inverter_charge_voltage("14.6V").value == 14.6
    assert parse_inverter_charge_voltage("1,000V").value == 1000 and not parse_inverter_charge_voltage("1,000V").notices   # the comma is stripped, no notice
    assert parse_inverter_charge_voltage("936V").value == 936
    # a range narrower than 5 V takes the lower figure as the conservative maximum (Felicity 3P rows)
    narrow = parse_inverter_charge_voltage("58.4V–60V")
    assert narrow.value == 58.4 and "range" in narrow.flags and narrow.extra["range"] == [58.4, 60] and "narrower than 5 V: the lower figure, 58.4 V, is the maximum used" in narrow.notices[0]
    # 5 V or wider, en dash or hyphen, takes the upper figure and keeps the low end in the notes
    for text in ("40 – 60 V", "40-60V"):
        wide = parse_inverter_charge_voltage(text)
        assert wide.value == 60 and wide.extra["range"] == [40, 60] and "the upper figure, 60 V, is the maximum; the low end 40 V is kept here" in wide.notices[0]
    bms = parse_inverter_charge_voltage("Varies by BMS / Up to 800V")
    assert bms.value == 800 and "varies_bms" in bms.flags and "varies by BMS; 800 V is used; verify per battery" in bms.notices[0]


def test_battery_charge_voltage_takes_the_upper_figure_and_keeps_the_floor():
    for text, lo, hi in (("44.8-57.6V", 44.8, 57.6), ("48-57.6", 48, 57.6), ("185.6-230V", 185.6, 230), ("359-460V", 359, 460), ("22.4-28.8V", 22.4, 28.8), ("11.2-14.4V", 11.2, 14.4)):
        p = parse_battery_charge_voltage(text)
        assert p.value == hi and p.extra["range"] == [lo, hi] and f"the lower, {lo:g} V, is kept here as the discharge floor" in p.notices[0] and "assumption" in p.notices[0]
    assert parse_battery_charge_voltage("921.6V").value == 921.6 and parse_battery_charge_voltage("57.6V").notices == []


def test_current_cells():
    assert parse_current("250A", "x").value == 250 and parse_current("135 A", "x").value == 135 and parse_current("135 A", "x").notices == []
    star = parse_current("240A*", "recommended discharge current")
    assert star.value == 240 and "asterisk" in star.flags and "marked with an asterisk on the sheet; the condition is not on the sheet; verify" in star.notices[0]
    up = parse_current("Up to 290A*", "x")
    assert up.value == 290 and {"asterisk", "up_to"} <= up.flags and len(up.notices) == 1
    assert parse_current("100A*", "x").value == 100 and "asterisk" in parse_current("100A*", "x").flags
    # "80A + 80A" and "50A + 50A (Dual Input)": the per-input figure and two inputs
    for text, per in (("80A + 80A", 80), ("50A + 50A", 50), ("100A + 100A", 100), ("70A + 70A", 70), ("50A + 50A (Dual Input)", 50)):
        d = parse_current(text, "x")
        assert d.value == per and d.extra["inputs"] == 2 and "two battery inputs on the datasheet" in d.notices[0] and "prices one circuit and says to verify" in d.notices[0]
    # blanks with and without a notice
    no = parse_current("NO DISCHARGE OUTPUT", "x")
    assert no.value is None and "no_output" in no.flags and no.notices == []
    assert parse_current("N/A", "x", no_battery=True).notices == [] and parse_current("N/A", "x", no_battery=True).value is None
    assert parse_current("N/A", "max recommended charge current").notices == ["max recommended charge current is N/A on the sheet"]
    v = parse_current("Verify", "max recommended charge current")
    assert v.value is None and "verify" in v.flags and v.notices == ["max recommended charge current is marked Verify on the sheet"]
    # the twelve kW cells in the Felicity amps column: blank with the notice, never a number
    for text in ("13kW", "32kW", "28.8kW", "24kW", "22.4kW", "18kW", "15kW", "80kW", "64kW", "48kW", "47.84kW", "40kW"):
        k = parse_current(text, "max recommended charge current")
        assert k.value is None and "kw_in_amps" in k.flags and "a kW figure" in k.notices[0] and "asked of the owner (6.3)" in k.notices[0]
    w = parse_current("29.6A standard", "recommended discharge current")
    assert w.value == 29.6 and "word" in w.flags and "the sheet says '29.6A standard'; 29.6 A is used and the word is kept here" in w.notices[0]


def test_kw_kwh_mppt_and_details():
    assert parse_kw("8 kW") == 8 and parse_kw("0.48 Kw-12V") == 0.48 and parse_kw("1.2KW-12V") == 1.2 and parse_kw("13KW-720V") == 13
    assert parse_kw("12 kW; List says '12W' - typo for 12kW") == 12          # the kW match comes first; "12W" is never a rating
    assert parse_kw("30 kW; 220-230V; HV battery; HV battery; list shows '259,00' - confirm") == 30
    assert parse_kw("Commercial") is None
    assert parse_mppt("12 kW; MPPT 18/36/36A") == (3, 18, "18/36/36") and parse_mppt("6 kW; MPPT 18/18A") == (2, 18, "18/18") and parse_mppt("8 kW") is None
    assert parse_kwh("10.24 kWh") == 10.24 and parse_kwh("3.83kWh") == 3.83 and parse_kwh("16.076 kWh") == 16.076
    assert parse_kwh("16 kWh; IP65; ~16.1 kWh") == 16                           # the "~" figure is ignored
    assert parse_battery_details("48 V; 100 Ah; 4.8 kWh") == {"nominal_v": 48, "capacity_ah": 100, "kwh": 4.8}
    assert parse_battery_details("1 kWh; 4.74 kWh/module, min 37.92 kWh") == {"nominal_v": None, "capacity_ah": None, "kwh": 1}
    assert parse_battery_details("100 Ah; 40 kWh") == {"nominal_v": None, "capacity_ah": 100, "kwh": 40}


def test_the_type_table_and_the_phase_words():
    assert inverter_type_of("Grid-tie 1P") == ("grid_tie", 1, True) and inverter_type_of("Grid-tie 3P") == ("grid_tie", 3, True)
    assert inverter_type_of("Hybrid 1P") == ("hybrid", 1, True) and inverter_type_of("Hybrid 3P") == ("hybrid", 3, True) and inverter_type_of("Hybrid") == ("hybrid", None, True)
    assert inverter_type_of("Off-grid") == ("off_grid", None, False) and inverter_type_of("OFF GRID") == ("off_grid", None, False)
    assert inverter_type_of("Off-grid/Grid-tie") == ("hybrid", None, None)            # two modes named: unknown, like "(on/off-grid)"
    assert inverter_type_of("Charge controllers (MPPT)") == ("charge_controller", None, False)
    assert inverter_type_of("Commercial ESS (inverter + battery set)") == ("ess_set", 3, None)
    assert inverter_type_of("") == ("", None, None)
    assert phase_from_details("150 kW; 380-400V") == 3 and phase_from_details("200 kW; 480V") == 3 and phase_from_details("50 kW; 380V") == 3 and phase_from_details("125 kW; 440-480V") == 3
    assert phase_from_details("3.0KW-230V") == 1 and phase_from_details("8 kW") is None
    assert class_of_voltage(14.6) == 12 and class_of_voltage(29.2) == 24 and class_of_voltage(60) == 48 and class_of_voltage(800) == "HV" and class_of_voltage(None) is None
    assert battery_class_of_text("LOW VOLTAGE") == "LV" and battery_class_of_text("HIGH VOLTAGE") == "HV" and battery_class_of_text("12V / 24V batteries") == "LV"
    assert battery_class_of_text("48V low-voltage batteries") == "LV" and battery_class_of_text("High-voltage batteries") == "HV" and battery_class_of_text("12 kW; LV battery") == "LV"


@pytest.fixture(scope="module")
def sheets():
    """The three fixture workbooks as parsed, keyed by (sheet, row) under "panels", "inverters" and "batteries"."""
    out: dict[str, dict] = {"panels": {}, "inverters": {}, "batteries": {}}
    brands: set[str] = set()
    for kind, path in (("panels", PANELS), ("inverters", INVERTERS), ("batteries", BATTERIES)):
        for r in read_datasheet_workbook(path, brands=brands):
            brands.add(r.brand)
            out[kind][(r.source_sheet, r.source_row)] = r
    return out


def test_the_sheets_are_read_by_their_words_not_their_names(sheets):
    assert {r.category for r in sheets["inverters"].values()} == {"Inverter", "All-in-one System"}
    assert len(sheets["panels"]) == 14 and all(r.category == "Solar Panel" and r.source_sheet == "Sheet1" for r in sheets["panels"].values())
    assert len(sheets["batteries"]) == 82 and all(r.category == "Battery" for r in sheets["batteries"].values())
    # the header on the Felicity inverter sheet sits on row 4, the data from row 5; the Solis orphan rows are skipped with the reason
    rows = sheets["inverters"]
    assert rows[("Sheet5", 5)].model == "IVEM3024"
    orphans = [k for k, r in rows.items() if r.skipped]
    assert len(orphans) == 7 and all(rows[k].skipped == "no model in the model column" for k in orphans) and all(k[0] == "Sheet2" and k[1] >= 33 for k in orphans)


def test_panel_rows_as_parsed(sheets):
    rows = sheets["panels"]
    r = rows[("Sheet1", 4)]
    assert r.category == "Solar Panel" and r.fields["max_system_voltage_v"] == 600 and r.fields["rating"] == 100 and r.fields["rating_unit"] == "W"
    assert any("two system-voltage ratings" in n for n in r.notices)
    approx = rows[("Sheet1", 13)]
    assert approx.fields["vmp_v"] == 42.1 and approx.fields["imp_a"] == 15.92 and approx.fields["voc_v"] == 49.5 and approx.fields["isc_a"] == 16.9
    assert sum("marked approximate" in n for n in approx.notices) == 4
    assert approx.brand == "Aiko" and approx.brand_in_model == "IAN Solar" and approx.model == "IAN670-132BCDGF 670W"
    # the six brand-shifted rows carry both brands and the maker in the text (6.1)
    shifted = {k[1]: (r.brand, r.brand_in_model) for k, r in rows.items() if r.category == "Solar Panel" and r.brand_in_model}
    assert shifted == {8: ("Trina Solar", "JA Solar"), 9: ("Trina Solar", "JA Solar"), 10: ("IAN Solar", "Trina Solar"), 11: ("JA Solar", "Trina Solar"), 12: ("JA Solar", "Aiko Solar"), 13: ("Aiko", "IAN Solar")}
    assert rows[("Sheet1", 7)].brand_in_model == "" and rows[("Sheet1", 7)].model == "JAM66D45 625W"


def test_inverter_rows_as_parsed(sheets):
    rows = sheets["inverters"]
    deye_grid = rows[("Sheet1", 3)]
    assert deye_grid.fields["inverter_type"] == "grid_tie" and deye_grid.fields["phase"] == 1 and deye_grid.fields["battery_class"] == "none" and deye_grid.fields["grid_interactive"] is True
    assert "charge_v_max" not in deye_grid.fields and deye_grid.notices == [] and not deye_grid.held
    assert rows[("Sheet1", 7)].fields["phase"] == 3                     # "380V" in the details on a Grid-tie 3P row
    hy = rows[("Sheet1", 9)]                                            # "DEYE 1P 12KW HYBRID 18/36/36A"
    assert hy.fields["mppt_count"] == 3 and hy.fields["mppt_max_a"] == 18 and hy.fields["mppt_currents_a"] == "18/36/36" and hy.fields["rating"] == 12
    assert hy.fields["charge_v_max"] == 60 and hy.fields["battery_max_a"] == 250 and hy.fields["charge_a_max"] == 250 and "battery_class" not in hy.fields
    dual = rows[("Sheet1", 15)]                                         # "1,000V", "80A + 80A", HV battery
    assert dual.fields["charge_v_max"] == 1000 and dual.fields["battery_max_a"] == 80 and dual.fields["battery_inputs"] == 2 and dual.fields["battery_class"] == "HV" and dual.fields["phase"] == 3
    star = rows[("Sheet1", 19)]
    assert star.fields["battery_max_a"] == 240 and any("asterisk" in n for n in star.notices)
    # the Solis grid-tie 1P rows: parsed by the range rule but held (1.5, 6.4)
    held = rows[("Sheet2", 5)]
    assert held.held and held.held_fields == {"charge_v_max": 60, "battery_max_a": 135, "charge_a_max": 135} and "charge_v_max" not in held.fields
    assert held.fields["inverter_type"] == "grid_tie" and held.fields["phase"] == 1 and held.fields["rating"] == 6
    assert any("battery figures on a grid-tie unit; held" in n for n in held.notices)
    ess = rows[("Sheet2", 4)]
    assert ess.category == "All-in-one System" and ess.fields["inverter_type"] == "ess_set" and ess.fields["phase"] == 3 and "rating" not in ess.fields and ess.fields["charge_v_max"] == 936
    assert rows[("Sheet2", 10)].fields["phase"] == 3 and rows[("Sheet2", 11)].fields["phase"] == 3   # 480V, 380-400V
    typo = rows[("Sheet2", 13)]
    assert typo.fields["rating"] == 12 and not any("12W" in n for n in typo.notices)
    assert any("(21A) in the details is unexplained" in n for n in rows[("Sheet2", 12)].notices)
    assert rows[("Sheet2", 21)].fields["battery_max_a"] == 290 and rows[("Sheet2", 24)].fields["charge_v_max"] == 60
    cc = rows[("Sheet3", 4)]                                            # a charge controller: 0.48 kW, class from the 14.6 V, no discharge output
    assert cc.fields["inverter_type"] == "charge_controller" and cc.fields["rating"] == 0.48 and cc.fields["battery_class"] == "LV" and cc.fields["charge_a_max"] == 40
    assert "battery_max_a" not in cc.fields and cc.fields["grid_interactive"] is False
    verify = rows[("Sheet3", 16)]
    assert "charge_a_max" not in verify.fields and any("marked Verify" in n for n in verify.notices) and verify.fields["battery_max_a"] == 93
    assert rows[("Sheet3", 13)].fields["inverter_type"] == "off_grid" and rows[("Sheet3", 13)].fields["grid_interactive"] is False
    both = rows[("Sheet4", 5)]                                          # "Off-grid/Grid-tie": hybrid, grid unknown
    assert both.fields["inverter_type"] == "hybrid" and both.fields["grid_interactive"] is None
    assert any("12 V battery and the max charge voltage 58.4 V" in n for n in rows[("Sheet4", 8)].notices)
    fel = rows[("Sheet5", 9)]
    assert fel.fields["inverter_type"] == "off_grid" and fel.fields["phase"] == 1 and fel.fields["battery_max_a"] == 139 and fel.fields["charge_a_max"] == 135 and fel.fields["charge_v_max"] == 58.4
    assert any("230 V) cannot be the battery class" in n for n in fel.notices)
    kw = rows[("Sheet5", 16)]
    assert kw.fields["charge_v_max"] == 58.4 and "charge_a_max" not in kw.fields and any("a kW figure (13kW)" in n for n in kw.notices)
    bms = rows[("Sheet5", 23)]
    assert bms.fields["charge_v_max"] == 800 and bms.fields["battery_max_a"] == 50 and bms.fields["battery_inputs"] == 2


def test_battery_rows_as_parsed(sheets):
    rows = sheets["batteries"]
    bc = rows[("Sheet1", 6)]                                            # the LV/HV column left of BATTERY TYPE has no header
    assert bc.fields["battery_class"] == "LV" and bc.raw["class"] == "LOW VOLTAGE" and bc.raw["chemistry"] == "LIFEPO4BATTERY PACK"
    assert bc.fields["nominal_v"] == 51.2 and bc.fields["capacity_ah"] == 200 and bc.fields["rating"] == 10.24 and bc.fields["rating_unit"] == "kWh"
    assert bc.fields["charge_v_max"] == 60 and bc.fields["continuous_a"] == 120 and bc.fields["discharge_a_recommended"] == 100 and bc.fields["charge_a_max"] == 40
    assert any("recommended discharge current (125 A) is above the maximum (120 A)" in n for n in rows[("Sheet1", 7)].notices)
    odd = rows[("Sheet1", 20)]                                          # 25.6 V, 120 Ah, 60 V ceiling: stored as typed, flagged
    assert odd.fields["nominal_v"] == 25.6 and odd.fields["charge_v_max"] == 60 and any("ceiling is of another class" in n for n in odd.notices)
    assert rows[("Sheet1", 27)].model == "SMART-BCT-V-48-100 P" and rows[("Sheet1", 27)].model_norm == "SMARTBCTV48100P"
    base = rows[("Sheet2", 5)]                                          # 150 A on 100 Ah: above 1 C, held
    assert base.held and base.held_fields == {"continuous_a": 150} and "continuous_a" not in base.fields and any("above 1 C (1.5 C on 100 Ah)" in n for n in base.notices)
    assert rows[("Sheet2", 4)].fields["continuous_a"] == 100 and not rows[("Sheet2", 4)].held   # 1.0 C is not above 1 C
    assert rows[("Sheet2", 6)].fields["charge_v_max"] == 57.6 and rows[("Sheet2", 6)].fields["continuous_a"] == 150
    hv = rows[("Sheet2", 14)]
    assert hv.fields["battery_class"] == "HV" and any("typed HV and the nominal voltage 51.2 V is a LV figure" in n for n in hv.notices)
    assert rows[("Sheet2", 17)].fields["rating"] == 3.83                 # "3.83kWh"
    tall = rows[("Sheet2", 43)]
    assert tall.fields["nominal_v"] == 102.4 and tall.fields["charge_v_max"] == 230 and any("2.2× the nominal" in n for n in tall.notices)
    s3 = rows[("Sheet3", 11)]                                           # Pylontech 48 V as typed; the sub-header kept the details column
    assert s3.fields["nominal_v"] == 48 and s3.fields["capacity_ah"] == 100 and s3.fields["rating"] == 4.8 and s3.fields["battery_class"] == "LV"
    assert not any("Ah = " in n for n in s3.notices)                     # 48 × 100 / 1000 = 4.8: the Ah–kWh check passes
    assert rows[("Sheet3", 10)].fields["discharge_a_recommended"] == 100 and any("asterisk" in n for n in rows[("Sheet3", 10)].notices)
    per_kwh = rows[("Sheet3", 12)]
    assert per_kwh.fields["rating"] == 1 and "nominal_v" not in per_kwh.fields and any("no nominal voltage on the sheet" in n for n in per_kwh.notices)
    assert per_kwh.fields["discharge_a_recommended"] == 29.6 and per_kwh.fields["battery_class"] == "HV"
    deye_hv = rows[("Sheet3", 17)]
    assert deye_hv.fields["capacity_ah"] == 100 and deye_hv.fields["rating"] == 40 and "nominal_v" not in deye_hv.fields and any("series stack" in n for n in deye_hv.notices)
    assert rows[("Sheet3", 6)].fields["rating"] == 16 and rows[("Sheet3", 24)].fields["rating"] == 16.076
    assert rows[("Sheet3", 39)].brand == "JK" and rows[("Sheet3", 39)].raw["brand"] == "JK (One Solar)"
    # every row with all three figures passes the Ah–kWh check (3.8): no notice anywhere on the three sheets
    assert not any("one of the three figures is wrong" in n for r in rows.values() for n in r.notices)
