"""The engine must reproduce the workbook's sample job: 5 kWp / 6 kW / 11.7 kWh hybrid, P329,300."""
from pathlib import Path

import pytest

from solarapp.pricing.engine import BomLine, JobInputs, freight_for, labor_for, landed_cost, price_job, price_lines, takeoff_from_lines
from solarapp.pricing.importer import read_workbook

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"

SAMPLE_BOM = [
    ("BC-PNL-004", 8), ("FS-INV-001", 1), ("FS-BAT-006", 1), ("BC-MNT-001", 8), ("BC-MNT-006", 24), ("BC-MNT-003", 8),
    ("BC-MNT-004", 12), ("BC-MNT-005", 4), ("BC-WIR-001", 15), ("BC-WIR-002", 15), ("IAN-WIR-004", 35), ("OP-WIR-007", 2),
    ("IAN-WIR-026", 4), ("IAN-PRT-009", 2), ("IAN-PRT-018", 1), ("IAN-PRT-003", 1), ("OP-PRT-035", 1), ("IAN-PRT-027", 4),
    ("IAN-PRT-035", 4), ("OP-ENC-007", 2), ("OP-ENC-009", 1), ("IAN-ENC-011", 30), ("OP-GND-001", 1), ("IAN-GND-001", 4), ("IAN-CSM-001", 2),
]


@pytest.fixture(scope="module")
def imported():
    return read_workbook(WB)


def test_import_counts_and_config(imported):
    assert imported.item_count == 362 and imported.supplier_count == 4
    cfg = imported.config
    assert cfg.truck.running_cost_per_km == pytest.approx(17.2857142857)
    assert cfg.handling.typical_job_cost == 750 and cfg.handling.typical_fill == pytest.approx(0.144482896668418)
    assert cfg.category("Battery").markup_tier == 0.15 and cfg.category("Wires and Terminations").wastage == 0.05
    assert cfg.route.stops[0] == "Pila base" and cfg.route.km[0][1] == 110 and cfg.route.toll[0][1] == 1110
    assert cfg.ground.hybrid_pace == pytest.approx(0.375001547634115)
    assert cfg.mobdemob.crew_transport_per_day == 800 and cfg.tools.charge_per_installation_day == pytest.approx(905.624978858076)
    assert cfg.job.services_markup == 0.3 and cfg.job.lgu_permit_cfei == 5000 and cfg.job.erc_coc_fee == 1500
    panel = imported.catalog.get("BC-PNL-001")
    assert panel.panel_length_m == 2.278 and panel.panel_width_m == 1.134
    assert imported.catalog.get("BC-WIR-001").list_price == 46.5  # formula cell read as value
    assert all(code in imported.catalog.items for code in imported.config.roles.thhn.values())


def test_landed_costs_match_workbook(imported):
    cat, cfg = imported.catalog, imported.config
    lc = landed_cost(cat.get("BC-PNL-001"), cat, cfg)
    assert lc.truck_share == pytest.approx(0.00866666666666667)
    assert lc.handling == pytest.approx(44.9880238414462)
    assert lc.landed == pytest.approx(4994.98802384145)
    assert landed_cost(cat.get("BC-PNL-004"), cat, cfg).landed == pytest.approx(5497.92954847723)
    assert landed_cost(cat.get("FS-BAT-006"), cat, cfg).landed == pytest.approx(87192.0642556308)
    assert landed_cost(cat.get("IAN-CSM-001"), cat, cfg).landed == pytest.approx(330.60560801325)  # 10% wastage
    assert landed_cost(cat.get("IAN-WIR-004"), cat, cfg).landed == pytest.approx(94.6782217867565)


def test_sample_job_reproduces_329300(imported):
    cat, cfg = imported.catalog, imported.config
    bom = [BomLine(c, q) for c, q in SAMPLE_BOM]
    lines = price_lines(bom, cat, cfg)
    assert sum(l.landed for l in lines) == pytest.approx(207458.821216027)
    assert sum(l.markup for l in lines) == pytest.approx(31753.6709367143)
    t = takeoff_from_lines(lines)
    assert (t.panels, t.hybrid_inverters, t.gridtie_inverters, t.battery_packs) == (8, 1, 0, 1)
    assert t.heaviest_pack_kg == 111 and t.enclosures == 2 and t.protective_devices == 13
    assert t.conduit_m == 32 and t.wire_m == 65 and t.mc4_pairs == 4 and t.ground_rods == 1
    fr = freight_for(lines, cat, cfg)
    assert fr.stops_on_run == ["IAN Solar", "Felicity Solar", "One Point", "Blue Carbon"]
    assert fr.loop_km == 235 and fr.toll == 2220 and fr.run_cost == pytest.approx(17282.1428571429)
    assert fr.truck_share == pytest.approx(0.144716230001751) and fr.trips == 1
    job = JobInputs(roof_factor=0.75, roof_closed_days=1, max_days=2, max_pairs=2, battery_haul_hours=0.5, net_metering=True)
    lb = labor_for(t, cfg, job)
    assert lb.total_mh == pytest.approx(15.8643722245762)
    assert lb.carry_crew == 4 and lb.pairs == 1 and lb.days == 1 and lb.persons == 4
    assert lb.labor == 6500 and lb.mobdemob == 1300 and lb.tools == pytest.approx(905.624978858076)
    res = price_job(bom, cat, cfg, job)
    tot = res["totals"]
    assert tot["direct"] == pytest.approx(244346.589052027)
    assert tot["markup"] == pytest.approx(37377.6798589431)
    assert tot["commission"] == pytest.approx(12217.3294526014)
    assert tot["contract"] == pytest.approx(329214.590167201)
    assert tot["contract_rounded"] == 329300
    assert tot["kwp"] == pytest.approx(5.04) and tot["price_per_wp"] == pytest.approx(65.3373015873016)
    assert tot["ocm"] == pytest.approx(18688.8399294716)
    cust = res["customer"]
    assert sum(s["amount"] for s in cust["sections"]) == pytest.approx(329300)
    assert [s["key"] for s in cust["sections"]] == ["materials", "labor", "equipment", "tax"]
    assert cust["sections"][2]["amount"] == pytest.approx(905.62 * 1.3 * (1 + 0.05 / (1 + (37377.68 / 244346.59))), rel=0.02)  # tools with services markup and its commission share
    for sec in cust["sections"]:  # category lines add up to the section
        assert sec["items"] and sum(i["amount"] for i in sec["items"]) == pytest.approx(sec["amount"])
    mat = cust["sections"][0]["items"]
    assert [i["key"] for i in mat] == ["Solar Panel", "Inverter", "Battery", "Mounting", "Wires and Terminations", "Protective Devices", "Enclosures and Raceways", "Grounding", "Consumables"]
    assert mat[0]["qty"] == 8 and mat[0]["name"].startswith("Solar panels: 8 ×") and mat[3]["unit"] == "lot"
    assert {i["key"] for i in cust["sections"][1]["items"]} >= {"seal", "permit", "erc", "meter"}  # the permit lines sit under Installation and permits
    assert [s["label"] for s in cust["sections"]] == ["Materials", "Installation and permits", "Installation tools", "VAT (12%)"]
    assert [i["key"] for i in cust["sections"][1]["items"]] == ["labor", "mobdemob", "ppe", "seal", "permit", "erc", "meter"]
    assert cust["sections"][2]["items"][0]["qty"] == res["labor"]["days"]


def test_crew_options_and_far_site(imported):
    cat, cfg = imported.catalog, imported.config
    bom = [BomLine(c, q) for c, q in SAMPLE_BOM]
    # a far site adds km to the truck run and to crew transport each day
    res = price_job(bom, cat, cfg, JobInputs(extra_km=40, extra_toll=200))
    assert res["freight"]["loop_km"] == 235 + 80 and res["freight"]["toll"] == 2420
    assert res["labor"]["mobdemob"] == pytest.approx(1300 + 1 * (2 * 40 * 12 + 200))
    # a big job needs more pairs or days
    big = [BomLine("BC-PNL-004", 30), BomLine("FS-INV-002", 1), BomLine("FS-BAT-003", 2)] + [BomLine(c, q) for c, q in SAMPLE_BOM[3:]]
    lb = labor_for(takeoff_from_lines(price_lines(big, cat, cfg)), cfg, JobInputs(max_days=1, max_pairs=3))
    assert lb.pairs >= 1 and lb.days == 1 and lb.carry_crew == 5


def test_vat_is_twelve_percent_of_the_rounded_contract_and_labels_follow_the_settings(imported):
    """Finance 9 and 14: the customer's VAT is worked out on the rounded, VAT-inclusive contract (VAT = total x rate / (1 + rate)),
    the base is the rest, the rounding pesos sit on the crew line, and the VAT labels come from the setting, not a literal."""
    cat, cfg = imported.catalog, imported.config
    bom = [BomLine(c, q) for c, q in SAMPLE_BOM]
    res = price_job(bom, cat, cfg, JobInputs())
    cust, tot = res["customer"], res["totals"]
    rounded = tot["contract_rounded"]
    assert cust["total"] == rounded == 329300
    assert cust["vat"] == pytest.approx(rounded * 0.12 / 1.12)
    assert cust["subtotal_ex_vat"] == pytest.approx(rounded - cust["vat"])
    assert cust["subtotal_ex_vat"] * 0.12 == pytest.approx(cust["vat"])   # "VAT, 12% of the amounts above", to the peso
    secs = {s["key"]: s for s in cust["sections"]}
    assert secs["materials"]["amount"] + secs["labor"]["amount"] + secs["equipment"]["amount"] == pytest.approx(cust["subtotal_ex_vat"])
    assert secs["tax"]["amount"] == pytest.approx(cust["vat"]) and sum(s["amount"] for s in cust["sections"]) == pytest.approx(rounded)
    # the rounding pesos (85.41 on this job, VAT inside) sit on the crew line and nowhere else
    crew, labor_line = secs["labor"]["items"][0], res["build_up"][2]
    assert crew["key"] == "labor" and labor_line["key"] == "labor"
    rounding = rounded - tot["contract"]
    assert rounding == pytest.approx(329300 - 329214.590167201)
    assert crew["amount"] - (labor_line["selling"] + tot["commission"] * labor_line["direct"] / tot["direct"]) == pytest.approx(rounding / 1.12, abs=0.01)
    # the internal build-up stays the workbook's: VAT on the unrounded contract (JOB!B121)
    assert tot["vat"] == pytest.approx(tot["contract_ex_vat"] * 0.12)
    assert cust["vat_rate"] == 0.12 and cust["vat_label"] == "VAT (12%)"
    # another rate: the labels and the arithmetic follow it
    cfg10 = cfg.model_copy(deep=True)
    cfg10.job.vat = 0.10
    c10 = price_job(bom, cat, cfg10, JobInputs())["customer"]
    tax10 = next(s for s in c10["sections"] if s["key"] == "tax")
    assert tax10["label"] == "VAT (10%)" and tax10["items"][0]["name"] == "VAT, 10% of the amounts above" and c10["vat_label"] == "VAT (10%)"
    assert c10["vat"] == pytest.approx(c10["total"] * 0.10 / 1.10) and c10["subtotal_ex_vat"] * 0.10 == pytest.approx(c10["vat"])


def test_roof_closed_in_zero_days_prices_as_one_day(imported):
    """Finance 8: the workbook's #DIV/0! case. The schema reads 0 as 1 and the engine floors it, so the job prices."""
    from solarapp.schemas import PricingJob

    assert PricingJob(roof_closed_days=0).roof_closed_days == 1
    assert PricingJob(roof_closed_days=2).roof_closed_days == 2 and PricingJob().roof_closed_days is None
    with pytest.raises(ValueError):
        PricingJob(roof_closed_days=-1)
    cat, cfg = imported.catalog, imported.config
    bom = [BomLine(c, q) for c, q in SAMPLE_BOM]
    zero = price_job(bom, cat, cfg, JobInputs(roof_closed_days=0))
    one = price_job(bom, cat, cfg, JobInputs(roof_closed_days=1))
    assert zero["totals"]["contract_rounded"] == one["totals"]["contract_rounded"] == 329300
    assert zero["labor"]["detail"]["min_pairs"] == one["labor"]["detail"]["min_pairs"] == 1


def test_settings_version_moves_only_with_settings_that_move_a_price(imported):
    """Finance 1: the fingerprint a priced project stores. Any setting behind a price, the program or the savings moves it;
    the website estimate's own knobs, the import stamp and the company label do not."""
    from solarapp.pricing.config import settings_version

    cfg = imported.config
    v = settings_version(cfg)
    assert len(v) == 16 and v == settings_version(cfg.model_copy(deep=True))
    moved = cfg.model_copy(deep=True)
    moved.job.services_markup = 0.35
    assert settings_version(moved) != v
    tier = cfg.model_copy(deep=True)
    tier.category("Battery").markup_tier = 0.20
    assert settings_version(tier) != v
    eco = cfg.model_copy(deep=True)
    eco.economics.replacement_labor_php = 500
    assert settings_version(eco) != v
    same = cfg.model_copy(deep=True)
    same.quick.max_requests_per_hour = 99
    same.imported_at = "2030-01-01T00:00:00"
    same.company_base = "elsewhere"
    assert settings_version(same) == v
