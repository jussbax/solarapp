"""Plain data for the pricing engine: items, suppliers, categories. No database here."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .config import PricingConfig


@dataclass
class Item:
    code: str
    category: str
    supplier: str
    name: str
    spec: str = ""
    unit: str = "pc"
    sold_as: str = "pc"
    list_price: float = 0.0
    rating: Optional[float] = None
    rating_unit: str = ""
    weight_kg: float = 0.0
    volume_m3: float = 0.0
    weight_source: str = ""
    storage: float = 0.0
    price_list_date: str = ""
    remarks: str = ""
    panel_length_m: Optional[float] = None
    panel_width_m: Optional[float] = None
    active: bool = True
    # electrical data (contract C4), None until the datasheet is typed or the workbook carries the column
    grid_interactive: Optional[bool] = None
    certifications: str = ""
    max_pv_voltage_v: Optional[float] = None
    mppt_min_v: Optional[float] = None
    mppt_max_v: Optional[float] = None
    mppt_count: Optional[int] = None
    mppt_max_a: Optional[float] = None
    ac_input_a: Optional[float] = None
    battery_max_a: Optional[float] = None
    continuous_a: Optional[float] = None
    voc_v: Optional[float] = None
    vmp_v: Optional[float] = None
    isc_a: Optional[float] = None
    imp_a: Optional[float] = None
    temp_coeff_voc_pct: Optional[float] = None
    temp_coeff_isc_pct: Optional[float] = None

    @property
    def is_hybrid_inverter(self) -> bool:
        n = self.name.lower()
        return self.category == "All-in-one System" or (self.category == "Inverter" and ("hybrid" in n or "off-grid" in n))

    def amps_in_name(self) -> Optional[float]:
        m = re.findall(r"(\d+(?:\.\d+)?)\s*A\b", self.name)
        return max(float(x) for x in m) if m else None


ELECTRICAL_FIELDS = (
    "grid_interactive", "certifications", "max_pv_voltage_v", "mppt_min_v", "mppt_max_v", "mppt_count", "mppt_max_a",
    "ac_input_a", "battery_max_a", "continuous_a", "voc_v", "vmp_v", "isc_a", "imp_a", "temp_coeff_voc_pct", "temp_coeff_isc_pct",
)


def infer_grid_interactive(name: str, remarks: str = "") -> Optional[bool]:
    """From the item's name first, then the workbook remark. "grid-tie" means it may export; "off-grid" in the NAME
    means it may not; "on/off-grid" names a mode, not a listing, so it is unknown; any other "hybrid" may export (the
    Felicity eco-hybrid included: the owner confirmed its selling option with the maker, whatever the remark calls its
    type). A remark that says it cannot export, or to CHECK the certification, overrides. Stays editable on the
    Materials page."""
    n = (name or "").lower()
    r = (remarks or "").lower()
    if re.search(r"(no|cannot|can't|without)\s+(export|sell|feed)", f"{n} {r}"):
        return False
    if re.search(r"check[^.]*certif", r):
        return None
    if re.search(r"grid[\s-]?tie", n):
        return True
    if re.search(r"on/off[\s-]?grid|on[\s-]grid", n):
        return None
    if re.search(r"off[\s-]?grid", n):
        return False
    if "hybrid" in n:
        return True
    if re.search(r"grid[\s-]?tie", r):
        return True
    if re.search(r"off[\s-]?grid", r):
        return False
    return None


def certifications_in_remarks(remarks: str) -> str:
    """The IEC or UL listings a remark names ("IEC 61727 / 62116 listed"), unless it says they are not listed."""
    text = remarks or ""
    if re.search(r"not\s+listed", text, re.I):
        return ""
    found = re.findall(r"\b(?:IEC|UL|EN)\s*\d{4,5}(?:\s*/\s*\d{4,5})*", text)
    return "; ".join(dict.fromkeys(f.strip() for f in found))


def _num(pattern: str, text: str) -> Optional[float]:
    m = re.search(pattern, text, re.I)
    return float(m.group(1)) if m else None


def electrical_from_remarks(category: str, name: str, spec: str, remarks: str) -> dict:
    """Figures the owner wrote into the workbook remark or spec ("2 MPPT, 18A each; battery 135A", "500 Voc",
    "Continuous 120A"). Only a starting point: the datasheet column, when the workbook has one, wins."""
    text = f"{spec or ''}. {remarks or ''}"
    out: dict = {}
    if category == "Inverter":
        out["battery_max_a"] = _num(r"battery\s*(\d+(?:\.\d+)?)\s*A\b", text)
        n_mppt = _num(r"(\d+)\s*(?:x\s*)?MPPT", text)
        out["mppt_count"] = int(n_mppt) if n_mppt else None
        out["mppt_max_a"] = _num(r"(\d+(?:\.\d+)?)\s*A\s*each", text) or _num(r"MPPT\s*(\d+(?:\.\d+)?)\s*A\b", text) or _num(r"\d+\s*x\s*(\d+(?:\.\d+)?)\s*A\s*PV", text)
        out["max_pv_voltage_v"] = _num(r"(\d{3,4})\s*Voc", text)
    elif category == "Battery":
        out["continuous_a"] = _num(r"continuous(?: current)?\s*(\d+(?:\.\d+)?)\s*A\b", text)
    return {k: v for k, v in out.items() if v is not None}


@dataclass
class Supplier:
    name: str
    pickup_address: str = ""
    dealer_discount: float = 0.0
    payment_fee: float = 0.0
    delivers_free: bool = False
    price_list_date: str = ""
    prices_note: str = ""
    warranty: str = ""
    remarks: str = ""


@dataclass
class Catalog:
    items: dict[str, Item] = field(default_factory=dict)
    suppliers: dict[str, Supplier] = field(default_factory=dict)

    def get(self, code: str) -> Optional[Item]:
        return self.items.get(code)

    def supplier(self, name: str) -> Supplier:
        return self.suppliers.get(name) or Supplier(name=name)

    def by_category(self, category: str) -> list[Item]:
        return [i for i in self.items.values() if i.category == category and i.active]


PANEL_DIMS_RE = re.compile(r"(\d{4})\s*[x×]\s*(\d{3,4})\s*[x×]\s*\d{2,3}\s*mm", re.I)


def parse_panel_dims(spec: str) -> tuple[Optional[float], Optional[float]]:
    m = PANEL_DIMS_RE.search(spec or "")
    if not m:
        return None, None
    a, b = int(m.group(1)), int(m.group(2))
    return max(a, b) / 1000.0, min(a, b) / 1000.0


def make_config_for_catalog(cfg: PricingConfig) -> PricingConfig:
    return cfg
