"""The maker's datasheet workbooks into the app (round 12, docs/audits/round-12/engineer-brief.md).

    python -m solarapp.pricing.datasheets <files…> [--dry-run] [--report out.csv] [--apply-held]

Three workbooks (panels, inverters, batteries), told apart by the header words of each sheet, never by the file name.
Every sheet row becomes a row of `datasheet_specs` (never deleted; a re-run upserts by category, model and brand) and
is matched to a material item in three tiers, exact, contains and base (brief, section 2.2). The figures then go on
the item under the precedence of section 2.4: the owner's edit on the Materials page > the datasheet > the materials
workbook's electrical column > the remark inference; the same figures are re-applied at the end of every materials
import, because the workbook import writes the remark inference back over the item's electrical fields.

Nothing on a sheet is corrected. An irregular cell is parsed by the rule of section 1.5, the row carries a notice, and
where the brief says so the figure is held back (section 6: the Solis grid-tie rows' battery figures, a battery
maximum above 1 C) until the owner answers; `--apply-held` applies them all, the Materials page applies them per row,
and the owner's word is kept on the row (held_applied_at) through every later run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import openpyxl
from sqlmodel import Session, select

from ..models import Assessment, DatasheetSpec, MaterialItem, MaterialSupplier, utcnow
from .catalog import ELECTRICAL_FIELDS, ELECTRICAL_TEXT_FIELDS, Item, certifications_in_remarks, electrical_from_remarks, infer_grid_interactive
from .importer import ELECTRICAL_HEADERS, _norm_header

KIND_LABEL = {"Solar Panel": "panels", "Inverter": "inverters", "All-in-one System": "inverters", "Battery": "batteries"}
# how far an item's rating may sit from the sheet's before the import says so (the item's figure stands either way; 1.1–1.3)
RATING_TOLERANCE = {"Solar Panel": 0.005, "Inverter": 0.005, "All-in-one System": 0.02, "Battery": 0.02}
# the header words that tell a sheet's kind (5.1); a header row carries at least three of its kind's words
PANEL_WORDS = {"brand", "modelcapacity", "model", "pmax", "vmp", "imp", "voc", "isc", "maxdcsystemvoltage"}
BATTERY_WORDS = {"batterytype", "model", "brand", "nominalvoltage", "voltage", "capacity", "energycapacity", "energyrating", "maxchargevoltage",
                 "maxdischargecurrent", "recommendeddischargecurrent", "maxrecommendedchargecurrent", "detailsspecs"}
INVERTER_WORDS = {"typesofinverter", "model", "miodel", "brand", "detailsspecs", "maxchargevoltage", "recommendeddischargecurrent", "maxrecommendedchargecurrent"}
# the sheet's own column names → the parser's keys (the electrical aliases of the materials workbook come on top)
PANEL_COLUMNS = {"brand": "brand", "modelcapacity": "model", "model": "model", "pmax": "pmax", "vmp": "vmp", "imp": "imp", "voc": "voc", "isc": "isc",
                 "maxdcsystemvoltage": "max_system", "maxsystemvoltage": "max_system"}
INVERTER_COLUMNS = {"typesofinverter": "type", "type": "type", "model": "model", "miodel": "model", "brand": "brand", "detailsspecs": "details",
                    "details": "details", "specs": "details", "maxchargevoltage": "charge_v", "recommendeddischargecurrent": "discharge_a",
                    "maxrecommendedchargecurrent": "charge_a"}
BATTERY_COLUMNS = {"batterytype": "chemistry", "model": "model", "brand": "brand", "nominalvoltage": "nominal_v", "voltage": "nominal_v",
                   "capacity": "capacity", "energycapacity": "energy", "energyrating": "energy", "detailsspecs": "details",
                   "maxchargevoltage": "charge_v", "maxdischargecurrent": "max_discharge_a", "recommendeddischargecurrent": "discharge_a",
                   "maxrecommendedchargecurrent": "charge_a"}
# the type column (1.4): inverter_type, phase, grid_interactive (None = unknown)
INVERTER_TYPES: dict[str, tuple[str, Optional[int], Optional[bool]]] = {
    "gridtie1p": ("grid_tie", 1, True), "gridtie3p": ("grid_tie", 3, True), "gridtie": ("grid_tie", None, True),
    "hybrid1p": ("hybrid", 1, True), "hybrid3p": ("hybrid", 3, True), "hybrid": ("hybrid", None, True),
    "offgrid": ("off_grid", None, False), "offgridgridtie": ("hybrid", None, None),
    "chargecontrollersmppt": ("charge_controller", None, False), "chargecontroller": ("charge_controller", None, False),
    "commercialessinverterbatteryset": ("ess_set", 3, None), "commercialess": ("ess_set", 3, None),
}
# the words that are a maker, never part of a model code: stripped from the front of a panel model text (2.2)
EXTRA_MAKER_WORDS = ("solar",)
NUMBER = re.compile(r"\d+(?:\.\d+)?")
RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*V?\s*(?:–|—|-|to)\s*(\d+(?:\.\d+)?)\s*V?", re.I)
DUAL = re.compile(r"(\d+(?:\.\d+)?)\s*A\s*\+\s*(\d+(?:\.\d+)?)\s*A", re.I)
THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
SLASH_ALTERNATIVES = re.compile(r"(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)+)([A-Za-z]+)")
BOUNDARY_BEFORE = " ,;/("
BOUNDARY_AFTER = " ,;/)"


# ---------------------------------------------------------------- text helpers

def norm(s: Any) -> str:
    """Upper case, letters and digits only: hyphens, spaces, dots, parentheses and slashes vanish, so a model typed
    with a space before its last letter equals the same model typed without."""
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def _clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v if v is not None else "")).strip()


def _plain(v: Any) -> str:
    """The cell as typed with thousands commas removed ("1,000V" → "1000V")."""
    return THOUSANDS.sub("", _clean(v))


def _brand_words(brand: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", brand.lower()) if w not in EXTRA_MAKER_WORDS and w not in ("inc", "co", "ltd")]


def _brand_in(brand: str, text: str) -> bool:
    words = _brand_words(brand)
    low = text.lower()
    return bool(words) and all(re.search(rf"\b{re.escape(w)}\b", low) for w in words)


# ---------------------------------------------------------------- one cell

@dataclass
class Parsed:
    """A figure as the sheet typed it: the number the rule takes, what the rule noticed, and the flags that name
    the irregularity (approximate, asterisk, range, no_battery, held…)."""
    value: Optional[float] = None
    notices: list[str] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)
    extra: dict[str, Any] = field(default_factory=dict)


def parse_measure(text: Any, unit: str = "") -> Parsed:
    """A plain figure: "40.50 V" → 40.5, "585W" → 585. A leading "~" (1.1) parses to the number and flags approximate."""
    s = _plain(text)
    p = Parsed()
    if not s:
        return p
    if "~" in s:
        p.flags.add("approximate")
        p.notices.append(f"{unit or 'figure'} {s!r} is marked approximate on the datasheet; verify before the plans are sealed")
    m = NUMBER.search(s)
    if m:
        p.value = float(m.group())
    return p


def parse_system_voltage(text: Any) -> Parsed:
    """"1500V DC" → 1500; two figures with a slash ("600V DC / 1000V DC") → the lower, the conservative bound for the string check (1.1)."""
    s = _plain(text)
    p = Parsed()
    if not s:
        return p
    nums = [float(x) for x in NUMBER.findall(s)]
    if "/" in s and len(nums) >= 2:
        p.value = min(nums)
        p.flags.add("two_ratings")
        p.notices.append(f"two system-voltage ratings on the sheet ({s}); the lower, {p.value:g} V, is used; verify which applies to the unit sold")
    elif nums:
        p.value = nums[0]
    return p


def parse_inverter_charge_voltage(text: Any) -> Parsed:
    """The inverter's Max Charge Voltage (1.2): "N/A (No Battery Input)" is a fact, a narrow range (< 5 V) takes the
    lower figure as the conservative maximum, a wide range the upper with the low end kept here, "Varies by BMS /
    Up to 800V" takes 800 with a notice."""
    s = _plain(text)
    low = s.lower()
    p = Parsed()
    if not s:
        return p
    if "no battery input" in low:
        p.flags.add("no_battery")
        return p
    if low in ("n/a", "na", "-"):
        p.flags.add("na")
        return p
    if "varies by bms" in low:
        nums = [float(x) for x in NUMBER.findall(s)]
        p.value = nums[-1] if nums else None
        p.flags.add("varies_bms")
        p.notices.append(f"max charge voltage {s!r}: varies by BMS; {p.value:g} V is used; verify per battery")
        return p
    r = RANGE.search(s)
    if r:
        lo, hi = float(r.group(1)), float(r.group(2))
        p.flags.add("range")
        p.extra["range"] = [lo, hi]
        if hi - lo < 5:
            p.value = lo
            p.notices.append(f"max charge voltage range {lo:g}–{hi:g} V is narrower than 5 V: the lower figure, {lo:g} V, is the maximum used (the pair is kept here)")
        else:
            p.value = hi
            p.notices.append(f"max charge voltage range {lo:g}–{hi:g} V: the upper figure, {hi:g} V, is the maximum; the low end {lo:g} V is kept here as the window's low end (no check uses it yet)")
        return p
    m = NUMBER.search(s)
    p.value = float(m.group()) if m else None
    return p


def parse_battery_charge_voltage(text: Any) -> Parsed:
    """The battery's MAX CHARGE VOLTAGE (1.3): a range takes the upper figure as the ceiling; the lower is kept here as
    the discharge floor (assumption: on a LiFePO4 pack the lower figure of the range is the cut-off; no check uses it)."""
    s = _plain(text)
    p = Parsed()
    if not s:
        return p
    r = RANGE.search(s)
    if r:
        lo, hi = float(r.group(1)), float(r.group(2))
        p.value = hi
        p.flags.add("range")
        p.extra["range"] = [lo, hi]
        p.notices.append(f"max charge voltage range {lo:g}–{hi:g} V: the upper figure, {hi:g} V, is the ceiling; the lower, {lo:g} V, is kept here as the discharge floor "
                         "(assumption: on a LiFePO4 pack the lower figure of a voltage range is the cut-off; no check uses it)")
        return p
    m = NUMBER.search(s)
    p.value = float(m.group()) if m else None
    return p


def parse_current(text: Any, column: str, no_battery: bool = False) -> Parsed:
    """A current column (1.2, 1.3): "250A" → 250; an asterisk is flagged; "80A + 80A" is the per-input figure of a
    two-input port; "NO DISCHARGE OUTPUT" and "N/A" are blank (a notice only when the row has a battery port);
    "Verify" is blank with its notice; a kW figure in an amps column is never read as amps (6.3)."""
    s = _plain(text)
    low = s.lower()
    p = Parsed()
    if not s:
        return p
    if "no discharge output" in low:
        p.flags.add("no_output")
        return p
    if low in ("n/a", "na", "-"):
        p.flags.add("na")
        if not no_battery:
            p.notices.append(f"{column} is N/A on the sheet")
        return p
    if low == "verify":
        p.flags.add("verify")
        p.notices.append(f"{column} is marked Verify on the sheet")
        return p
    if re.search(r"\d\s*kw\b", low):
        p.flags.add("kw_in_amps")
        p.notices.append(f"{column}: a kW figure ({s}) in the charge-current column; asked of the owner (6.3); left blank, never converted to amps")
        return p
    d = DUAL.search(s)
    if d:
        a, b = float(d.group(1)), float(d.group(2))
        p.value = a
        p.flags.add("dual")
        p.extra["inputs"] = 2
        p.notices.append(f"{column}: two battery inputs on the datasheet ({s}); the per-input figure {a:g} A is stored; the circuit rule prices one circuit and says to verify")
        if b != a:
            p.notices.append(f"{column}: the two inputs differ ({a:g} A and {b:g} A); the first is stored")
        return p
    if "*" in s:
        p.flags.add("asterisk")
        p.notices.append(f"{column} {s!r} is marked with an asterisk on the sheet; the condition is not on the sheet; verify")
    if "up to" in low:
        p.flags.add("up_to")
    m = NUMBER.search(s)
    if not m:
        p.notices.append(f"{column} {s!r} carries no figure")
        return p
    p.value = float(m.group())
    tail = re.sub(r"^[^A-Za-z]*A\b\*?", "", s[m.end():].strip(), count=1).strip(" *")
    if tail and "up to" not in low:
        p.flags.add("word")
        p.notices.append(f"{column}: the sheet says {s!r}; {p.value:g} A is used and the word is kept here")
    return p


def parse_kw(details: Any) -> Optional[float]:
    """The first number followed by kW in the details ("8 kW", "0.48 Kw-12V", "12 kW; List says '12W' - typo"): the kW
    match comes first, so "12W" is never read as a rating. "Commercial" has none."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*kw\b", _plain(details), re.I)
    return float(m.group(1)) if m else None


def parse_mppt(details: Any) -> Optional[tuple[int, float, str]]:
    """"MPPT 18/36/36A" → (3 inputs, 18 A the smallest, "18/36/36"); the smallest figure is the conservative single
    value because every input must hold its own strings (1.2)."""
    m = re.search(r"MPPT\s*((?:\d+(?:\.\d+)?/)+\d+(?:\.\d+)?)\s*A", _plain(details), re.I)
    if not m:
        return None
    parts = [float(x) for x in m.group(1).split("/")]
    return len(parts), min(parts), "/".join(f"{x:g}" for x in parts)


def parse_kwh(text: Any) -> Optional[float]:
    """The first kWh figure not marked "~" ("16 kWh; … ~16.1 kWh" → 16; "3.83kWh" → 3.83)."""
    for m in re.finditer(r"(~?)\s*(\d+(?:\.\d+)?)\s*kwh", _plain(text), re.I):
        if not m.group(1):
            return float(m.group(2))
    return None


def parse_battery_details(details: Any) -> dict[str, Optional[float]]:
    """Battery sheet 3's details cell: the V, Ah and first kWh figures ("48 V; 100 Ah; 4.8 kWh")."""
    s = _plain(details)
    v = re.search(r"(\d+(?:\.\d+)?)\s*V\b", s)
    ah = re.search(r"(\d+(?:\.\d+)?)\s*Ah\b", s, re.I)
    return {"nominal_v": float(v.group(1)) if v else None, "capacity_ah": float(ah.group(1)) if ah else None, "kwh": parse_kwh(s)}


def inverter_type_of(text: Any) -> tuple[str, Optional[int], Optional[bool]]:
    """The type column → (inverter_type, phase, grid_interactive) per the table of 1.4; unknown text → blanks."""
    key = re.sub(r"[^a-z0-9]", "", _clean(text).lower())
    if key in INVERTER_TYPES:
        return INVERTER_TYPES[key]
    for k, v in INVERTER_TYPES.items():
        if key.startswith(k):
            return v
    return "", None, None


def phase_from_details(details: Any) -> Optional[int]:
    """"380V", "380-400V", "400V", "440-480V", "480V" → 3; "230V" → 1 (1.4); blank otherwise."""
    s = _plain(details)
    if re.search(r"\b(380(?:-400)?|400|440-480|480)\s*V\b", s):
        return 3
    if re.search(r"\b(220-)?230\s*V\b", s):
        return 1
    return None


def class_of_voltage(v: Optional[float]) -> Optional[Any]:
    """12 if V ≤ 16, 24 if ≤ 32, 48 if ≤ 64, else HV (3.7); applied to a nominal voltage and to a charge ceiling alike."""
    if v is None:
        return None
    return 12 if v <= 16 else 24 if v <= 32 else 48 if v <= 64 else "HV"


def battery_class_of_text(text: Any) -> str:
    low = _clean(text).lower()
    if "high" in low and "volt" in low:
        return "HV"
    if ("low" in low and "volt" in low) or "12v" in low or "24v" in low or "48v" in low:
        return "LV"
    if "hv battery" in low:
        return "HV"
    if "lv battery" in low:
        return "LV"
    return ""


def battery_class_of_voltage(v: Optional[float]) -> str:
    c = class_of_voltage(v)
    return "" if c is None else ("HV" if c == "HV" else "LV")


# ---------------------------------------------------------------- one sheet row

@dataclass
class SheetRow:
    category: str
    brand: str
    model: str
    source_file: str
    source_sheet: str
    source_row: int
    brand_in_model: str = ""
    fields: dict[str, Any] = field(default_factory=dict)
    held_fields: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    notices: list[str] = field(default_factory=list)
    held: bool = False
    skipped: str = ""                 # the reason a row has no specs row
    matched_code: Optional[str] = None
    match_tier: str = ""
    match_note: str = ""

    @property
    def model_norm(self) -> str:
        return norm(self.model)

    @property
    def where(self) -> str:
        return f"{KIND_LABEL.get(self.category, self.category)} {self.source_sheet.lower().replace(' ', '')} row {self.source_row}"

    @property
    def maker(self) -> str:
        return self.brand_in_model or self.brand


def _rating_fields(value: Optional[float], unit: str) -> dict:
    return {"rating": value, "rating_unit": unit} if value is not None else {}


def parse_panel_row(cells: dict[str, Any], brands: set[str], where: tuple[str, str, int]) -> SheetRow:
    brand = _clean(cells.get("brand"))
    model = _clean(cells.get("model"))
    row = SheetRow("Solar Panel", brand, model, *where, raw={k: _clean(v) for k, v in cells.items() if v not in (None, "")})
    # the maker's words come off the front of the model text (2.2): "maker + code + watts" must match an item named "code + watts"
    stripped, maker = strip_maker(model, brands)
    row.model = stripped
    if maker and norm(maker) != norm(brand):
        row.brand_in_model = maker
        row.notices.append(f"the brand column says {brand!r} and the model text names {maker!r}; matched on the maker in the text (6.1)")
    p = parse_measure(cells.get("pmax"), "Pmax")
    row.fields.update(_rating_fields(p.value, "W"))
    row.notices += p.notices
    for key, fld, unit in (("vmp", "vmp_v", "Vmp"), ("imp", "imp_a", "Imp"), ("voc", "voc_v", "Voc"), ("isc", "isc_a", "Isc")):
        q = parse_measure(cells.get(key), unit)
        if q.value is not None:
            row.fields[fld] = q.value
        row.notices += q.notices
    sv = parse_system_voltage(cells.get("max_system"))
    if sv.value is not None:
        row.fields["max_system_voltage_v"] = sv.value
    row.notices += sv.notices
    _extra_electrical(row, cells)
    return row


def strip_maker(model: str, brands: Iterable[str]) -> tuple[str, str]:
    """"JA Solar JAM66D45 630W" → ("JAM66D45 630W", "JA Solar"); "AIKO Solar ABC 665W Bifacial" → ("ABC 665W Bifacial", "AIKO Solar")."""
    names = sorted({b.strip() for b in brands if b and b.strip()}, key=len, reverse=True)
    low = model.lower()
    for b in names:
        bl = b.lower()
        if low.startswith(bl + " ") and len(low) > len(bl) + 1:
            rest = model[len(b):].strip()
            maker = b
            for w in EXTRA_MAKER_WORDS:
                if rest.lower().startswith(w + " ") and not bl.endswith(w):
                    maker = f"{b} {rest[:len(w)]}"
                    rest = rest[len(w):].strip()
            return rest, maker
        # a brand that is "<maker> Solar" also matches the maker alone ("Aiko" for "AIKO Solar …")
        for w in EXTRA_MAKER_WORDS:
            if bl.endswith(" " + w) and low.startswith(bl[: -len(w) - 1] + " "):
                core = b[: -len(w) - 1]
                rest = model[len(core):].strip()
                if rest.lower().startswith(w + " "):
                    rest = rest[len(w):].strip()
                return rest, b
    return model, ""


def _extra_electrical(row: SheetRow, cells: dict[str, Any]) -> None:
    """Columns the owner may add later (6.5, 6.6: temperature coefficients, the MPPT window), read through the
    materials importer's alias table so the same words work in either workbook."""
    for fld, v in cells.items():
        if fld.startswith("elec:") and v not in (None, ""):
            name = fld[5:]
            try:
                row.fields[name] = _clean(v) if name in ELECTRICAL_TEXT_FIELDS else float(_plain(v).split()[0])
            except ValueError:
                row.notices.append(f"{name}: {_clean(v)!r} is not a number")


def parse_inverter_row(cells: dict[str, Any], where: tuple[str, str, int]) -> SheetRow:
    brand = _clean(cells.get("brand"))
    model = _clean(cells.get("model"))
    details = _clean(cells.get("details"))
    itype, phase, grid = inverter_type_of(cells.get("type"))
    category = "All-in-one System" if itype == "ess_set" else "Inverter"
    row = SheetRow(category, brand, model, *where, raw={k: _clean(v) for k, v in cells.items() if v not in (None, "")})
    f = row.fields
    if itype:
        f["inverter_type"] = itype
    elif _clean(cells.get("type")):
        row.notices.append(f"type {_clean(cells.get('type'))!r} is not one of the sheet's types; left unknown")
    if phase is None:
        phase = phase_from_details(details)
    if phase is not None:
        f["phase"] = phase
    f["grid_interactive"] = grid          # applied only when the item's flag is None (2.4)
    if itype != "ess_set":
        kw = parse_kw(details)
        f.update(_rating_fields(kw, "kW"))
    mppt = parse_mppt(details)
    if mppt:
        f["mppt_count"], f["mppt_max_a"], f["mppt_currents_a"] = mppt
    cls = battery_class_of_text(details)
    cv = parse_inverter_charge_voltage(cells.get("charge_v"))
    no_battery = "no_battery" in cv.flags
    row.notices += cv.notices
    if no_battery:
        cls = "none"
    elif not cls and cv.value is not None and itype in ("charge_controller", "off_grid"):
        cls = battery_class_of_voltage(cv.value)
    if cls:
        f["battery_class"] = cls
    battery_figs: dict[str, Any] = {}
    if cv.value is not None:
        battery_figs["charge_v_max"] = cv.value
    da = parse_current(cells.get("discharge_a"), "recommended discharge current", no_battery)
    ca = parse_current(cells.get("charge_a"), "max recommended charge current", no_battery)
    row.notices += da.notices + ca.notices
    if da.value is not None:
        battery_figs["battery_max_a"] = da.value
    if ca.value is not None:
        battery_figs["charge_a_max"] = ca.value
    inputs = da.extra.get("inputs") or ca.extra.get("inputs")
    if inputs:
        battery_figs["battery_inputs"] = inputs
    # the dash voltage after the kW in the details ("-12V", "-48V"): the battery class on One Solar and Blue Carbon rows,
    # cross-checked against the charge voltage; on the Felicity rows (230, 380, 720 V) it cannot be the class (6.8)
    dash = re.search(r"\d\s*kw\s*-\s*(\d+(?:\.\d+)?)\s*V\b", details, re.I)
    if dash:
        dv = float(dash.group(1))
        if dv in (12, 24, 48):
            if cv.value is not None and class_of_voltage(cv.value) != dv:
                row.notices.append(f"the details say a {dv:g} V battery and the max charge voltage {cv.value:g} V is a {class_of_voltage(cv.value)} V class figure; one of the two is for another unit (6.8)")
        else:
            row.notices.append(f"the voltage after the dash in the details ({dv:g} V) cannot be the battery class; left in the raw text; asked in 6.8")
    if re.search(r"\(\s*\d+\s*A\s*\)", details):
        row.notices.append(f"{re.search(r'\(\s*\d+\s*A\s*\)', details).group()} in the details is unexplained (6.8)")
    if itype == "grid_tie" and battery_figs:
        # a grid-tie unit has no battery port; figures in those columns are held until the owner answers 6.4 (1.5)
        row.held = True
        row.held_fields.update(battery_figs)
        if cls and cls != "none":
            row.held_fields["battery_class"] = cls
            f.pop("battery_class", None)
        row.notices.append("battery figures on a grid-tie unit; held, not applied to the item until the owner answers 6.4")
    else:
        f.update(battery_figs)
    _extra_electrical(row, cells)
    return row


def parse_battery_row(cells: dict[str, Any], class_text: Any, where: tuple[str, str, int]) -> SheetRow:
    brand_raw = _clean(cells.get("brand"))
    brand = brand_raw.split("(")[0].strip() if "(" in brand_raw else brand_raw     # "JK (One Solar)" → JK: the maker
    model = _clean(cells.get("model"))
    row = SheetRow("Battery", brand, model, *where, raw={k: _clean(v) for k, v in cells.items() if v not in (None, "")})
    if _clean(class_text):
        row.raw["class"] = _clean(class_text)
    f = row.fields
    cls = battery_class_of_text(class_text)
    if cls:
        f["battery_class"] = cls
    details = _clean(cells.get("details"))
    if details:
        d = parse_battery_details(details)
        nominal_v, capacity_ah, kwh = d["nominal_v"], d["capacity_ah"], d["kwh"]
    else:
        nominal_v = parse_measure(cells.get("nominal_v"), "nominal voltage").value
        capacity_ah = parse_measure(cells.get("capacity"), "capacity").value
        kwh = parse_kwh(cells.get("energy"))
    if nominal_v is not None:
        f["nominal_v"] = nominal_v
    else:
        row.notices.append("no nominal voltage on the sheet; the Ah–kWh check is skipped")
    if capacity_ah is not None:
        f["capacity_ah"] = capacity_ah
    f.update(_rating_fields(kwh, "kWh"))
    if re.search(r"\d+\s*[x×]\s*\d+\s*Ah", model, re.I):
        row.notices.append("the pack is a series stack (the model text says how many modules); the Ah stored is the module's, as typed")
    cv = parse_battery_charge_voltage(cells.get("charge_v"))
    row.notices += cv.notices
    if cv.value is not None:
        f["charge_v_max"] = cv.value
    mx = parse_current(cells.get("max_discharge_a"), "max discharge current")
    rd = parse_current(cells.get("discharge_a"), "recommended discharge current")
    ca = parse_current(cells.get("charge_a"), "max recommended charge current")
    row.notices += mx.notices + rd.notices + ca.notices
    if mx.value is not None:
        if capacity_ah and mx.value > capacity_ah + 1e-9:
            # a maximum above 1 C would lift a hard block if it were a peak figure: held until the owner confirms (1.3, 3.9)
            row.held = True
            row.held_fields["continuous_a"] = mx.value
            row.notices.append(f"max discharge current {mx.value:g} A is above 1 C ({mx.value / capacity_ah:.1f} C on {capacity_ah:g} Ah); verify it is a continuous rating, not a peak; held, not applied to the item")
        else:
            f["continuous_a"] = mx.value
    if rd.value is not None:
        f["discharge_a_recommended"] = rd.value
        if mx.value is not None and rd.value > mx.value + 1e-9:
            row.notices.append(f"the recommended discharge current ({rd.value:g} A) is above the maximum ({mx.value:g} A); which column is the BMS limit? the maximum is used (6.8)")
    if ca.value is not None:
        f["charge_a_max"] = ca.value
    # the class against the nominal voltage, and the ceiling against the nominal (6.8)
    if cls and nominal_v is not None and battery_class_of_voltage(nominal_v) != cls:
        row.notices.append(f"typed {cls} and the nominal voltage {nominal_v:g} V is a {battery_class_of_voltage(nominal_v)} figure; one of the two is for another pack (6.8)")
    if nominal_v is not None and cv.value is not None:
        ratio = cv.value / nominal_v
        if class_of_voltage(nominal_v) != class_of_voltage(cv.value):
            row.notices.append(f"a {nominal_v:g} V pack with a {cv.value:g} V max charge voltage: the ceiling is of another class; one of the two is for another pack (6.8)")
        elif ratio > 1.3:
            row.notices.append(f"the max charge voltage {cv.value:g} V is {ratio:.1f}× the nominal {nominal_v:g} V, which no LiFePO4 pack does; one of the two figures is for another pack (6.8)")
    # Ah–kWh consistency (3.8): a notice at import; the job warns when it prices the unit
    if nominal_v is not None and capacity_ah is not None and kwh:
        calc = nominal_v * capacity_ah / 1000.0
        dev = abs(calc - kwh) / kwh
        if dev > 0.02:
            row.notices.append(f"{nominal_v:g} V × {capacity_ah:g} Ah = {calc:.2f} kWh against the {kwh:g} kWh on the sheet ({dev * 100:.1f} %); one of the three figures is wrong; verify")
    _extra_electrical(row, cells)
    return row


# ---------------------------------------------------------------- the workbook

def _header_kind(keys: list[str]) -> Optional[str]:
    """Which kind's header row this is, by its words (5.1): panels (PMAX and VOC), batteries (BATTERY TYPE, Capacity
    and Energy, or MAX DISCHARGE CURRENT, which no inverter sheet has), inverters (TYPES OF INVERTER, or MODEL with
    Max Charge Voltage). Never the file name."""
    ks = set(keys)
    if {"pmax", "voc"} <= ks and len(ks & PANEL_WORDS) >= 3:
        return "Solar Panel"
    if ("batterytype" in ks or "maxdischargecurrent" in ks or ("capacity" in ks and ks & {"energycapacity", "energyrating"})) and len(ks & BATTERY_WORDS) >= 3:
        return "Battery"
    if ("typesofinverter" in ks or (ks & {"model", "miodel"} and "maxchargevoltage" in ks)) and len(ks & INVERTER_WORDS) >= 3:
        return "Inverter"
    return None


def read_datasheet_workbook(path: str | Path, source_name: Optional[str] = None, brands: Optional[set[str]] = None) -> list[SheetRow]:
    """Every row of every sheet as a SheetRow; a row without a model is a SheetRow with `skipped` set. The header row is
    found by its words on every sheet; battery sheet 3's maker sub-headers are header rows and reset the column map."""
    path = Path(path)
    wb = openpyxl.load_workbook(path, data_only=True)
    source = source_name or path.name
    rows: list[SheetRow] = []
    known_brands: set[str] = set(brands or set())
    pending_panels: list[tuple[dict, tuple]] = []
    for ws in wb.worksheets:
        kind: Optional[str] = None
        colmap: dict[int, str] = {}
        class_col: Optional[int] = None
        for r_idx, cells in enumerate(ws.iter_rows(values_only=True), start=1):
            keys = [_norm_header(c) for c in cells]
            header_kind = _header_kind([k for k in keys if k])
            if header_kind:
                same_kind = header_kind == kind
                kind = header_kind
                table = PANEL_COLUMNS if kind == "Solar Panel" else BATTERY_COLUMNS if kind == "Battery" else INVERTER_COLUMNS
                # a maker sub-header (battery sheet 3) resets the map but leaves some headers blank ("Details / specs"):
                # those columns keep the sheet's earlier mapping
                previous = colmap if same_kind else {}
                colmap = {i: name for i, name in previous.items() if i < len(keys) and not keys[i]}
                for i, k in enumerate(keys):
                    if not k:
                        continue
                    if k in table and table[k] not in colmap.values():
                        colmap[i] = table[k]
                    else:
                        for fld, aliases in ELECTRICAL_HEADERS.items():
                            if k in aliases and fld not in ("battery_max_a", "charge_a_max", "charge_v_max", "capacity_ah", "nominal_v", "discharge_a_recommended", "inverter_type"):
                                colmap[i] = f"elec:{fld}"
                # the LV/HV column has no header: the column left of BATTERY TYPE (sheets 1–2), else of MODEL (sheet 3's class text)
                if kind == "Battery":
                    by_name = {v: i for i, v in colmap.items()}
                    class_col = (by_name["chemistry"] - 1) if "chemistry" in by_name else (by_name["model"] - 1 if "model" in by_name else None)
                continue
            if kind is None or not colmap:
                continue
            values = {name: cells[i] if i < len(cells) else None for i, name in colmap.items()}
            if all(v in (None, "") for v in cells):
                continue
            model = _clean(values.get("model"))
            where = (source, ws.title, r_idx)
            if not model:
                text = "; ".join(_clean(v) for v in cells if v not in (None, ""))
                skipped = SheetRow(kind, _clean(values.get("brand")), "", *where, raw={"text": text}, skipped="no model in the model column")
                rows.append(skipped)
                continue
            if kind == "Solar Panel":
                known_brands.add(_clean(values.get("brand")))
                pending_panels.append((values, where))
            elif kind == "Battery":
                class_text = cells[class_col] if class_col is not None and 0 <= class_col < len(cells) else None
                rows.append(parse_battery_row(values, class_text, where))
                known_brands.add(_clean(values.get("brand")).split("(")[0].strip())
            else:
                rows.append(parse_inverter_row(values, where))
                known_brands.add(_clean(values.get("brand")))
    for values, where in pending_panels:
        rows.append(parse_panel_row(values, known_brands, where))
    rows.sort(key=lambda r: (r.source_sheet, r.source_row))
    return rows


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- matching (2.2)

def _collapse(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _occurs_whole(model: str, text: str) -> bool:
    """The raw model text occurs in the raw item text, spaces collapsed, case-insensitive, bounded on both sides by
    the end, a space, a comma, a semicolon, a slash or a parenthesis: never inside a longer code
    ("BCT-V-48-100" is not "SMART-BCT-V-48-100", "IVEM6048" is not "IVEM6048-II")."""
    m, t = _collapse(model), _collapse(text)
    if not m or not t:
        return False
    start = 0
    while True:
        i = t.find(m, start)
        if i < 0:
            return False
        before = t[i - 1] if i > 0 else " "
        after = t[i + len(m)] if i + len(m) < len(t) else " "
        if before in BOUNDARY_BEFORE and after in BOUNDARY_AFTER:
            return True
        start = i + 1


def _alternatives(text: str) -> list[str]:
    """An item name that lists alternatives with a slash ("40A ONE MPPT - 12/24/48V") is read once per alternative."""
    m = SLASH_ALTERNATIVES.search(text)
    if not m:
        return [text]
    parts, unit = m.group(1).split("/"), m.group(2)
    return [text] + [text[: m.start()] + p + unit + text[m.end():] for p in parts]


def _item_texts(item: Item) -> list[str]:
    out = _alternatives(item.name)
    if item.spec:
        out.append(item.spec)
    return out


def _tokens(item: Item) -> list[str]:
    return [t for t in re.split(r"[ ,;/()]+", f"{item.name} {item.spec}") if t]


def _model_token(item: Item) -> str:
    """The item's own model token: the first comma-separated segment of the spec, else the name."""
    src = (item.spec or "").split(",")[0].strip() or item.name
    return src


def _brand_filter(row: SheetRow, cands: list[Item]) -> list[Item]:
    """The tie-breaker inside a tier: the sheet's brand (or the maker in the model text) against the item's name,
    spec and supplier; the category is already the sheet's."""
    if len(cands) <= 1:
        return cands
    for brand in (row.brand_in_model, row.brand):
        if not brand:
            continue
        kept = [i for i in cands if _brand_in(brand, f"{i.name} {i.spec} {i.supplier}")]
        if kept:
            return kept
    return cands


def match_rows(rows: list[SheetRow], items: dict[str, Item], taken: Optional[dict[str, str]] = None) -> None:
    """Three tiers in order, each row taking at most one item and each item at most one row (2.2). `taken` maps the
    codes already matched (by earlier runs or manual links) to the row key that holds them. Sets matched_code,
    match_tier and match_note on every row; a row that finds nothing says why."""
    taken = dict(taken or {})
    open_rows = [r for r in rows if not r.skipped and r.matched_code is None]
    by_cat: dict[str, list[Item]] = {}
    for it in items.values():
        by_cat.setdefault(it.category, []).append(it)

    def take(row: SheetRow, item: Item, tier: str, note: str) -> None:
        row.matched_code, row.match_tier, row.match_note = item.code, tier, note
        taken[item.code] = f"{row.source_file}:{row.source_sheet}:{row.source_row}"

    # tier 1, exact: collect every row's exact candidates, then settle the items two rows claim (the longer model wins)
    exact: dict[str, list[SheetRow]] = {}
    row_cands: dict[int, list[Item]] = {}
    for row in open_rows:
        cands = [it for it in by_cat.get(row.category, []) if any(_occurs_whole(row.model, t) for t in _item_texts(it))]
        cands = _brand_filter(row, cands)
        row_cands[id(row)] = cands
        if len(cands) == 1:
            exact.setdefault(cands[0].code, []).append(row)
        elif len(cands) > 1:
            row.match_note = "ambiguous: " + ", ".join(sorted(i.code for i in cands))
    for code, claimants in exact.items():
        if code in taken:
            for r in claimants:
                r.match_note = f"{code} is already matched to another datasheet row ({taken[code]})"
            continue
        longest = max(len(r.model) for r in claimants)
        winners = [r for r in claimants if len(r.model) == longest]
        if len(winners) == 1:
            w = winners[0]
            others = [r for r in claimants if r is not w]
            note = "verbatim in the item" if not others else "the longer of two models the item names; the other row (" + ", ".join(r.model for r in others) + ") stays specs-only"
            take(w, items[code], "exact", note)
            for r in others:
                r.match_note = f"{code} names this model too, but takes the longer {w.model!r}; link by hand if this is the unit sold"
        else:
            for r in claimants:
                r.match_note = f"one item ({code}) stands for {len(claimants)} sheet rows of the same length; specs-only until the owner says which (6.7)"
    # tier 2, contains: a one-word model begins an item token; a multi-word text is a substring of the normalised name and spec
    for row in open_rows:
        if row.matched_code or row.match_note:
            continue
        nm = row.model_norm
        if len(nm) < 4:
            continue
        if " " in row.model.strip():
            cands = [it for it in by_cat.get(row.category, []) if nm in norm(f"{it.name} {it.spec}")]
        else:
            cands = [it for it in by_cat.get(row.category, []) if any(norm(t).startswith(nm) and norm(t) != nm for t in _tokens(it))]
        cands = _brand_filter(row, cands)
        if len(cands) == 1:
            it = cands[0]
            if it.code in taken:
                row.match_note = f"{it.code} contains this model but is already matched to another datasheet row ({taken[it.code]})"
            else:
                take(row, it, "contains", "the item's spec carries a suffix the sheet row lacks; verify it is the unit sold")
        elif len(cands) > 1:
            row.match_note = "ambiguous: " + ", ".join(sorted(i.code for i in cands))
    # tier 3, base: the item's own model token is a prefix of the sheet's model, and exactly one row extends it
    for cat, cat_items in by_cat.items():
        for it in cat_items:
            if it.code in taken:
                continue
            tok = norm(_model_token(it))
            if len(tok) < 6 or not re.search(r"\d", tok):
                continue
            extending = [r for r in open_rows if r.category == cat and not r.matched_code and not r.match_note and r.model_norm.startswith(tok) and r.model_norm != tok]
            extending = [r for r in extending if not r.brand or _brand_in(r.brand, f"{it.name} {it.spec} {it.supplier}") or not _brand_words(r.brand)]
            if len(extending) == 1:
                take(extending[0], it, "base", "the sheet's model extends the item's model by a suffix; verify it is the unit sold")
            elif len(extending) > 1:
                for r in extending:
                    r.match_note = f"{it.code} is the base of {len(extending)} sheet rows (" + ", ".join(x.model for x in extending) + "); specs-only until the owner says which"
    # what is left: the clash with another category, else plain specs-only
    for row in open_rows:
        if row.matched_code or row.match_note:
            continue
        other = [it for cat, its in by_cat.items() if cat != row.category for it in its if any(_occurs_whole(row.model, t) for t in _item_texts(it))]
        row.match_note = (f"matches {other[0].code} of category {other[0].category!r}, not the sheet's {row.category!r}; specs-only" if other
                          else "no item in the materials list names this model")


# ---------------------------------------------------------------- applying the figures (2.4)

def _same(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)
    return a == b


def _fmt(v: Any) -> str:
    if v is None or v == "":
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def apply_spec(item: MaterialItem, spec: DatasheetSpec, apply_held: bool = False) -> tuple[list[str], list[str]]:
    """The spec row's figures onto its item under the precedence of 2.4. Returns the changes as "field old -> new"
    and the notes the apply raised (a rating that differs, a grid flag kept). A field the owner typed over
    (overridden_fields) is left alone; a held figure is applied only with apply_held."""
    changes: list[str] = []
    notes: list[str] = []
    figures = dict(spec.fields)
    # the held figures go on once the owner has said so (held_applied_at, kept on the row through every later run) or on --apply-held
    apply_held = apply_held or bool(spec.held_applied_at)
    if apply_held:
        figures.update(spec.held_fields or {})
    overridden = set(spec.overridden_fields or [])
    # the rating: fill when blank; both present and apart by more than the tolerance → the item's stands, said once
    rating, unit = figures.pop("rating", None), figures.pop("rating_unit", None)
    if rating is not None:
        if not item.rating:
            changes.append(f"rating - -> {_fmt(rating)} {unit}")
            item.rating, item.rating_unit = float(rating), unit or item.rating_unit
        elif (item.rating_unit or "").lower() != (unit or "").lower():
            notes.append(f"the sheet rates it in {unit} and the item in {item.rating_unit or '?'}; the item's rating stands")
        elif abs(float(item.rating) - float(rating)) / float(item.rating) > RATING_TOLERANCE.get(item.category, 0.02):
            notes.append(f"the item's rating is {_fmt(item.rating)} {item.rating_unit} and the sheet says {_fmt(rating)} {unit}; the item's rating stands (it is the price base)")
    # the grid flag: the type fills it only when the item's is None; a disagreement is reported, the item stands
    grid = figures.pop("grid_interactive", None)
    if grid is not None:
        if item.grid_interactive is None:
            # the owner's remark that says to check the certification keeps the flag unknown on purpose (catalog.infer_grid_interactive):
            # the sheet's "Hybrid" is one word about a family, the remark is the owner's note about this unit (review finding 1)
            if re.search(r"check[^.]*certif", item.remarks or "", re.I):
                notes.append("grid flag left unknown: the item's remark says to check the certification")
            else:
                item.grid_interactive = bool(grid)
                changes.append(f"grid_interactive - -> {_fmt(bool(grid))}")
        elif item.grid_interactive != bool(grid):
            notes.append(f"grid_interactive kept (item {_fmt(item.grid_interactive)}, sheet {spec.fields.get('inverter_type', '?').replace('_', '-')})")
    for fld, new in figures.items():
        if fld not in ELECTRICAL_FIELDS or fld in ("certifications", "has_transfer_switch"):
            continue
        if fld in overridden:
            continue
        if fld in ("mppt_count", "phase", "battery_inputs") and new is not None:
            new = int(new)
        old = getattr(item, fld, None)
        if _same(old, new):
            continue
        setattr(item, fld, new)
        changes.append(f"{fld} {_fmt(old)} -> {_fmt(new)}")
    if changes:
        item.updated_at = utcnow()
    return changes, notes


def note_overrides(session: Session, code: str, patch: dict[str, Any]) -> None:
    """The owner typed over a field on the Materials page: when the item has a datasheet row and the new value is not
    the datasheet's, the field joins overridden_fields and the next run leaves it alone; typing the datasheet's own
    figure back ("reset to datasheet") takes it off the list."""
    spec = session.exec(select(DatasheetSpec).where(DatasheetSpec.matched_code == code)).first()
    if spec is None:
        return
    overridden = set(spec.overridden_fields or [])
    for k, v in patch.items():
        if k not in spec.fields or k in ("rating", "rating_unit", "grid_interactive"):
            continue
        if _same(spec.fields[k], v):
            overridden.discard(k)
        else:
            overridden.add(k)
    if set(spec.overridden_fields or []) != overridden:
        spec.overridden_fields = sorted(overridden)
        session.add(spec)
        session.commit()


# ---------------------------------------------------------------- the run

@dataclass
class ReportLine:
    status: str            # matched, held, specs-only, skipped
    where: str
    category: str
    brand: str
    model: str
    code: str = ""
    tier: str = ""
    changes: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    note: str = ""

    def text(self) -> str:
        if self.status == "skipped":
            return f"skipped {self.where}: {self.note}"
        if self.status == "specs-only":
            return f"specs-only {self.where} ({self.note})" + (f": {'; '.join(self.notices)}" if self.notices else "")
        head = f"{self.status} {self.code} <- {self.where} ({self.tier})"
        body = ", ".join(self.changes) if self.changes else "no change"
        tail = "; ".join(self.notices)
        return f"{head}: {body}" + (f"; {tail}" if tail else "")


@dataclass
class DatasheetReport:
    lines: list[ReportLine] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    changed_codes: list[str] = field(default_factory=list)
    projects_using_changed: list[int] = field(default_factory=list)
    dry_run: bool = False
    files: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        c = self.counts
        return (f"rows read {c.get('rows', 0)}, matched {c.get('matched', 0)}, specs-only {c.get('specs_only', 0)}, skipped {c.get('skipped', 0)}, "
                f"held {c.get('held', 0)}, items changed {c.get('items_changed', 0)}, items untouched {c.get('items_untouched', 0)}, "
                f"priced projects that use a changed item {len(self.projects_using_changed)}"
                + (" (dry run: nothing written)" if self.dry_run else ""))

    def to_dict(self) -> dict:
        return {"lines": [l.text() for l in self.lines], "rows": [asdict(l) for l in self.lines], "counts": self.counts, "changed_codes": self.changed_codes,
                "projects_using_changed": self.projects_using_changed, "summary": self.summary, "dry_run": self.dry_run, "files": self.files}

    def write_csv(self, path: str | Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["status", "code", "where", "category", "brand", "model", "tier", "changes", "notices", "note"])
            for l in self.lines:
                w.writerow([l.status, l.code, l.where, l.category, l.brand, l.model, l.tier, "; ".join(l.changes), "; ".join(l.notices), l.note])
            w.writerow([])
            w.writerow(["summary", self.summary])


def _items_as_catalog(session: Session) -> dict[str, Item]:
    out: dict[str, Item] = {}
    for r in session.exec(select(MaterialItem)).all():
        d = r.model_dump()
        d.pop("updated_at", None)
        out[r.code] = Item(**d)
    return out


def _spec_key(category: str, model_norm: str, brand: str, model: str) -> tuple[str, str, str, str]:
    """The upsert key: the brief's (category, normalised model, brand) plus the model as typed, because the
    normalisation drops the dot and "BCT-FXC-1.2KW" and "BCT-FXC-12KW" are two units, not one row."""
    return category, model_norm, norm(brand), _collapse(model)


def _spec_row_from_sheet(row: SheetRow) -> SheetRow:
    return row


def _projects_using(session: Session, codes: set[str]) -> list[int]:
    """The priced projects whose BOM carries a changed item: they re-price on their next Calculate (the materials list
    is not versioned, DECISIONS "Money, round three"), the same follow-up as a price edit."""
    if not codes:
        return []
    ids: list[int] = []
    for a in session.exec(select(Assessment)).all():
        lines = ((a.results or {}).get("pricing") or {}).get("lines") or []
        if any(str(l.get("code")) in codes for l in lines):
            ids.append(int(a.id))
    return ids


def import_datasheets(session: Session, paths: list[str | Path], source_names: Optional[dict[str, str]] = None, dry_run: bool = False,
                      apply_held: bool = False) -> DatasheetReport:
    """Read the workbooks, upsert the specs rows, match the open ones, apply the figures, report per row (5.1). A dry
    run rolls the session back at the end; otherwise the import stamps the pricing config."""
    from .store import load_config, save_config   # here, not at the top: store imports this module for the re-apply after a materials import

    report = DatasheetReport(dry_run=dry_run, files=[Path(p).name for p in paths])
    items = _items_as_catalog(session)
    rows_by_item = {r.code: r for r in session.exec(select(MaterialItem)).all()}
    existing = {_spec_key(s.category, s.model_norm, s.brand, s.model): s for s in session.exec(select(DatasheetSpec)).all()}
    taken = {s.matched_code: f"{s.source_file}:{s.source_sheet}:{s.source_row}" for s in existing.values() if s.matched_code}
    now = utcnow()
    brands: set[str] = set()
    sheet_rows: list[SheetRow] = []
    for p in paths:
        name = (source_names or {}).get(str(p)) or Path(p).name
        rows = read_datasheet_workbook(p, name, brands)
        for r in rows:
            brands.add(r.brand)
        sha = file_sha256(p)
        seen: set[tuple[str, str, str, str]] = set()
        for r in rows:
            r.raw["_sha256"] = sha
            if not r.skipped:
                seen.add(_spec_key(r.category, r.model_norm, r.brand, r.model))
        # a row of this file's earlier import that the file no longer carries keeps its specs row, with a notice
        for key, s in existing.items():
            if s.source_file == name and key not in seen:
                msg = f"not on the sheet imported on {now.date().isoformat()} (the earlier row is kept)"
                if msg not in s.notices:
                    s.notices = list(s.notices) + [msg]
                    session.add(s)
        sheet_rows += rows
    # upsert the specs rows: an existing match is never moved by a re-run (a manual link least of all)
    specs: list[tuple[SheetRow, DatasheetSpec]] = []
    for r in sheet_rows:
        if r.skipped:
            report.lines.append(ReportLine("skipped", r.where, r.category, r.brand, r.model, note=r.skipped))
            continue
        key = _spec_key(r.category, r.model_norm, r.brand, r.model)
        s = existing.get(key)
        if s is None:
            s = DatasheetSpec(category=r.category, brand=r.brand, model=r.model, model_norm=r.model_norm, imported_at=now)
            existing[key] = s
        if s.matched_code and s.matched_code not in rows_by_item:
            taken.pop(s.matched_code, None)
            s.matched_code, s.match_tier, s.match_note = None, "", f"its item is no longer in the materials list; matched again on {now.date().isoformat()}"
        s.brand_in_model, s.model = r.brand_in_model, r.model
        s.fields, s.held_fields, s.raw, s.notices = r.fields, r.held_fields, r.raw, list(r.notices)
        s.source_file, s.source_sheet, s.source_row, s.file_sha256, s.last_seen_at, s.held = r.source_file, r.source_sheet, r.source_row, r.raw["_sha256"], now, r.held
        if apply_held and r.held_fields and not s.held_applied_at:
            s.held_applied_at = now          # the owner's word, kept on the row through every later run (review finding 2)
        if not r.held_fields:
            s.held_applied_at = None
        r.matched_code, r.match_tier, r.match_note = s.matched_code, s.match_tier, s.match_note if s.matched_code else ""
        specs.append((r, s))
    match_rows([r for r, _ in specs], items, taken)
    changed: set[str] = set()
    untouched: set[str] = set()
    for r, s in specs:
        s.matched_code, s.match_tier = r.matched_code, r.match_tier
        if r.match_note and not (s.match_tier == "manual"):
            s.match_note = r.match_note
        line = ReportLine("specs-only", r.where, r.category, r.brand, r.model, tier=s.match_tier, notices=list(s.notices), note=s.match_note)
        if s.matched_code:
            item = rows_by_item[s.matched_code]
            changes, notes = apply_spec(item, s, apply_held)
            for n in notes:
                if n not in s.notices:
                    s.notices = list(s.notices) + [n]
            applied = bool(s.held_applied_at)
            line.status, line.code, line.changes, line.notices = ("held" if s.held and not applied else "matched"), s.matched_code, changes, list(s.notices)
            if s.held and applied:
                line.tier = f"{s.match_tier}; held figures applied on {s.held_applied_at.date().isoformat()}"
            if changes:
                changed.add(s.matched_code)
                session.add(item)
            else:
                untouched.add(s.matched_code)
        session.add(s)
        report.lines.append(line)
    report.lines.sort(key=lambda l: (l.where.split(" row ")[0], int(l.where.rsplit(" ", 1)[-1])))
    untouched -= changed
    report.changed_codes = sorted(changed)
    report.projects_using_changed = _projects_using(session, changed)
    report.counts = {
        "rows": len(sheet_rows), "matched": sum(1 for l in report.lines if l.status in ("matched", "held")), "specs_only": sum(1 for l in report.lines if l.status == "specs-only"),
        "skipped": sum(1 for l in report.lines if l.status == "skipped"), "held": sum(1 for l in report.lines if l.status == "held"),
        "items_changed": len(changed), "items_untouched": len(untouched),
    }
    if dry_run:
        session.rollback()
        return report
    cfg = load_config(session)
    cfg.datasheets_imported_at = datetime.now(timezone.utc).isoformat()
    cfg.datasheets_imported_from = ", ".join(report.files)
    session.commit()
    save_config(session, cfg)
    return report


def reapply_datasheets(session: Session) -> dict:
    """After a materials import (2.6): match the open specs rows again over the (possibly renamed) items, never
    moving an existing match unless its item is gone, then re-apply every matched row's figures, because the
    workbook import wrote the remark inference back over the electrical fields."""
    rows_by_item = {r.code: r for r in session.exec(select(MaterialItem)).all()}
    specs = list(session.exec(select(DatasheetSpec)).all())
    if not specs:
        return {"matched": 0, "changed": 0}
    items = _items_as_catalog(session)
    for s in specs:
        if s.matched_code and s.matched_code not in rows_by_item:
            s.matched_code, s.match_tier, s.match_note = None, "", "its item is no longer in the materials list; matched again after the materials import"
    taken = {s.matched_code: f"{s.source_file}:{s.source_sheet}:{s.source_row}" for s in specs if s.matched_code}
    sheet_rows = []
    for s in specs:
        r = SheetRow(s.category, s.brand, s.model, s.source_file, s.source_sheet, s.source_row, brand_in_model=s.brand_in_model, fields=s.fields,
                     held_fields=s.held_fields, raw=s.raw, notices=list(s.notices), held=s.held, matched_code=s.matched_code, match_tier=s.match_tier)
        sheet_rows.append((r, s))
    match_rows([r for r, _ in sheet_rows], items, taken)
    matched = changed = 0
    for r, s in sheet_rows:
        if r.matched_code and not s.matched_code:
            s.matched_code, s.match_tier, s.match_note = r.matched_code, r.match_tier, r.match_note
        if s.matched_code:
            matched += 1
            item = rows_by_item[s.matched_code]
            changes, _ = apply_spec(item, s)
            if changes:
                changed += 1
                session.add(item)
        session.add(s)
    session.commit()
    return {"matched": matched, "changed": changed}


def link_spec(session: Session, spec_id: int, code: str) -> dict:
    """A manual match from the Materials page (2.3): applied at once, never moved by a later run."""
    spec = session.get(DatasheetSpec, spec_id)
    item = session.get(MaterialItem, code)
    if spec is None or item is None:
        raise LookupError("No such datasheet row or item.")
    other = session.exec(select(DatasheetSpec).where(DatasheetSpec.matched_code == code)).first()
    if other is not None and other.id != spec.id:
        raise ValueError(f"{code} is already linked to the datasheet row {other.model!r}; unlink it there first.")
    spec.matched_code, spec.match_tier, spec.match_note = code, "manual", "linked by the owner on the Materials page"
    changes, notes = apply_spec(item, spec)
    for n in notes:
        if n not in spec.notices:
            spec.notices = list(spec.notices) + [n]
    session.add(spec)
    session.add(item)
    session.commit()
    return {"code": code, "changes": changes, "notes": notes}


def apply_held_spec(session: Session, spec_id: int) -> dict:
    """The owner confirms one held row (review finding 5: the answers to 6.4 and 6.8 differ): held_applied_at is set and
    kept on the row through every later run, and the figures go on the item at once."""
    spec = session.get(DatasheetSpec, spec_id)
    if spec is None:
        raise LookupError("No such datasheet row.")
    if not spec.held_fields:
        raise ValueError("This row holds no figure back.")
    spec.held_applied_at = utcnow()
    changes: list[str] = []
    if spec.matched_code:
        item = session.get(MaterialItem, spec.matched_code)
        if item is not None:
            changes, notes = apply_spec(item, spec)
            for n in notes:
                if n not in spec.notices:
                    spec.notices = list(spec.notices) + [n]
            session.add(item)
    session.add(spec)
    session.commit()
    return {"code": spec.matched_code, "changes": changes, "held_applied_at": spec.held_applied_at.isoformat()}


def withdraw_held_spec(session: Session, spec_id: int) -> dict:
    """The owner takes the confirmation back: the row is held again and each held figure still on the item goes back
    to what the item carried without it (the workbook remark's figure, else blank)."""
    spec = session.get(DatasheetSpec, spec_id)
    if spec is None:
        raise LookupError("No such datasheet row.")
    spec.held_applied_at = None
    changes: list[str] = []
    if spec.matched_code:
        item = session.get(MaterialItem, spec.matched_code)
        if item is not None:
            inferred = electrical_from_remarks(item.category, item.name, item.spec, item.remarks)
            for fld, v in (spec.held_fields or {}).items():
                if fld not in ELECTRICAL_FIELDS or not _same(getattr(item, fld, None), v):
                    continue
                new = inferred.get(fld, "" if fld in ELECTRICAL_TEXT_FIELDS else None)
                setattr(item, fld, new)
                changes.append(f"{fld} {_fmt(v)} -> {_fmt(new)}")
            if changes:
                item.updated_at = utcnow()
                session.add(item)
    session.add(spec)
    session.commit()
    return {"code": spec.matched_code, "changes": changes}


def add_item_from_spec(session: Session, spec_id: int, code: str, supplier: str = "") -> MaterialItem:
    """"Add as item" (2.3): a material item with the owner's code, the datasheet figures, list price 0 and inactive,
    so the BOQ never prices it at zero; the owner types the price and activates it."""
    spec = session.get(DatasheetSpec, spec_id)
    if spec is None:
        raise LookupError("No such datasheet row.")
    if session.get(MaterialItem, code) is not None:
        raise ValueError("An item with this code exists already")
    name = spec.model if spec.category != "Solar Panel" else f"{spec.model}"
    if not supplier:
        # the maker is the supplier only when a supplier of that name is on the SUPPLIERS sheet (a dealer sells most makers); else blank for the owner
        known = {str(x).lower(): str(x) for x in session.exec(select(MaterialSupplier.name)).all()}
        supplier = known.get(spec.brand.strip().lower(), "")
    item = MaterialItem(code=code, category=spec.category, supplier=supplier, name=name, spec=f"{spec.brand}; datasheet row {spec.source_sheet} row {spec.source_row}",
                        list_price=0.0, active=False, weight_source="manual")
    session.add(item)
    spec.matched_code, spec.match_tier, spec.match_note = code, "manual", "added as an item from the datasheet row"
    apply_spec(item, spec)
    session.add(spec)
    session.commit()
    session.refresh(item)
    return item


def datasheet_page(session: Session, category: Optional[str] = None) -> dict:
    """What the Materials page shows (2.5): every specs row (the ones without an item are "datasheet only"), and per
    equipment item the source of each electrical figure: datasheet, typed (the owner's override), remarks (the
    workbook's remark inference) or none."""
    specs = session.exec(select(DatasheetSpec).order_by(DatasheetSpec.category, DatasheetSpec.source_file, DatasheetSpec.source_sheet, DatasheetSpec.source_row)).all()
    if category:
        specs = [s for s in specs if s.category == category]
    by_code = {s.matched_code: s for s in specs if s.matched_code}
    items: dict[str, dict] = {}
    stmt = select(MaterialItem).where(MaterialItem.category.in_(["Solar Panel", "Inverter", "Battery", "All-in-one System"]))  # type: ignore[attr-defined]
    for it in session.exec(stmt).all():
        if category and it.category != category:
            continue
        s = by_code.get(it.code)
        inferred = electrical_from_remarks(it.category, it.name, it.spec, it.remarks)
        if it.category == "Inverter":
            # the flag and the certificate are read from the item's name and remark at import, like the remark figures
            inferred["grid_interactive"] = infer_grid_interactive(it.name, it.remarks)
            inferred["certifications"] = certifications_in_remarks(it.remarks)
        prov: dict[str, str] = {}
        sheet = {} if s is None else dict(s.fields)
        if s is not None and s.held_applied_at:
            sheet.update(s.held_fields or {})     # a held figure the owner applied reads "datasheet" too
        for fld in ELECTRICAL_FIELDS:
            v = getattr(it, fld, None)
            if v in (None, ""):
                continue
            if fld in sheet and fld not in ((s.overridden_fields or []) if s else []) and _same(sheet[fld], v):
                prov[fld] = "datasheet"
            elif fld in inferred and _same(inferred[fld], v):
                prov[fld] = "remarks"
            else:
                prov[fld] = "typed"
        items[it.code] = {
            "code": it.code, "name": it.name, "category": it.category, "provenance": prov,
            "source": "datasheet" if "datasheet" in prov.values() else "typed" if "typed" in prov.values() else "remarks" if "remarks" in prov.values() else "none",
            "datasheet": None if s is None else {"id": s.id, "file": s.source_file, "date": s.imported_at.isoformat() if s.imported_at else None, "sheet": s.source_sheet, "row": s.source_row,
                                                 "tier": s.match_tier, "fields": s.fields, "held_fields": s.held_fields, "held": s.held, "overridden": s.overridden_fields, "notices": s.notices,
                                                 "held_applied_at": s.held_applied_at.isoformat() if s.held_applied_at else None},
        }
    return {
        "rows": [{"id": s.id, "category": s.category, "brand": s.brand, "brand_in_model": s.brand_in_model, "model": s.model, "fields": s.fields, "held_fields": s.held_fields,
                  "notices": s.notices, "source_file": s.source_file, "source_sheet": s.source_sheet, "source_row": s.source_row,
                  "imported_at": s.imported_at.isoformat() if s.imported_at else None, "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
                  "matched_code": s.matched_code, "match_tier": s.match_tier, "match_note": s.match_note, "overridden_fields": s.overridden_fields, "held": s.held,
                  "held_applied_at": s.held_applied_at.isoformat() if s.held_applied_at else None} for s in specs],
        "items": items,
    }


def datasheet_sources(session: Session) -> dict[str, dict]:
    """Per matched item: the file and date its figures came from (the plan set says so beside each figure, 4.2)."""
    out: dict[str, dict] = {}
    for s in session.exec(select(DatasheetSpec).where(DatasheetSpec.matched_code.is_not(None))).all():  # type: ignore[union-attr]
        out[str(s.matched_code)] = {"file": s.source_file, "date": s.imported_at.date().isoformat() if s.imported_at else "", "fields": s.fields, "held": s.held}
    return out


# ---------------------------------------------------------------- the command

def main(argv: Optional[list[str]] = None) -> int:
    from ..config import get_settings
    from ..db import init_engine
    from .store import ensure_seeded

    ap = argparse.ArgumentParser(description="Import the maker's datasheet workbooks (panels, inverters, batteries) into the app database.")
    ap.add_argument("files", nargs="+", help="the datasheet workbooks (.xlsx); the kind is read from each sheet's header words")
    ap.add_argument("--dry-run", action="store_true", help="report what would change and write nothing")
    ap.add_argument("--report", help="write the per-row report to this CSV file")
    ap.add_argument("--apply-held", action="store_true", help="apply the held figures too (the grid-tie rows' battery figures, a maximum above 1 C): only on the owner's word")
    args = ap.parse_args(argv)
    settings = get_settings()
    engine = init_engine(settings.database_path)
    with Session(engine) as session:
        ensure_seeded(session)
        report = import_datasheets(session, args.files, dry_run=args.dry_run, apply_held=args.apply_held)
    for l in report.lines:
        print(l.text())
    print(report.summary)
    if report.projects_using_changed:
        print("projects to re-price on their next Calculate:", ", ".join(str(i) for i in report.projects_using_changed))
    if args.report:
        report.write_csv(args.report)
        print("report written to", args.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
