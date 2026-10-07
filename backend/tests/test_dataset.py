import json

from solarapp.core.dataset import NasaReference, PvgisDataset
from solarapp.data_download.cli import write_synthetic


def test_synthetic_dataset_roundtrip(tmp_path):
    # tiny box around Manila so it is fast
    write_synthetic(tmp_path, (14.5, 14.75, 120.75, 121.0), 0.25)
    ds = PvgisDataset(tmp_path)
    assert ds.available and ds.synthetic
    cell = ds.nearest_cell(14.6, 121.0)
    assert cell is not None and cell.distance_km < 40
    tmy = ds.load_tmy(cell)
    assert len(tmy) == 8760 and str(tmy.index.tz) == "UTC"
    assert set(["ghi", "dni", "dhi", "temp_air", "wind_speed"]) <= set(tmy.columns)
    nasa = NasaReference(tmp_path)
    assert nasa.available
    p = nasa.nearest_point(14.6, 121.0)
    assert p and len(p["ghi_kwh_m2_day"]) == 12


def test_missing_dataset(tmp_path):
    ds = PvgisDataset(tmp_path)
    assert not ds.available and ds.nearest_cell(14, 121) is None
    assert ds.info()["cell_count"] == 0
