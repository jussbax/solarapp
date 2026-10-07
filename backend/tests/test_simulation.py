import numpy as np

from solarapp.core.simulation import FaceSpec, ThermalModel, prepare_sky, simulate, typical_air_temperature
from tests.conftest import MANILA


def _face(tilt, az, n=10, fid="f1"):
    return FaceSpec(fid, "roof", tilt, az, n)


def test_basic_shape_and_totals(manila_tmy):
    lat, lon, elev = MANILA
    res = simulate(manila_tmy, lat, lon, elev, [_face(15, 180)], 550, 0.95, ThermalModel())
    assert len(res.monthly_kwh) == 12
    assert all(m > 0 for m in res.monthly_kwh)
    assert abs(res.annual_kwh - sum(res.monthly_kwh)) < 1e-6
    assert sum(res.days_in_month) == 365
    assert res.system_kwp == 5.5
    # a plausible specific yield for a tropical site with cloudy season
    assert 900 < res.faces[0].specific_yield_kwh_per_kwp < 1900


def test_horizontal_face_matches_ghi(manila_tmy):
    lat, lon, elev = MANILA
    res = simulate(manila_tmy, lat, lon, elev, [_face(0, 180)], 550, 1.0, ThermalModel())
    assert abs(res.faces[0].annual_poa_kwh_m2 - res.annual_ghi_kwh_m2) / res.annual_ghi_kwh_m2 < 0.01


def test_k_site_scales_linearly(manila_tmy):
    lat, lon, elev = MANILA
    sky = prepare_sky(manila_tmy, lat, lon, elev)
    a = simulate(manila_tmy, lat, lon, elev, [_face(15, 180)], 550, 0.5, ThermalModel(), sky=sky)
    b = simulate(manila_tmy, lat, lon, elev, [_face(15, 180)], 550, 1.0, ThermalModel(), sky=sky)
    assert abs(a.annual_kwh * 2 - b.annual_kwh) < 1e-6


def test_south_beats_north_in_manila(manila_tmy):
    lat, lon, elev = MANILA
    sky = prepare_sky(manila_tmy, lat, lon, elev)
    s = simulate(manila_tmy, lat, lon, elev, [_face(20, 180)], 550, 1.0, ThermalModel(), sky=sky)
    n = simulate(manila_tmy, lat, lon, elev, [_face(20, 0)], 550, 1.0, ThermalModel(), sky=sky)
    assert s.annual_kwh > n.annual_kwh


def test_hotter_roof_yields_less(manila_tmy):
    lat, lon, elev = MANILA
    sky = prepare_sky(manila_tmy, lat, lon, elev)
    cool = simulate(manila_tmy, lat, lon, elev, [_face(15, 180)], 550, 1.0, ThermalModel("site_rise", 20.0), sky=sky)
    hot = simulate(manila_tmy, lat, lon, elev, [_face(15, 180)], 550, 1.0, ThermalModel("site_rise", 40.0), sky=sky)
    assert hot.annual_kwh < cool.annual_kwh


def test_multiple_faces_sum(manila_tmy):
    lat, lon, elev = MANILA
    res = simulate(manila_tmy, lat, lon, elev, [_face(15, 180, 6, "a"), _face(15, 0, 4, "b")], 550, 0.9, ThermalModel())
    assert res.total_panels == 10
    assert abs(sum(f.annual_kwh for f in res.faces) - res.annual_kwh) < 1e-6


def test_typical_air_temperature(manila_tmy):
    t = typical_air_temperature(manila_tmy, 4, 12)
    assert t is not None and 20 < t < 40


def test_time_offset_shifts_solar_geometry(manila_tmy):
    lat, lon, elev = MANILA
    a = prepare_sky(manila_tmy, lat, lon, elev, 0.0)
    b = prepare_sky(manila_tmy, lat, lon, elev, 0.5)
    assert len(a.zenith) == len(b.zenith) == len(manila_tmy)
    assert (a.azimuth.values != b.azimuth.values).any()
    assert list(a.zenith.index) == list(manila_tmy.index)
