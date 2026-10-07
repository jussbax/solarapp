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

    @property
    def is_hybrid_inverter(self) -> bool:
        n = self.name.lower()
        return self.category == "All-in-one System" or (self.category == "Inverter" and ("hybrid" in n or "off-grid" in n))

    def amps_in_name(self) -> Optional[float]:
        m = re.findall(r"(\d+(?:\.\d+)?)\s*A\b", self.name)
        return max(float(x) for x in m) if m else None


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
