from solarapp.data_download.grid import cell_centers, land_cells
from solarapp.data_download.nasa import merge_points, parse_regional_json, tiles
from solarapp.data_download.pvgis import parse_tmy_json


def test_parse_pvgis_tmy():
    rows = []
    for h in range(24):
        rows.append({"time(UTC)": f"20120101:{h:02d}10", "T2m": 25.0 + h * 0.1, "RH": 70.0, "G(h)": 100.0 * h,
                     "Gb(n)": 50.0, "Gd(h)": 30.0, "IR(h)": 400.0, "WS10m": 1.0, "WD10m": 90.0, "SP": 101000.0})
    payload = {
        "inputs": {"location": {"latitude": 14.5, "longitude": 121.0, "elevation": 12.0},
                   "meteo_data": {"radiation_db": "PVGIS-ERA5", "meteo_db": "ERA5", "year_min": 2005, "year_max": 2023}},
        "outputs": {"months_selected": [{"month": 1, "year": 2012}], "tmy_hourly": rows},
    }
    payload["inputs"]["location"]["irradiance_time_offset"] = 0.5
    p = parse_tmy_json(payload)
    assert p.time_offset_h == 0.5
    assert len(p.frame) == 24 and str(p.frame.index.tz) == "UTC"
    assert p.frame["ghi"].iloc[5] == 500.0
    assert p.radiation_db == "PVGIS-ERA5" and p.elevation_m == 12.0


def test_parse_nasa_regional():
    payload = {"features": [
        {"geometry": {"coordinates": [121.0, 14.5, 10]}, "properties": {"parameter": {
            "ALLSKY_SFC_SW_DWN": {m: 5.0 for m in ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC", "ANN"]},
            "T2M": {m: 27.0 for m in ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC", "ANN"]},
        }}},
        {"geometry": {"coordinates": [122.0, 14.5, 10]}, "properties": {"parameter": {"ALLSKY_SFC_SW_DWN": {"JAN": -999}}}},
    ]}
    raw = parse_regional_json(payload)
    assert len(raw) == 2
    pts = merge_points(raw)
    assert len(pts) == 1 and pts[0]["ghi_annual_kwh_m2_day"] == 5.0 and len(pts[0]["ghi_kwh_m2_day"]) == 12
    assert pts[0]["t2m_c"][0] == 27.0


def test_parse_merges_parameters_from_separate_responses():
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC", "ANN"]
    a = {"features": [{"geometry": {"coordinates": [121.5, 14.5, 10]}, "properties": {"parameter": {"ALLSKY_SFC_SW_DWN": {m: 5.0 for m in months}}}}]}
    b = {"features": [{"geometry": {"coordinates": [121.5, 14.5, 10]}, "properties": {"parameter": {"T2M": {m: 27.0 for m in months}}}}]}
    raw = parse_regional_json(a)
    for k, rec in parse_regional_json(b).items():
        raw.setdefault(k, {"lat": rec["lat"], "lon": rec["lon"]}).update(rec)
    pts = merge_points(raw)
    assert len(pts) == 1 and pts[0]["t2m_c"][5] == 27.0 and pts[0]["ghi_kwh_m2_day"][0] == 5.0


def test_tiles_cover_box_and_keep_minimum_size():
    t = tiles((4.0, 21.5, 116.0, 127.0), 8.0)
    assert len(t) == 3 * 2
    assert t[-1][1] == 21.5 and t[-1][3] == 127.0
    assert all(b - a >= 2.0 and d - c >= 2.0 for a, b, c, d in t)


def test_land_mask_keeps_manila_drops_open_sea():
    cells = cell_centers((14.5, 14.5, 121.0, 121.0), 0.25) + cell_centers((12.0, 12.0, 112.0, 112.0), 0.25)
    kept = land_cells(cells, 0.25)
    assert any(abs(c.lat - 14.5) < 1e-6 and abs(c.lon - 121.0) < 1e-6 for c in kept)
    assert not any(abs(c.lon - 112.0) < 1e-6 for c in kept)


def test_tiles_pad_small_boxes():
    (lat_min, lat_max, lon_min, lon_max), = tiles((14.25, 14.75, 120.75, 121.25), 8.0)
    assert lat_max - lat_min >= 2.0 and lon_max - lon_min >= 2.0
