"""Round 12: the string design. The settings block (section 3 head: every value an assumption that moves the
settings version), the two TMY figures per project (T_cold and T_hot from the cell's typical-year extremes), and the
hand-worked checks of 3.1 to 3.4 on the brief's own figures."""
import math
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.pricing.config import PricingConfig, StringDesign, settings_version
from solarapp.pricing.design_checks import design_temperatures, faiman_rise_c_per_kw
from tests.test_documents import LAGUNA_DOC

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def test_the_settings_block_is_the_briefs_and_moves_the_version():
    sd = PricingConfig().string_design
    assert (sd.design_cold_c, sd.cold_margin_c, sd.design_hot_cell_c) == (14, 5, 70)
    assert (sd.temp_coeff_voc_default_pct, sd.temp_coeff_pmax_default_pct, sd.temp_coeff_isc_default_pct) == (-0.30, -0.35, 0.05)
    assert sd.isc_irradiance_factor == 1.25 and sd.dc_breaker_sizes_a == [16, 20, 25, 32, 40, 50, 63]
    cfg, cfg2 = PricingConfig(), PricingConfig()
    cfg2.string_design.design_cold_c = 10
    assert settings_version(cfg) != settings_version(cfg2)                     # a change flags quoted jobs
    cfg3 = PricingConfig(datasheets_imported_at="2026-10-10T00:00:00+00:00", datasheets_imported_from="x.xlsx")
    assert settings_version(cfg) == settings_version(cfg3)                     # the import stamp never does
    assert PricingConfig.model_validate({"wiring": {"pv_run_m": 20}}).string_design == StringDesign()   # an older config takes the block's defaults


def test_the_design_temperatures_take_the_wider_of_the_setting_and_the_cell():
    sd = StringDesign()
    t = design_temperatures(sd, None, None, 19.3, 34.1, 30.2)
    # floor(19.3) − 5 = 14, not below the 14 °C setting; 34.1 + 30.2 = 64.3, not above 70
    assert t["t_cold_c"] == 14 and t["cold_source"] == "setting" and t["tmy_cold_c"] == 14 and t["t_hot_c"] == 70 and t["hot_source"] == "setting" and t["tmy_hot_cell_c"] == pytest.approx(64.3)
    t2 = design_temperatures(sd, None, None, 16.8, 38.0, 37.0)
    assert t2["t_cold_c"] == 11 and t2["cold_source"] == "tmy" and t2["t_hot_c"] == 75 and t2["hot_source"] == "tmy"
    # the project's own figure stands in for the setting: a record low typed lower wins, a typed hot figure above the cell's stands
    t3 = design_temperatures(sd, 9.0, 80.0, 19.3, 34.1, 30.2)
    assert t3["t_cold_c"] == 9 and t3["cold_source"] == "project" and t3["t_hot_c"] == 80 and t3["hot_source"] == "project" and t3["cold_setting_c"] == 9
    # without a TMY (the website estimate) the settings alone
    t4 = design_temperatures(sd, None, None, None, None, None)
    assert t4["t_cold_c"] == 14 and t4["t_hot_c"] == 70 and t4["tmy_min_air_c"] is None
    # the Faiman rise at 1 kW/m² with the PVGIS constants: 37.2 °C still, about 30 at 1 m/s
    assert faiman_rise_c_per_kw(26.9, 6.2, 0.0) == pytest.approx(37.17, abs=0.01) and faiman_rise_c_per_kw(26.9, 6.2, 1.0) == pytest.approx(30.21, abs=0.01)


def test_results_carry_the_site_figures_and_the_project_override(client):
    aid = client.post("/api/assessments", json=deepcopy(LAGUNA_DOC)).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    site = r.json()["results"]["site"]
    sd = StringDesign()
    assert site["tmy_min_air_c"] < site["tmy_max_air_c"] and site["rise_c_per_kw"] > 0 and site["rise_source"] in ("site", "faiman")
    assert site["t_cold_c"] == min(sd.design_cold_c, math.floor(site["tmy_min_air_c"]) - sd.cold_margin_c)
    assert site["t_hot_c"] == pytest.approx(max(sd.design_hot_cell_c, site["tmy_max_air_c"] + site["rise_c_per_kw"]))
    assert site["cold_setting_c"] == 14 and site["hot_setting_c"] == 70
    # the pricing carries the same two figures into the string design block
    ch = r.json()["results"]["pricing"]["choices"]
    assert ch["string_design"]["t_cold_c"] == site["t_cold_c"] and ch["string_design"]["t_hot_c"] == pytest.approx(site["t_hot_c"])
    doc = client.get(f"/api/assessments/{aid}").json()["doc"]
    doc["pricing"] = {"design_cold_c": 5, "design_hot_cell_c": 90}
    res = client.post(f"/api/assessments/{aid}/compute", json=doc).json()["results"]
    assert res["site"]["t_cold_c"] <= 5 and res["site"]["cold_setting_c"] == 5 and res["site"]["t_hot_c"] >= 90 and res["site"]["hot_source"] == "project"
    assert res["pricing"]["choices"]["string_design"]["t_cold_c"] == res["site"]["t_cold_c"]
