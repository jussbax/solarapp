"""Every city and municipality in the Philippines, with a centroid, for the public estimate and the booking labels.

The quick estimate only needs the PVGIS cell (about 27 km across) and the trip
distance from the office, so a town centre is precise enough; the roof visit
settles the exact location. The list is bundled in ``towns_ph.json`` (PSA PSGC
names and codes; OCHA HDX administrative boundaries for the area-weighted
centroids, CC BY-IGO; via the psgc package 2026.4.13, MIT). Independent and
highly urbanised cities sit under their geographic province; Metro Manila for
NCR. The server never looks anything up outside.
"""
from __future__ import annotations

import json
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

Town = tuple[str, str, float, float]  # name, province, lat, lon

_FILE = Path(__file__).with_name("towns_ph.json")


@lru_cache(maxsize=1)
def _load() -> tuple[list[Town], list[str], str]:
    data = json.loads(_FILE.read_text(encoding="utf-8"))
    towns = [(str(n), str(p), float(la), float(lo)) for n, p, la, lo, _city in data["towns"]]
    provinces = sorted({t[1] for t in towns}, key=str.lower)
    return towns, provinces, str(data.get("source", ""))


def all_towns() -> list[Town]:
    return _load()[0]


def provinces() -> list[str]:
    return _load()[1]


def towns_payload(province: str | None = None) -> list[dict]:
    """The picker's rows: every town, or one province's, name-sorted."""
    key = (province or "").strip().lower()
    rows = [t for t in all_towns() if not key or t[1].lower() == key]
    return [{"name": n, "province": p, "lat": la, "lon": lo} for n, p, la, lo in sorted(rows, key=lambda t: t[0].lower())]


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a = sin(radians(lat2 - lat1) / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def nearest_town(lat: float, lon: float) -> tuple[Town, float]:
    """The town centre closest to a point and its distance in km."""
    towns = all_towns()
    best = min(towns, key=lambda t: _km(lat, lon, t[2], t[3]))
    return best, _km(lat, lon, best[2], best[3])


def _variants(name: str) -> set[str]:
    """"Tanauan", "Tanauan City" and "City of Tanauan" name the same place."""
    key = (name or "").strip().lower()
    if key.startswith("city of "):
        key = key[8:]
    if key.endswith(" city"):
        key = key[:-5]
    return {key, f"{key} city", f"city of {key}"}


def find_town(name: str, province: str = "") -> Town | None:
    """A town by name (any of its spellings) and, when given, province; without a province the first match wins."""
    wanted = _variants(name)
    if not wanted or wanted == {"", " city", "city of "}:
        return None
    prov = (province or "").strip().lower()
    for t in all_towns():
        if t[0].lower() in wanted and (not prov or t[1].lower() == prov):
            return t
    return None
