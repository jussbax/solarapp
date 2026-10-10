"""The uplift check (round 13, item 3; brief 3.5 to 3.7). Every figure below is a TEST INPUT, typed the way the signing
engineer and the office would type it, never a value the app ships: the app's defaults leave every wind and fastener
figure blank, and the check reads "not checked" until they are typed. The hand-worked case of 3.7: V = 200 km/h,
exposure B (α 7.0, zg 365.76 m), Kd 0.85, GCp −1.8, the 585 W panel 2.278 × 1.134 m at 32 kg, purlins at 0.6 m, feet
at 1.2 m, two screws per foot: 0.634 kN per screw; 1.5 kN pull-out passes (ratio 0.42); 0.5 kN closes the
feet to every purlin. The brief works Kz at the formula's 4.6 m floor (0.576, "the table's 0.57 at 0 to 4.6 m") while
naming h = 5 m; the engine follows the formula, 2.01 × (max(h, 4.6) / zg)^(2/α), which gives 0.590 at 5 m (the table's
interpolation between 0.57 at 15 ft and 0.62 at 20 ft), so the hand-worked case here takes h = 4.5 m and the 5 m figure
is asserted beside it. 0.5 kN closes the
feet to every purlin (five per 2.4 m rail, eight per 4.536 m line, 32 on the sample roof); exposure C gives Kz 0.849
and qh 1,365 N/m²; a blank V, GCp, purlin spacing, height or pull-out reads "not checked" naming it; the sample job's
BOM keeps its 24 L-feet without the figures."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.core.towns import provinces
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.pricing.boq import BoqRequest, RoofRow, generate_boq
from solarapp.pricing.catalog import Item
from solarapp.pricing.config import PricingConfig, WindZone, settings_version
from solarapp.pricing.importer import read_workbook
from solarapp.pricing.uplift import WIND_ZONES_FILE, apply_uplift, evaluate_face, kz_at, merged_construction, province_of, resolve_wind, uplift_block, velocity_pressure_pa, wind_zone_for
from solarapp.schemas import AssessmentDoc, RoofConstruction, RoofFace, WindInputs
from tests.test_drawings import PILA_DOC

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"

# ---- the test inputs of 3.7 (not the app's)
PANEL = Item(code="T-PNL", category="Solar Panel", supplier="t", name="585 W test panel", rating=585, rating_unit="W", weight_kg=32.0, weight_source="test", panel_length_m=2.278, panel_width_m=1.134)
WIND = {"v_kmh": 200, "v_source": "test input", "exposure": "B", "gcp_zone1": -1.0, "gcp_zone2": -1.4, "gcp_zone3": -1.8, "gcp_source": "test input"}
CONSTRUCTION = {"roof_type": "rib_metal", "sheet_profile": "rib 30 mm, pitch 250 mm", "purlin_material": "steel_c", "purlin_section": "C 100 × 50 × 1.5", "purlin_thickness_mm": 1.5,
                "purlin_spacing_m": 0.6, "mean_roof_height_m": 4.5, "condition_flag": "sound"}


def _cfg(pullout: float | None = 1.5, foot_max: float | None = 1.2, kd: float | None = 0.85, exposures: bool = True) -> PricingConfig:
    cfg = PricingConfig()
    m = cfg.mounting
    m.fastener_pullout_kn, m.fastener_pullout_source = pullout, "test input: the maker's sheet"
    m.fastener_description = "5.5 × 75 mm self-drilling screw with bonded EPDM washer"
    m.foot_spacing_max_m, m.foot_spacing_max_source = foot_max, "test input: the rail maker's manual"
    m.kd, m.kd_source = kd, "test input"
    if exposures:
        m.exposures["B"].alpha, m.exposures["B"].zg_m = 7.0, 365.76
        m.exposures["C"].alpha, m.exposures["C"].zg_m = 9.5, 274.32
        m.exposure_source = "test input"
    return cfg


def _doc(wind: dict | None = WIND, construction: dict | None = CONSTRUCTION) -> AssessmentDoc:
    return AssessmentDoc(lat=14.2335, lon=121.3645, faces=[RoofFace(id="f1", name="Main roof", length_m=9, width_m=5, construction=construction or {})], wind=wind or {})


def _face(doc: AssessmentDoc, cfg: PricingConfig, rows: list[RoofRow]) -> dict:
    face = doc.faces[0]
    wind = resolve_wind(doc.wind, province_of(doc.lat, doc.lon), cfg.mounting)
    return evaluate_face(face, merged_construction(face, doc.roof_default), wind, rows, PANEL, cfg)


def test_the_app_ships_no_wind_or_fastener_figure():
    m = PricingConfig().mounting
    assert m.fastener_pullout_kn is None and m.foot_spacing_max_m is None and m.kd is None and m.wind_zones == {} and m.rail_kg_per_m is None
    assert all(c.alpha is None and c.zg_m is None for c in m.exposures.values()) and set(m.exposures) == {"B", "C", "D"}
    w = WindInputs()
    assert w.v_kmh is None and w.exposure == "" and w.kzt is None and w.gcp_zone1 is w.gcp_zone2 is w.gcp_zone3 is None
    assert RoofConstruction().fastener_pullout_kn is None
    # the wind-zone file: every province of the town list, every figure blank, the figure named as the source
    data = json.loads(WIND_ZONES_FILE.read_text(encoding="utf-8"))
    assert set(data["provinces"]) == set(provinces()) and "207A.5-1A" in data["source"]
    assert all(row == {"zone": "", "v_kmh": None, "source": ""} for row in data["provinces"].values())
    assert wind_zone_for("Laguna", m)["status"] == "not set" and wind_zone_for(None, m)["status"] == "no pin"
    # a typed figure moves the settings version (it moves the L-foot count, so a priced job is flagged)
    cfg = PricingConfig()
    cfg.mounting.wind_zones["Laguna"] = WindZone(zone="II", v_kmh=200, source="test")
    assert settings_version(cfg) != settings_version(PricingConfig())


def test_the_chain_hand_worked_at_200_kmh():
    """3.7: Kz 0.576, qh 926 N/m², p_up 1.667 kPa, T_panel 2.39 kN, strip 1.139 m, T_foot 1.267 kN at 1.2 m, 0.634 kN per screw,
    pass at 1.5 kN (ratio 0.42), three feet per 2.4 m rail."""
    assert kz_at(4.5, 7.0, 365.76) == kz_at(4.6, 7.0, 365.76) == pytest.approx(0.576, abs=0.001)   # the floor: the table's 0.57 at 0 to 4.6 m
    assert kz_at(5, 7.0, 365.76) == pytest.approx(0.590, abs=0.001)          # above the floor the formula climbs (the table's 0.57 to 0.62 between 15 and 20 ft)
    assert velocity_pressure_pa(200 / 3.6, kz_at(4.6, 7.0, 365.76), 1.0, 0.85) == pytest.approx(926, abs=1)
    assert kz_at(4.6, 9.5, 274.32) == pytest.approx(0.849, abs=0.001)        # exposure C, the table's 0.85
    assert velocity_pressure_pa(200 / 3.6, kz_at(4.6, 9.5, 274.32), 1.0, 0.85) == pytest.approx(1365, abs=3)   # the brief's rounded Kz
    f = _face(_doc(), _cfg(pullout=1.5), [RoofRow(2, 1.134, 0.0, "f1")])   # two portrait panels: a 2.268 m line
    assert f["status"] == "pass" and f["detail"] == "A" and f["orientation"] == "portrait"
    assert f["v_ms"] == pytest.approx(55.56, abs=0.01) and f["kz"] == pytest.approx(0.576, abs=0.001) and f["qh_pa"] == pytest.approx(926, abs=1)
    assert f["p_up_kpa"] == pytest.approx(1.667, abs=0.002) and f["d_kpa"]["value"] == pytest.approx(0.1215, abs=0.001)
    assert f["t_panel_kn"] == pytest.approx(2.39, abs=0.01) and f["strip_m"]["value"] == pytest.approx(1.139)
    assert f["s_std_m"] == pytest.approx(1.2) and f["k_std"] == 2 and f["t_foot_std_kn"] == pytest.approx(1.267, abs=0.005)
    assert f["t_screw_std_kn"] == pytest.approx(0.634, abs=0.003) and f["ratio_std"] == pytest.approx(0.42, abs=0.01) and f["holds_std"] is True
    assert f["s_foot_m"] == pytest.approx(1.2) and f["t_screw_kn"] == pytest.approx(0.634, abs=0.003)
    # every typed figure carries its source; the two labelled assumptions (Kzt, the worst zone's GCp) and no other
    assert f["pullout_kn"] == {"value": 1.5, "source": "test input: the maker's sheet", "assumed": False, "note": "", "missing": None}
    assert any("Kzt" not in a and "no hill or ridge" in a for a in f["assumptions"]) and any("zone 3, -1.8" in a for a in f["assumptions"])
    assert not any("exposure B" in a for a in f["assumptions"])   # typed, so not an assumption here
    # the 2.268 m line takes two feet at 1.2 m; a 2.4 m rail piece three (the rule's count too)
    assert f["rows"][0]["feet_per_line"] == 2 and f["feet"] == 4 and f["screws"] == 8 and f["feet_per_rail"] == 3 and f["l_foot_rule"] == 6


def test_a_weak_fastener_closes_the_feet_to_every_purlin_and_a_hopeless_one_fails():
    """3.7: at 0.5 kN the 1.2 m spacing does not hold (0.634 per screw); s_allow = 1.0 / (0.927 × 1.139) = 0.947 m, so the feet
    sit on every purlin (0.6 m): five per 2.4 m rail, eight per 4.536 m line, 32 on the sample roof's four lines, and the
    check passes at that spacing. A pull-out below the every-purlin share fails, hard, printing, not blocking."""
    f = _face(_doc(), _cfg(pullout=0.5), [RoofRow(2, 1.134, 0.0, "f1")])
    assert f["status"] == "pass" and f["holds_std"] is False and f["t_screw_std_kn"] == pytest.approx(0.634, abs=0.003)
    assert f["s_allow_m"] == pytest.approx(0.947, abs=0.003) and f["s_foot_m"] == pytest.approx(0.6) and f["k_foot"] == 1
    assert f["t_screw_kn"] == pytest.approx(0.317, abs=0.002) and f["feet_per_rail"] == 5 and f["rows"][0]["feet_per_line"] == 4 and f["feet"] == 8
    assert any("close up to every 1st purlin" in n for n in f["notes"])
    sample = _face(_doc(), _cfg(pullout=0.5), [RoofRow(4, 1.134, 0.0, "f1"), RoofRow(4, 1.134, 0.0, "f1")])
    assert [r["feet_per_line"] for r in sample["rows"]] == [8, 8] and sample["feet"] == 32 and sample["l_foot_rule"] == 24
    # the same roof at 1.5 kN keeps the rule's 24 (feet at 1.2 m: floor(4.536 / 1.2) + 1 = 4 per line, 16 feet: fewer than the rule's, the rule's note says so)
    strong = _face(_doc(), _cfg(pullout=1.5), [RoofRow(4, 1.134, 0.0, "f1"), RoofRow(4, 1.134, 0.0, "f1")])
    assert strong["status"] == "pass" and strong["feet"] == 16 and strong["l_foot_rule"] == 24
    # 0.3 kN: even a foot on every purlin carries 0.317 kN per screw: FAIL, the hard warning, nothing blocks
    bad = _face(_doc(), _cfg(pullout=0.3), [RoofRow(2, 1.134, 0.0, "f1")])
    assert bad["status"] == "fail" and bad["s_foot_m"] == pytest.approx(0.6) and bad["t_screw_kn"] == pytest.approx(0.317, abs=0.002)
    w = next(w for w in bad["warnings"] if w["code"] == "uplift_fail")
    assert w["hard"] is True and not w.get("blocks_documents") and "0.32 kN" in w["message"] and "signing engineer" in w["message"]


def test_a_blank_input_reads_not_checked_and_names_it():
    cases = [
        ({**WIND, "v_kmh": None}, CONSTRUCTION, _cfg(), "basic wind speed V: not set for Laguna under Settings"),
        ({**WIND, "gcp_zone1": None, "gcp_zone2": None, "gcp_zone3": None}, CONSTRUCTION, _cfg(), "GCp per roof zone: not typed on the project"),
        (WIND, {**CONSTRUCTION, "purlin_spacing_m": None}, _cfg(), "purlin spacing not surveyed"),
        (WIND, {**CONSTRUCTION, "mean_roof_height_m": None}, _cfg(), "mean roof height h not surveyed"),
        (WIND, CONSTRUCTION, _cfg(pullout=None), "allowable withdrawal: not typed under Settings"),
        (WIND, CONSTRUCTION, _cfg(kd=None), "Kd (directionality"),
        (WIND, CONSTRUCTION, _cfg(exposures=False), "exposure B: alpha and zg not typed"),
    ]
    for wind, construction, cfg, reason in cases:
        f = _face(_doc(wind, construction), cfg, [RoofRow(2, 1.134, 0.0, "f1")])
        assert f["status"] == "not checked" and any(reason in m for m in f["missing"]), (reason, f["missing"])
        assert f["kz"] is None and f["t_screw_kn"] is None and f["feet"] is None and f["l_foot_rule"] == 6
    # the province's row under Settings stands in for the project's V; the project's own figure wins over it
    cfg = _cfg()
    cfg.mounting.wind_zones["Laguna"] = WindZone(zone="II", v_kmh=150, source="test: the settings row")
    f = _face(_doc({**WIND, "v_kmh": None}), cfg, [RoofRow(2, 1.134, 0.0, "f1")])
    assert f["status"] == "pass" and f["v_ms"] == pytest.approx(150 / 3.6)
    wind = resolve_wind(WindInputs(**{**WIND, "v_kmh": None}), "Laguna", cfg.mounting)
    assert wind["v_kmh"]["source"] == "test: the settings row" and wind["zone"] == "II"
    assert resolve_wind(WindInputs(**WIND), "Laguna", cfg.mounting)["v_kmh"]["value"] == 200
    # the blank exposure is the labelled assumption B; a typed C reads its own constants
    assert resolve_wind(WindInputs(**{**WIND, "exposure": ""}), "Laguna", cfg.mounting)["exposure"]["assumed"] is True
    c = resolve_wind(WindInputs(**{**WIND, "exposure": "C"}), "Laguna", cfg.mounting)
    assert c["alpha"]["value"] == 9.5 and c["zg_m"]["value"] == 274.32 and c["exposure"]["assumed"] is False


def test_the_roof_type_and_condition_warn_and_the_tile_and_deck_are_out_of_scope():
    f = _face(_doc(construction={**CONSTRUCTION, "roof_type": "concrete_deck"}), _cfg(), [RoofRow(2, 1.134, 0.0, "f1")])
    assert f["status"] == "not checked" and f["detail"] is None and any(w["code"] == "roof_type_out_of_scope" for w in f["warnings"])
    t = _face(_doc(construction={**CONSTRUCTION, "roof_type": "tile_clay"}), _cfg(), [RoofRow(2, 1.134, 0.0, "f1")])
    assert t["status"] == "not checked" and "owner's word" in t["missing"][0]
    c = _face(_doc(construction={**CONSTRUCTION, "roof_type": "corrugated_metal", "condition_flag": "rusted", "condition": "rust at the eave"}), _cfg(), [RoofRow(2, 1.134, 0.0, "f1")])
    assert c["status"] == "pass" and c["detail"] == "B"
    w = next(w for w in c["warnings"] if w["code"] == "roof_condition")
    assert w["hard"] is True and not w.get("blocks_documents") and "rusted (rust at the eave)" in w["message"]
    # a blank roof type runs the chain and says the detail is blank
    b = _face(_doc(construction={**CONSTRUCTION, "roof_type": ""}), _cfg(), [RoofRow(2, 1.134, 0.0, "f1")])
    assert b["status"] == "pass" and b["detail"] is None and any("not surveyed" in n for n in b["notes"])
    # a face's figures over the project's default, field by field
    doc = AssessmentDoc(faces=[RoofFace(id="f1", name="A", length_m=9, width_m=5, construction={"purlin_spacing_m": 0.9})], roof_default=CONSTRUCTION)
    m = merged_construction(doc.faces[0], doc.roof_default)
    assert m.purlin_spacing_m == 0.9 and m.roof_type == "rib_metal" and m.mean_roof_height_m == 4.5


@pytest.fixture(scope="module")
def imported():
    return read_workbook(WB)


def test_the_sample_jobs_l_foot_count_is_unchanged_without_the_figures(imported):
    """The round-3 sample job (8 × 585 W, two rows of four) keeps 24 L-feet and its lines: no figure is typed, so the check
    is not checked, the line's note says so, and the warning is ordinary."""
    cat, cfg = imported.catalog, imported.config
    rows = [RoofRow(4, 1.134, 0.0, "f1"), RoofRow(4, 1.134, 0.0, "f1")]
    res = generate_boq(BoqRequest("BC-PNL-004", 8, rows, inverter_kw=6, battery_kwh=11.7), cat, cfg)
    before = [(l.code, l.qty, l.role) for l in res.lines]
    block = apply_uplift(_doc(wind=None, construction=None), rows, cat.get("BC-PNL-004"), cfg, res)
    assert block["status"] == "not checked" and block["l_foot"] == {"rule": 24, "checked": None, "bom": 24, "note": block["l_foot"]["note"], "screws": None}
    assert [(l.code, l.qty, l.role) for l in res.lines] == before
    lf = next(l for l in res.lines if l.role == "l_foot")
    assert lf.qty == 24 and lf.note.startswith("3 per rail; the uplift check is not checked (")
    w = next(w for w in res.warnings if w["code"] == "uplift_not_checked")
    assert not w.get("hard") and not w.get("blocks_documents") and "basic wind speed V" in w["message"]
    assert res.choices["uplift"]["faces"][0]["name"] == "Main roof" and res.choices["uplift"]["province"] == "Laguna"
    # with the figures typed and a 0.5 kN pull-out the line moves to 32 and says why; at 1.5 kN it stays 24 (16 would do: the note says so)
    res2 = generate_boq(BoqRequest("BC-PNL-004", 8, rows, inverter_kw=6, battery_kwh=11.7), cat, cfg)
    block2 = apply_uplift(_doc(), rows, PANEL, _cfg(pullout=0.5), res2)
    lf2 = next(l for l in res2.lines if l.role == "l_foot")
    assert block2["status"] == "pass" and block2["l_foot"]["bom"] == 32 and lf2.qty == 32 and "feet on every purlin (0.6 m" in lf2.note and "would give 24" in lf2.note
    assert block2["l_foot"]["screws"] == 64
    res3 = generate_boq(BoqRequest("BC-PNL-004", 8, rows, inverter_kw=6, battery_kwh=11.7), cat, cfg)
    block3 = apply_uplift(_doc(), rows, PANEL, _cfg(pullout=1.5), res3)
    assert block3["status"] == "pass" and block3["l_foot"]["bom"] == 16 and next(l for l in res3.lines if l.role == "l_foot").qty == 16


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)  # Laguna
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def test_the_pila_record_through_the_api(client):
    """The sample record: not checked and the rule's 24 L-feet with nothing typed; with the wind and fastener figures typed
    under Settings and on the project, the check runs per face, the warnings print and none blocks, and the figures round-trip."""
    doc = deepcopy(PILA_DOC)
    aid = client.post("/api/assessments", json=doc).json()["id"]
    res = client.post(f"/api/assessments/{aid}/compute").json()["results"]
    up = res["pricing"]["choices"]["uplift"]
    rule = up["l_foot"]["rule"]
    assert up["status"] == "not checked" and up["province"] == "Laguna" and up["l_foot"]["bom"] == rule and up["l_foot"]["checked"] is None
    assert next(l for l in res["pricing"]["lines"] if l["role"] == "l_foot")["qty"] == rule == 3 * next(l for l in res["pricing"]["lines"] if l["role"] == "rail")["qty"]
    assert any(w["code"] == "uplift_not_checked" for w in res["pricing"]["warnings"]) and res["pricing"]["design_blocked"] == []
    cfg = client.get("/api/pricing/config").json()
    assert cfg["mounting"]["fastener_pullout_kn"] is None and cfg["mounting"]["wind_zones"] == {}
    cfg["mounting"].update({"fastener_pullout_kn": 0.5, "fastener_pullout_source": "test: the maker's sheet", "foot_spacing_max_m": 1.2, "foot_spacing_max_source": "test",
                            "kd": 0.85, "kd_source": "test", "exposure_source": "test", "wind_zones": {"Laguna": {"zone": "II", "v_kmh": 200, "source": "test: the figure"}}})
    cfg["mounting"]["exposures"]["B"] = {"alpha": 7.0, "zg_m": 365.76}
    saved = client.put("/api/pricing/config", json=cfg).json()
    assert saved["mounting"]["wind_zones"]["Laguna"]["v_kmh"] == 200 and saved["mounting"]["exposures"]["B"]["alpha"] == 7.0
    doc = client.get(f"/api/assessments/{aid}").json()["doc"]
    doc["wind"] = {"exposure": "B", "gcp_zone3": -1.8, "gcp_source": "test: the figure"}
    doc["roof_default"] = {**CONSTRUCTION, "fastener_pullout_kn": None}
    doc["faces"][0]["construction"] = {"purlin_spacing_m": 0.9, "condition_flag": "rusted", "condition": "rust at the gutter"}
    out = client.post(f"/api/assessments/{aid}/compute", json=doc).json()
    assert out["doc"]["wind"]["gcp_zone3"] == -1.8 and out["doc"]["faces"][0]["construction"]["purlin_spacing_m"] == 0.9
    res = out["results"]
    up = res["pricing"]["choices"]["uplift"]
    assert up["status"] == "pass" and up["wind"]["v_kmh"]["value"] == 200 and up["wind"]["v_kmh"]["source"] == "test: the figure"
    by = {f["name"]: f for f in up["faces"]}
    # the sized system sits on the main roof alone (the kitchen holds no rows, so no evaluation); its panels lie landscape (a 0.567 m
    # strip), its own 0.9 m purlins over the project's 0.6 m, the project's roof type: a foot on every purlin holds at 0.5 kN
    assert list(by) == ["Main roof (south)"]
    main = by["Main roof (south)"]
    assert main["orientation"] == "landscape" and main["strip_m"]["value"] == pytest.approx(0.567) and main["construction"]["roof_type"] == "rib_metal"
    assert main["purlin_spacing_m"]["value"] == 0.9 and main["s_foot_m"] == 0.9 and main["k_foot"] == 1 and main["h_m"]["value"] == 4.5
    assert next(l for l in res["pricing"]["lines"] if l["role"] == "l_foot")["qty"] == up["l_foot"]["bom"] == up["l_foot"]["checked"]
    codes = {w["code"] for w in res["pricing"]["warnings"]}
    assert "roof_condition" in codes and "uplift_not_checked" not in codes and res["pricing"]["design_blocked"] == []
    # the quick estimate never reaches the check
    import solarapp.core.quick as quick
    assert "uplift" not in Path(quick.__file__).read_text(encoding="utf-8")

def _pdf_pages(pdf: bytes) -> list[str]:
    import shutil
    import subprocess

    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    text = subprocess.run(["pdftotext", "-layout", "-", "-"], input=pdf, capture_output=True, check=True).stdout.decode()
    return [p for p in text.split("\f") if p.strip()]


def test_the_sheet_prints_the_chain_with_its_sources_and_the_verdict(client):
    """The mounting detail sheet (brief 3.3 to 3.6): the two details, the callouts, the chain per face with every typed figure
    beside its source, the labelled assumptions, PASS; FAIL in the fail case; NOT CHECKED with the blanks when nothing is
    typed, and the last sheet then lists the inputs; the wind-zone file through the API."""
    flat = lambda s: " ".join(s.split())  # noqa: E731
    zones = client.get("/api/pricing/wind-zones").json()
    assert set(zones["provinces"]) == set(provinces()) and zones["provinces"]["Laguna"] == {"zone": "", "v_kmh": None, "source": ""}
    assert client.post("/api/pricing/config/reset").status_code == 200
    aid = client.post("/api/assessments", json=deepcopy(PILA_DOC)).json()["id"]
    assert client.post(f"/api/assessments/{aid}/compute").status_code == 200
    pages = _pdf_pages(client.get(f"/api/assessments/{aid}/plans.pdf").content)
    sheet = next(p for p in pages if "Standard details" in p)
    assert "Detail A: rib-type metal sheet on steel C-purlins, 1:5" in sheet and "Detail B: corrugated sheet on purlins, 1:5" in sheet
    assert "NOT CHECKED" in sheet and "not set for Laguna" in flat(sheet) and "not typed on the project" in flat(sheet)
    assert "Plan key" in sheet and "Rail: 12 pc" in flat(sheet) and "L-foot: 36 pc" in flat(sheet) and "(not checked)" in sheet
    assert "Uplift check inputs" in flat(pages[-1]) and "Not checked: basic wind speed V" in flat(pages[-1])
    assert "): feet on every" not in flat(sheet) and "FAIL: even" not in flat(sheet)
    # the figures typed as test inputs (never the app's): PASS with every source printed, the feet on every 2nd purlin, 24 L-feet
    cfg = client.get("/api/pricing/config").json()
    cfg["mounting"].update({"fastener_description": "5.5 × 75 mm screw, EPDM washer (test)", "fastener_pullout_kn": 0.5, "fastener_pullout_source": "test: the screw maker's sheet",
                            "foot_spacing_max_m": 1.2, "foot_spacing_max_source": "test: the rail manual", "kd": 0.85, "kd_source": "test: Table 207A.6-1",
                            "exposure_source": "test: Table 207A.9-1", "wind_zones": {"Laguna": {"zone": "II", "v_kmh": 200, "source": "test: Fig. 207A.5-1A"}}})
    cfg["mounting"]["exposures"]["B"] = {"alpha": 7.0, "zg_m": 365.76}
    assert client.put("/api/pricing/config", json=cfg).status_code == 200
    doc = client.get(f"/api/assessments/{aid}").json()["doc"]
    doc["wind"] = {"gcp_zone3": -1.8, "gcp_source": "test: Fig. 207E.4-2A"}
    doc["roof_default"] = CONSTRUCTION
    assert client.post(f"/api/assessments/{aid}/compute", json=doc).status_code == 200
    pages = _pdf_pages(client.get(f"/api/assessments/{aid}/plans.pdf").content)
    sheet = flat(next(p for p in pages if "Standard details" in p))
    # pdftotext's layout mode interleaves the columns' lines, so each fragment is one line's worth
    for text in ("200 km/h = 55.56 m/s; zone II, Laguna", "source: test: Fig. 207A.5-1A", "B (assumption: exposure B, a town site", "alpha 7, zg 365.76 m", "207A.9-1)",
                 "0.576", "926 N/m²", "0.85 (source: test: Table 207A.6-1)", "-1.8 (assumption: the worst typed zone's figure (zone 3, -1.8)", "source: test: Fig. 207E.4-2A",
                 "1.667 kPa", "PASS", "every 2nd purlin (1.2 m)", "24 feet, 48 screws", "the BOQ rule's 36", "S = 1.2 m (every 2nd purlin)", "5.5 × 75 mm screw, EPDM washer (test)",
                 "C 100 × 50 × 1.5, steel C-purlin", "1 (assumption: 1.0, no hill or ridge"):
        assert text in sheet, text
    assert "inputs blank (the blank lines above" not in sheet and "FAIL: even" not in sheet and "Uplift check inputs" not in flat(pages[-1])
    cover = flat(pages[0])
    assert "3. Mounting." in cover and "PASS, 24 L-feet on the BOM" in cover
    # a 0.1 kN figure fails even with a foot on every purlin: FAIL on the sheet, the rule's count on the BOM, nothing blocks
    cfg["mounting"]["fastener_pullout_kn"] = 0.1
    assert client.put("/api/pricing/config", json=cfg).status_code == 200
    res = client.post(f"/api/assessments/{aid}/compute", json=client.get(f"/api/assessments/{aid}").json()["doc"]).json()["results"]
    assert res["pricing"]["choices"]["uplift"]["status"] == "fail" and res["pricing"]["design_blocked"] == []
    assert next(l for l in res["pricing"]["lines"] if l["role"] == "l_foot")["qty"] == 36
    sheet = flat(next(p for p in _pdf_pages(client.get(f"/api/assessments/{aid}/plans.pdf").content) if "Standard details" in p))
    assert "FAIL: even a foot on every purlin" in sheet and "ratio 3.20" in sheet and "L-feet on the BOM: 36" in sheet
    client.post("/api/pricing/config/reset")
