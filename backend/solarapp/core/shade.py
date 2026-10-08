"""Shade from firewalls, long walls, trees and buildings.

Walls: a long wall beside a face casts a strip along its whole length. The sun's
path at the site latitude is swept over a year to find how far the shadow
reaches during the main hours (9 to 3) and all day (8 to 4), as a multiple of
the wall's height above the roof; the main-hours strip is cut out of the face
before panels are fitted. In the hourly simulation the same geometry gives the
share of the remaining panels in the wall's shadow for every hour, and that
share loses its beam irradiance.

Trees and buildings: direction and angle to the top from the panel height. The
field rule (under 18 degrees ignore, 18 to 32 small loss, over 32 leave the area
out, north side ignored under 60) is reported as guidance; the simulation blocks
the beam whenever the sun is inside the obstacle's sector and below its top.
Ported from the owner's earlier roof-check tool.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import numpy as np

from .layout import FaceCuts

EDGES = ("eave", "ridge", "left", "right")


def norm360(a: float) -> float:
    a = a % 360.0
    return a + 360.0 if a < 0 else a


def sunpos(lat_deg: float, doy: int, hour: float) -> tuple[float, float]:
    """Solar elevation and azimuth (radians, azimuth clockwise from north) from a simple model; solar time."""
    lat = math.radians(lat_deg)
    dec = math.radians(23.44) * math.sin(2 * math.pi * (284 + doy) / 365.0)
    h = math.radians((hour - 12.0) * 15.0)
    s = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(h)
    el = math.asin(max(-1.0, min(1.0, s)))
    cz = (math.sin(dec) - math.sin(el) * math.sin(lat)) / max(math.cos(el) * math.cos(lat), 1e-9)
    az = math.acos(max(-1.0, min(1.0, cz)))
    if h > 0:
        az = 2 * math.pi - az
    return el, az


@lru_cache(maxsize=512)
def wall_factors(lat_deg: float, wall_az_deg: float) -> dict:
    """How far a long wall's shadow reaches, as a multiple of its height above the panels.
    main = 9 am to 3 pm, all = 8 am to 4 pm, on any day of the year."""
    key = round(norm360(wall_az_deg) / 5.0) * 5.0 % 360.0
    lat = round(lat_deg, 1)
    res: dict = {}
    for name, h0, h1 in (("all", 8, 16), ("main", 9, 15)):
        mn = 90.0
        for d in range(1, 366, 2):
            m = h0 * 60
            while m <= h1 * 60:
                el, az = sunpos(lat, d, m / 60.0)
                c = math.cos(az - math.radians(key))
                if c > 0.01 and el > 0:
                    prof = math.degrees(math.atan(math.tan(el) / c))
                    if prof < mn:
                        mn = prof
                m += 10
        res[name] = 0.0 if mn >= 89.9 else 1.0 / math.tan(math.radians(mn))
        res[name + "_angle"] = mn
    return res


def wall_azimuth(face_az_deg: float, edge: str) -> float:
    """Compass direction of a wall from the panels, given the direction the face looks toward and the edge it lies along."""
    a = float(face_az_deg)
    if edge == "eave":
        return norm360(a)
    if edge == "ridge":
        return norm360(a + 180.0)
    if edge == "left":
        return norm360(a + 90.0)   # left as you face the roof from the ground
    return norm360(a - 90.0)       # right


def wall_cut(factor: float, height_m: float, gap_m: float, tilt_deg: float, edge: str) -> float:
    """Distance into the face that is shaded: along the slope for eave/ridge walls, along the eave for end walls."""
    t = math.radians(float(tilt_deg or 0.0))
    need = factor * height_m - gap_m
    if need <= 0:
        return 0.0
    if edge == "eave":
        return need / (math.cos(t) + factor * math.sin(t))
    if edge == "ridge":
        den = math.cos(t) - factor * math.sin(t)
        return math.inf if den <= 0 else need / den
    return need


@dataclass
class WallDetail:
    id: str
    edge: str
    side_deg: float
    height_m: float
    gap_m: float
    strip_m: float        # main hours (9 to 3), cut from the face
    strip_all_m: float    # all day (8 to 4)
    whole_face: bool

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["strip_m"] = None if math.isinf(d["strip_m"]) else d["strip_m"]
        d["strip_all_m"] = None if math.isinf(d["strip_all_m"]) else d["strip_all_m"]
        return d


def face_cuts(face, lat_deg: float) -> tuple[FaceCuts, list[WallDetail]]:
    """Main-hours strips per edge from the face's walls."""
    cuts = FaceCuts()
    details: list[WallDetail] = []
    for w in getattr(face, "walls", []) or []:
        h = float(w.height_m or 0.0)
        if h <= 0 or w.edge not in EDGES:
            continue
        waz = wall_azimuth(face.azimuth_deg, w.edge)
        f = wall_factors(lat_deg, waz)
        c_main = wall_cut(f["main"], h, float(w.gap_m or 0.0), face.tilt_deg, w.edge)
        c_all = wall_cut(f["all"], h, float(w.gap_m or 0.0), face.tilt_deg, w.edge)
        dim = face.width_m if w.edge in ("eave", "ridge") else face.length_m
        whole = math.isinf(c_main) or c_main >= dim
        setattr(cuts, w.edge, max(getattr(cuts, w.edge), min(c_main, dim) if not math.isinf(c_main) else dim))
        details.append(WallDetail(w.id, w.edge, waz, h, float(w.gap_m or 0.0), c_main, c_all, whole))
    return cuts, details


def obstacle_class(direction_deg: float, elevation_deg: float) -> tuple[str, str]:
    a = norm360(float(direction_deg))
    ang = float(elevation_deg)
    north = a > 292.5 or a < 67.5
    if north and ang < 60:
        return "clear", "North side: no shade between 8 am and 4 pm."
    if ang < 18:
        return "clear", "Under 18 degrees: no shade between 8 am and 4 pm."
    if ang <= 32:
        return "small", "18 to 32 degrees: shade early or late in some months. Small loss."
    return "main", "Over 32 degrees: shade between 9 am and 3 pm in some months. Consider leaving that area out."


def beam_factor(face, cuts: FaceCuts, sun_az_deg: np.ndarray, sun_el_deg: np.ndarray, lat_deg: float) -> Optional[np.ndarray]:
    """Per-hour share of the face's panels that still see the sun (1 = no shade). None when the face has no obstacles."""
    walls = [w for w in (getattr(face, "walls", []) or []) if (w.height_m or 0) > 0 and w.edge in EDGES]
    trees = [t for t in (getattr(face, "obstacles", []) or []) if t.elevation_deg is not None and t.elevation_deg > 0]
    if not walls and not trees:
        return None
    az = np.radians(np.asarray(sun_az_deg, dtype=float))
    el = np.radians(np.asarray(sun_el_deg, dtype=float))
    up = el > 0
    f = np.ones_like(el)
    t = math.radians(float(face.tilt_deg or 0.0))
    for w in walls:
        waz = math.radians(wall_azimuth(face.azimuth_deg, w.edge))
        c = np.cos(az - waz)
        mask = up & (c > 0.01)
        if not mask.any():
            continue
        factor = np.zeros_like(el)
        factor[mask] = 1.0 / np.tan(np.arctan(np.tan(el[mask]) / c[mask]))
        need = factor * float(w.height_m) - float(w.gap_m or 0.0)
        if w.edge == "eave":
            d = need / (math.cos(t) + factor * math.sin(t))
        elif w.edge == "ridge":
            den = math.cos(t) - factor * math.sin(t)
            d = np.where(den > 0, need / np.where(den > 0, den, 1.0), np.inf)
        else:
            d = need
        strip = getattr(cuts, w.edge)
        dim = float(face.width_m if w.edge in ("eave", "ridge") else face.length_m)
        span = dim - strip
        frac = np.clip((d - strip) / span, 0.0, 1.0) if span > 0 else np.ones_like(el)
        frac = np.where(mask & (need > 0), frac, 0.0)
        f *= 1.0 - frac
    for tr in trees:
        direction = math.radians(norm360(float(tr.direction_deg or 0.0)))
        half = math.radians(float(tr.width_deg or 40.0) / 2.0)
        diff = np.abs((az - direction + np.pi) % (2 * np.pi) - np.pi)
        blocked = up & (diff <= half) & (el < math.radians(float(tr.elevation_deg)))
        f = np.where(blocked, f * (1.0 - float(tr.share if tr.share is not None else 1.0)), f)
    return f
