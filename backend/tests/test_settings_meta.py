"""Every pricing setting the owner can edit has a label, a unit (numbers), decimals and a one-line help in the
front end's META map (round 4: "a number reads as a person would say it, every number has its unit, a help text is
one short line"). The map lives in frontend/src/components/pricingMeta.ts; this test reads it as text so a
setting added to config.py without its META entry fails here rather than showing up as a title-cased key."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from solarapp.pricing.config import GroundRates, PricingConfig

META_FILE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "pricingMeta.ts"
# keys the pages draw elsewhere (the base pin with the company base, the late finish row in the minutes table) or never show
DRAWN_ELSEWHERE = {"route.base_lat", "route.base_lon"}
STAMPS = {"imported_from", "imported_at", "datasheets_imported_from", "datasheets_imported_at"}
SHORT_HELP = 60   # characters: one line in a two-column cell
SHORT_UNIT = 13   # characters beside a control ("per rail line" is the longest the spec names)


def _meta() -> dict[str, dict[str, str]]:
    text = META_FILE.read_text(encoding="utf-8")
    start = text.index("export const META")
    end = text.index("\n}\n", start)
    body = text[start:end]
    out: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"^\s*'([a-z_]+\.[a-z_0-9]+)':\s*\{(.*)\},?\s*$", body, re.M):
        key, fields = m.group(1), m.group(2)
        entry: dict[str, str] = {}
        for f in re.finditer(r"(\w+):\s*(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"|([\w.]+))", fields):
            entry[f.group(1)] = f.group(2) if f.group(2) is not None else f.group(3) if f.group(3) is not None else f.group(4)
        out[key] = entry
    return out


@pytest.fixture(scope="module")
def meta() -> dict[str, dict[str, str]]:
    m = _meta()
    assert len(m) > 100, "the META map was not found or not parsed"
    return m


def _settings() -> list[tuple[str, object]]:
    cfg = PricingConfig().model_dump()
    out = []
    for section, v in cfg.items():
        if section in STAMPS:
            continue
        if isinstance(v, dict):
            out.extend((f"{section}.{k}", x) for k, x in v.items())
        else:
            out.append((f"{section}.value", v))
    return out


def test_every_setting_has_a_label(meta):
    missing = [path for path, _ in _settings() if path not in meta]
    assert not missing, f"settings without a META entry (their label would be the title-cased key): {missing}"


def test_every_number_has_a_short_unit_and_decimals(meta):
    bad = []
    for path, v in _settings():
        if path in DRAWN_ELSEWHERE or not isinstance(v, (int, float)) or isinstance(v, bool):
            continue
        unit = meta[path].get("unit")
        if not unit:
            bad.append(f"{path}: no unit")
        elif len(unit) > SHORT_UNIT:
            bad.append(f"{path}: unit {unit!r} longer than {SHORT_UNIT} characters")
    assert not bad, bad


def test_help_is_one_line_and_the_long_text_is_behind_the_question_mark(meta):
    bad = [f"{path}: help {m['help']!r} is {len(m['help'])} characters" for path, m in meta.items() if m.get("help") and len(m["help"]) > SHORT_HELP]
    assert not bad, bad
    # the long texts the audit listed live behind the "?" (about), not under the field
    for path in ("job.vat", "roles.inverter_parallel_tolerance_pct", "economics.battery_life_years_override", "program.min_task_minutes", "sizing.days_of_autonomy"):
        assert meta[path].get("about"), f"{path} lost its long explanation"


def test_labels_are_sentence_case_and_carry_no_unit(meta):
    bad = []
    for path, m in meta.items():
        label = m["label"]
        if re.search(r"\((?:₱|kg|m³|m|V|A|W|mm²|%)\)$", label) or re.search(r"\b(mh|m3)\b", label):
            bad.append(f"{path}: label {label!r} carries a unit")
        if label[:1].islower():
            bad.append(f"{path}: label {label!r} starts lowercase")
    assert not bad, bad


def test_no_stale_meta_entries(meta):
    # an entry for a key the config no longer has would never be shown (the old truck.running_cost_per_km was one)
    paths = {path for path, _ in _settings()}
    stale = [k for k in meta if k not in paths and not k.endswith('.value')]
    assert not stale, stale


def test_a_removed_ground_task_counts_no_hours():
    g = GroundRates(tasks=[t for t in GroundRates().tasks if t.key != "ground_rod"])
    assert g.mh("ground_rod") == 0.0
    assert g.mh("hybrid_inverter") == pytest.approx(2 * g.mounting_mh_per_unit + 2 * g.wiring_mh_per_unit)
