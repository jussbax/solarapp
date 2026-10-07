import math
from datetime import datetime

from solarapp.core.kfactor import (
    ReadingRow, ReadingSetInput, evaluate_reading_set, relative_efficiency, select_site_set,
)


def test_relative_efficiency_is_one_at_stc():
    assert abs(relative_efficiency(1000, 25) - 1.0) < 1e-9


def test_relative_efficiency_drops_with_heat_and_low_light():
    assert relative_efficiency(800, 60) < relative_efficiency(800, 25)
    assert relative_efficiency(200, 25) < 1.0
    assert abs(relative_efficiency(800, 25) - 1.0) < 0.01


def test_k_raw_matches_owner_formula_per_row():
    s = ReadingSetInput(
        readings=[ReadingRow(900, 36.0, 55), ReadingRow(880, 35.0, 56), ReadingRow(910, 36.5, 55)],
        ambient_temp_c=32, sky_condition="clear",
    )
    r = evaluate_reading_set(s)
    expected = [36.0 / (50 * 0.9), 35.0 / (50 * 0.88), 36.5 / (50 * 0.91)]
    for a, b in zip(r.k_raw_values, expected):
        assert abs(a - b) < 1e-9
    assert abs(r.k_raw - sum(expected) / 3) < 1e-9
    assert r.k_site > r.k_raw  # heat removed
    assert r.ambient_source == "measured"
    assert r.rise_is_plausible
    assert not r.low_confidence
    assert 20 < r.rise_per_kw < 30


def test_calibration_factor_scales_k():
    rows = [ReadingRow(900, 36.0, 55)] * 3
    base = evaluate_reading_set(ReadingSetInput(readings=rows, ambient_temp_c=30))
    cal = evaluate_reading_set(ReadingSetInput(readings=rows, ambient_temp_c=30, calibration_factor=0.96))
    assert abs(cal.k_raw - base.k_raw / 0.96) < 1e-9


def test_quality_warnings():
    s = ReadingSetInput(
        readings=[ReadingRow(400, 16.0, 40), ReadingRow(300, 12.0, 39), ReadingRow(450, 18.0, 41)],
        sky_condition="cloudy",
    )
    r = evaluate_reading_set(s, ambient_estimate_c=29.0)
    codes = {w.code for w in r.warnings}
    assert {"low_irradiance", "unstable_irradiance", "cloudy_sky", "ambient_estimated"} <= codes
    assert r.low_confidence
    assert r.ambient_source == "estimated"


def test_no_ambient_disables_site_rise():
    r = evaluate_reading_set(ReadingSetInput(readings=[ReadingRow(900, 36.0, 55)] * 3))
    assert r.rise_per_kw is None and not r.rise_is_plausible
    assert any(w.code == "no_ambient" for w in r.warnings)


def test_select_highest_k_site():
    a = evaluate_reading_set(ReadingSetInput(readings=[ReadingRow(900, 34.0, 55)] * 3, ambient_temp_c=30, label="A"))
    b = evaluate_reading_set(ReadingSetInput(readings=[ReadingRow(900, 37.0, 55)] * 3, ambient_temp_c=30, label="B"))
    empty = evaluate_reading_set(ReadingSetInput(readings=[]))
    assert select_site_set([a, empty, b]) == 2
    assert select_site_set([empty]) is None


def test_missing_module_temperature_is_estimated():
    rows = [ReadingRow(930, 272.6), ReadingRow(1002, 272.6), ReadingRow(949, 272.6)]
    r = evaluate_reading_set(ReadingSetInput(readings=rows, test_panel_rating_w=350), ambient_estimate_c=29.0)
    assert r.module_temp_source == "estimated" and r.ambient_source == "estimated"
    assert 50 < r.avg_module_temp_c < 70  # PVGIS thermal model at ~960 W/m2 and 29 C ambient
    assert r.rise_per_kw is None and not r.rise_is_plausible
    codes = {w.code for w in r.warnings}
    assert "module_temp_estimated" in codes and "no_ambient" not in codes
    assert abs(r.k_raw - sum(272.6 / (350 * g / 1000) for g in (930, 1002, 949)) / 3) < 1e-9
    assert r.k_site > r.k_raw
    # no ambient at all: assumed 30 C, still computes
    r2 = evaluate_reading_set(ReadingSetInput(readings=rows, test_panel_rating_w=350))
    assert r2.ambient_source == "assumed" and r2.valid
    # mixed: one probe reading keeps the rise from that row only
    r3 = evaluate_reading_set(ReadingSetInput(readings=[ReadingRow(930, 272.6, 58), ReadingRow(1002, 272.6), ReadingRow(949, 272.6)], ambient_temp_c=31, test_panel_rating_w=350))
    assert r3.module_temp_source == "mixed" and r3.rise_per_kw is not None and len(r3.rise_per_kw_values) == 1
