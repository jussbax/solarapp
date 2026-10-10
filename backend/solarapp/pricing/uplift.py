"""The uplift check of the mounting (round 13, item 3; docs/audits/round-13/engineer-brief.md 3.4 to 3.7): NSCP 2015
Section 207, allowable stress design, per roof face, from the roof construction the survey typed and the wind figures
the signing engineer typed.

The chain, every figure verify:

    V        basic wind speed, 3-s gust at 10 m, by wind zone: the province's row under Settings > Mounting and wind, or the
             project's own figure                                                      (NSCP 2015 Figure 207A.5-1A: verify)
    Kz       = 2.01 × (max(h, 4.6) / zg)^(2/alpha), alpha and zg by exposure category, typed    (NSCP Table 207A.9-1 ≡ ASCE 7-10 26.9-1: verify)
    Kzt      topographic factor, 1.0 unless typed (ASSUMPTION: no hill or ridge)          (NSCP 207A.8: verify)
    Kd       directionality for components and cladding, typed                           (NSCP Table 207A.6-1: verify)
    qh       = 0.613 × Kz × Kzt × Kd × V²   [N/m², V in m/s]                             (NSCP 207B.3-1 / 207E.3-1: verify)
    GCp      external pressure coefficient, components and cladding, per roof zone, typed on the project; the worst typed
             zone's figure for every panel (ASSUMPTION)                                   (NSCP 207E.4-2: verify)
    p_up     = qh × |GCp|   (ASSUMPTION: the array sits above the roof surface, no internal pressure on it)
    D        panel weight (the item's weight_kg) + the rail share (mounting.rail_kg_per_m × rail per panel), over A_panel
    T_panel  = 0.6 × p_up × A − 0.6 × D × A   (0.6D + 0.6W, NSCP 203.4: verify; zero when negative)
    strip    = the panel dimension across the rails × 0.5 (each rail line carries half the panel)
    s_foot   the foot spacing along the rail: a multiple of the purlin spacing (the feet sit on purlins), at or under the
             rail maker's maximum span (the BOQ rule's spacing when that is not set: ASSUMPTION)
    T_foot   = (0.6 × p_up − 0.6 × D) × s_foot × strip;  T_screw = T_foot / screws_per_foot  at or under  the typed pull-out gives holds
    s_allow  = screws_per_foot × pull-out / ((0.6 × p_up − 0.6 × D) × strip);  s_foot = the largest multiple of the purlin
             spacing at or under min(s_allow, the maximum span);  feet per rail line = floor(line / s_foot) + 1

The verdict is on the design the BOM carries: PASS when a foot spacing on the purlins holds (the BOM's L-foot count then
follows the feet per rail line); FAIL when even a foot on every purlin does not hold (the fix is more screws per foot or a
stronger fastener, the signing engineer's; the BOM keeps the rule's count with a note); NOT CHECKED when an input is
blank, naming it. The app ships none of the figures: the zone, the speed, the exposure constants, Kd, GCp and the
pull-out are typed with their sources, printed with them, and a blank stops the chain at its line. Nothing here reaches
the website estimate or the customer documents.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from ..core.towns import nearest_town
from ..schemas import AssessmentDoc, RoofConstruction, RoofFace, WindInputs
from .catalog import Item
from .config import MountingConfig, PricingConfig
from .engine import BomLine

G = 9.81                 # m/s²
KZ_CONSTANT = 2.01       # the Kz formula's constant (the table's note: verify)
KZ_FLOOR_M = 4.6         # the formula's floor on the height, 15 ft (the table's note: verify)
Q_CONSTANT = 0.613       # qz = 0.613 Kz Kzt Kd V², N/m² with V in m/s (NSCP 207B.3-1: verify)
ASD = 0.6                # 0.6D + 0.6W (NSCP 203.4: verify)
KZT_DEFAULT = 1.0        # ASSUMPTION: no hill or ridge; the signing engineer types another
EXPOSURE_DEFAULT = "B"   # ASSUMPTION: a town site; C for open ground, the lakeshore and the coast
WIND_ZONES_FILE = Path(__file__).resolve().parent.parent / "core" / "wind_zones.json"
SETTINGS_WHERE = "Settings › Mounting and wind"
# the detail drawn for each roof type (brief 3.1): the metal sheets on purlins now; the tile detail waits on the owner's word
DETAILS = {"rib_metal": "A", "corrugated_metal": "B"}
TILE_TYPES = ("tile_clay", "tile_concrete")
ROOF_TYPE_WORDS = {"rib_metal": "rib-type metal sheet on purlins", "corrugated_metal": "corrugated metal sheet on purlins", "tile_clay": "clay tile",
                   "tile_concrete": "concrete tile", "concrete_deck": "concrete deck", "other": "other"}
PURLIN_WORDS = {"steel_c": "steel C-purlin", "steel_tubular": "steel tubular purlin", "wood": "wood purlin", "none": "no purlin"}


# ---------------------------------------------------------------- the wind zone by province

@lru_cache(maxsize=1)
def wind_zone_file() -> dict:
    """core/wind_zones.json: every province with the zone, the speed and the source, shipped blank."""
    return json.loads(WIND_ZONES_FILE.read_text(encoding="utf-8"))


def province_of(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    """The province behind the pin: the nearest town centre's (core/towns.py)."""
    if lat is None or lon is None:
        return None
    (_, province, _, _), _km = nearest_town(float(lat), float(lon))
    return province


def wind_zone_for(province: Optional[str], m: MountingConfig) -> dict:
    """The province's row: the figures typed under Settings over the shipped file's blank row."""
    typed = m.wind_zones.get(province or "")
    file_row = (wind_zone_file().get("provinces") or {}).get(province or "") or {}
    if typed is not None and typed.v_kmh:
        return {"province": province, "zone": typed.zone, "v_kmh": float(typed.v_kmh), "source": typed.source, "status": "typed"}
    return {"province": province, "zone": str(file_row.get("zone") or (typed.zone if typed else "") or ""), "v_kmh": None, "source": "",
            "status": "not set" if province else "no pin"}


# ---------------------------------------------------------------- the figures and their provenance

def _fig(value: Any, source: str = "", *, assumed: bool = False, note: str = "") -> dict:
    """A figure as the sheet prints it: the value, where it came from, whether it is an assumption, a note."""
    return {"value": value, "source": source, "assumed": assumed, "note": note, "missing": None}


def _missing(what: str) -> dict:
    return {"value": None, "source": "", "assumed": False, "note": "", "missing": what}


def resolve_wind(wind: WindInputs, province: Optional[str], m: MountingConfig) -> dict:
    """The project's wind figures with their sources: V (the project's, else the province's row), the exposure category and
    its constants, Kzt, Kd, GCp. Each is a figure or a missing-reason; nothing is defaulted beyond the two labelled
    assumptions (exposure B, Kzt 1.0)."""
    out: dict[str, Any] = {"province": province}
    row = wind_zone_for(province, m)
    if wind.v_kmh:
        out["v_kmh"] = _fig(float(wind.v_kmh), wind.v_source or "typed on the project (no source given: verify)")
        out["zone"] = wind.zone or row["zone"]
    elif row["v_kmh"]:
        out["v_kmh"] = _fig(row["v_kmh"], row["source"] or f"{SETTINGS_WHERE} (no source given: verify)")
        out["zone"] = row["zone"]
    else:
        where = f"not set for {province} under {SETTINGS_WHERE} nor typed on the project" if province else "the project has no map pin, and none is typed on the project"
        out["v_kmh"] = _missing(f"basic wind speed V: {where}")
        out["zone"] = wind.zone or row["zone"]
    exposure = wind.exposure or EXPOSURE_DEFAULT
    out["exposure"] = _fig(exposure, "typed on the project" if wind.exposure else "", assumed=not wind.exposure,
                           note="" if wind.exposure else f"assumption: exposure {EXPOSURE_DEFAULT}, a town site; C for open ground, the lakeshore and the coast")
    cat = m.exposures.get(exposure)
    if cat is not None and cat.alpha and cat.zg_m:
        out["alpha"] = _fig(float(cat.alpha), m.exposure_source or f"{SETTINGS_WHERE} (no source given: verify)")
        out["zg_m"] = _fig(float(cat.zg_m), m.exposure_source or f"{SETTINGS_WHERE} (no source given: verify)")
    else:
        out["alpha"] = _missing(f"exposure {exposure}: alpha and zg not typed under {SETTINGS_WHERE}")
        out["zg_m"] = _missing(f"exposure {exposure}: alpha and zg not typed under {SETTINGS_WHERE}")
    if wind.kzt:
        out["kzt"] = _fig(float(wind.kzt), wind.kzt_source or "typed on the project (no source given: verify)")
    else:
        out["kzt"] = _fig(KZT_DEFAULT, "", assumed=True, note="assumption: 1.0, no hill or ridge; the signing engineer types another")
    if m.kd:
        out["kd"] = _fig(float(m.kd), m.kd_source or f"{SETTINGS_WHERE} (no source given: verify)")
    else:
        out["kd"] = _missing(f"Kd (directionality): not typed under {SETTINGS_WHERE}")
    zones = {1: wind.gcp_zone1, 2: wind.gcp_zone2, 3: wind.gcp_zone3}
    typed = {k: float(v) for k, v in zones.items() if v is not None and float(v) != 0.0}
    if typed:
        worst = max(typed, key=lambda k: abs(typed[k]))
        out["gcp"] = _fig(typed[worst], wind.gcp_source or "typed on the project (no source given: verify)", assumed=True,
                          note=f"assumption: the worst typed zone's figure (zone {worst}, {typed[worst]:g}) for every panel"
                               + ("" if len(typed) == 3 else f"; zone{'s' if 3 - len(typed) > 1 else ''} {', '.join(str(k) for k in zones if k not in typed)} not typed"))
        out["gcp_zone"] = worst
        out["gcp_typed"] = typed
    else:
        out["gcp"] = _missing("GCp per roof zone: not typed on the project (Roof faces › Wind for the uplift check)")
        out["gcp_zone"] = None
        out["gcp_typed"] = {}
    return out


def merged_construction(face: Optional[RoofFace], default: RoofConstruction) -> RoofConstruction:
    """A face's construction over the project's default, field by field: a blank on the face reads the project's."""
    data = default.model_dump()
    if face is not None:
        for k, v in face.construction.model_dump().items():
            if v not in (None, ""):
                data[k] = v
    return RoofConstruction.model_validate(data)


def kz_at(h_m: float, alpha: float, zg_m: float) -> float:
    """Kz = 2.01 × (max(h, 4.6) / zg)^(2/alpha)."""
    return KZ_CONSTANT * (max(float(h_m), KZ_FLOOR_M) / float(zg_m)) ** (2.0 / float(alpha))


def velocity_pressure_pa(v_ms: float, kz: float, kzt: float, kd: float) -> float:
    """qh = 0.613 × Kz × Kzt × Kd × V², N/m² with V in m/s."""
    return Q_CONSTANT * kz * kzt * kd * float(v_ms) ** 2


# ---------------------------------------------------------------- one face

def evaluate_face(face: Optional[RoofFace], construction: RoofConstruction, wind: dict, rows: list, panel: Item, cfg: PricingConfig) -> dict:
    """The chain on one face for the rows it holds. Returns the steps as figures with their sources, the status
    (pass, fail, not checked), the reasons, the feet per rail line per row and the counts."""
    m, r = cfg.mounting, cfg.roles
    name = face.name if face is not None else "rows beyond the surveyed faces"
    out: dict[str, Any] = {"face_id": face.id if face is not None else None, "name": name, "rows": [], "missing": [], "assumptions": [], "notes": [], "warnings": []}
    roof_type = construction.roof_type
    out["roof_type"] = roof_type
    out["roof_type_words"] = ROOF_TYPE_WORDS.get(roof_type, "")
    out["detail"] = DETAILS.get(roof_type)
    out["construction"] = construction.model_dump()
    # the roof type decides the detail; a type out of scope or not surveyed is said so
    if not roof_type:
        out["notes"].append("roof type: not surveyed; the detail that applies is blank")
    elif roof_type in TILE_TYPES:
        out["missing"].append(f"{name}: a tile roof; the tile detail and its hook wait on the owner's word, so the chain is not run")
        out["warnings"].append({"code": "roof_type_out_of_scope", "message": f"{name}: {ROOF_TYPE_WORDS[roof_type]} roof; the mounting detail is not drawn for it yet (the tile bracket and screw wait on the owner's word) and the uplift check is not run. The structural check is the signing engineer's."})
    elif roof_type not in DETAILS:
        out["missing"].append(f"{name}: roof type {ROOF_TYPE_WORDS.get(roof_type, roof_type)} is out of scope; the structural check is the signing engineer's")
        out["warnings"].append({"code": "roof_type_out_of_scope", "message": f"{name}: mounting detail not drawn for {ROOF_TYPE_WORDS.get(roof_type, roof_type)}; the structural check is the signing engineer's."})
    if construction.condition_flag and construction.condition_flag != "sound":
        out["warnings"].append({"code": "roof_condition", "hard": True, "message": (
            f"{name}: roof condition {construction.condition_flag}" + (f" ({construction.condition})" if construction.condition else "")
            + "; verify the roof carries the array before the design is sealed. Printed on the mounting detail sheet.")})
    # the inputs of this face
    h = construction.mean_roof_height_m
    out["h_m"] = _fig(float(h), "surveyed") if h else _missing(f"{name}: mean roof height h not surveyed")
    sp = construction.purlin_spacing_m
    out["purlin_spacing_m"] = _fig(float(sp), "surveyed") if sp else _missing(f"{name}: purlin spacing not surveyed")
    if construction.fastener_pullout_kn:
        out["pullout_kn"] = _fig(float(construction.fastener_pullout_kn), construction.fastener_pullout_source or "typed on the project (no source given: verify)")
    elif m.fastener_pullout_kn:
        out["pullout_kn"] = _fig(float(m.fastener_pullout_kn), m.fastener_pullout_source or f"{SETTINGS_WHERE} (no source given: verify)")
    else:
        out["pullout_kn"] = _missing(f"the fastener's allowable withdrawal: not typed under {SETTINGS_WHERE} nor on the roof construction")
    # the panel: its area, its weight, the rail share
    L, W = float(panel.panel_length_m or 0), float(panel.panel_width_m or 0)
    area = L * W
    out["panel"] = {"code": panel.code, "length_m": L, "width_m": W, "area_m2": area}
    if area <= 0:
        out["missing"].append("the panel's length and width are not on the item")
    along = float(rows[0].panel_dim_along_row_m) if rows else W
    if abs(along - W) < 1e-6:
        across, out["orientation"] = L, "portrait"
    elif abs(along - L) < 1e-6:
        across, out["orientation"] = W, "landscape"
    else:
        across, out["orientation"] = max(L, W), "portrait"
        out["notes"].append("the row's panel dimension matches neither side of the panel; the long side is taken across the rails (verify)")
    out["strip_m"] = _fig(across / 2.0, "", note=f"the panel's {across:g} m across the rails, half to each rail line")
    out["rail_to_rail_m"] = _fig(across * (1.0 - 2.0 * m.rail_position_fraction), "", assumed=True,
                                 note=f"assumption: the rails at {m.rail_position_fraction:g} of the panel's dimension up the slope from each edge (the maker's clamping zone: verify)")
    weight = float(panel.weight_kg or 0)
    if weight > 0:
        out["weight_kg"] = _fig(weight, f"the item ({panel.weight_source})" if panel.weight_source else "the item")
    else:
        out["weight_kg"] = _fig(0.0, "", assumed=True, note="assumption: the panel's weight is not on the item; the dead load is taken as zero (the conservative side)")
    rail_m = 2.0 * along
    if m.rail_kg_per_m is not None and m.rail_kg_per_m > 0:
        rail_kg = float(m.rail_kg_per_m) * rail_m
        out["rail_kg"] = _fig(rail_kg, SETTINGS_WHERE, note=f"{m.rail_kg_per_m:g} kg/m × {rail_m:g} m of rail per panel (two lines)")
    else:
        rail_kg = 0.0
        out["rail_kg"] = _fig(0.0, "", assumed=True, note=f"assumption: the rail's weight per metre is not set under {SETTINGS_WHERE}; left out of the dead load (the conservative side)")
    d_kpa = (weight + rail_kg) * G / 1000.0 / area if area > 0 else None
    out["d_kpa"] = _fig(d_kpa, "") if d_kpa is not None else _missing("the panel's area")
    # the chain, stopped at the first blank
    missing = [x["missing"] for x in (wind["v_kmh"], out["h_m"], wind["alpha"], wind["kd"], wind["gcp"], out["purlin_spacing_m"], out["pullout_kn"]) if x["missing"]]
    out["missing"] += missing
    out["assumptions"] += [x["note"] for x in (wind["exposure"], wind["kzt"], wind["gcp"], out["weight_kg"], out["rail_kg"], out["rail_to_rail_m"]) if x["assumed"] and x["note"]]
    for key in ("v_ms", "kz", "qh_pa", "p_up_kpa", "t_panel_kn", "net_kpa", "cap_m", "s_std_m", "k_std", "t_foot_std_kn", "t_screw_std_kn", "ratio_std",
                "s_allow_m", "s_foot_m", "k_foot", "t_foot_kn", "t_screw_kn", "ratio", "feet", "feet_per_rail", "screws", "l_foot_rule"):
        out[key] = None
    out["holds_std"] = None
    # the rule's count on these rows, whatever the check says
    out["l_foot_rule"] = sum(2 * int(math.ceil(row.length_m / r.rail_length_m - 1e-9)) * r.l_feet_per_rail for row in rows if row.panels > 0)
    if m.screws_per_foot == 2:
        out["assumptions"].append("assumption: 2 screws per L-foot (the L-foot set's screw, rubber pad and bolt; the owner confirms)")
    out["screws_per_foot"] = _fig(int(m.screws_per_foot), SETTINGS_WHERE, assumed=m.screws_per_foot == 2)
    if m.foot_spacing_max_m:
        cap = float(m.foot_spacing_max_m)
        out["cap_m"] = _fig(cap, m.foot_spacing_max_source or f"{SETTINGS_WHERE} (no source given: verify)", note="the rail maker's maximum span between feet")
    else:
        cap = float(r.rail_length_m) / max(int(r.l_feet_per_rail) - 1, 1)
        out["cap_m"] = _fig(cap, "", assumed=True, note=f"assumption: the BOQ rule's spacing, {r.rail_length_m:g} m rails with {r.l_feet_per_rail} feet each, caps the span until the rail maker's maximum is typed under {SETTINGS_WHERE}")
        out["assumptions"].append(out["cap_m"]["note"])
    if out["missing"]:
        out["status"] = "not checked"
        out["rows"] = [{"length_m": row.length_m, "panels": row.panels, "feet_per_line": None} for row in rows if row.panels > 0]
        out["feet"] = None
        return out
    v_ms = float(wind["v_kmh"]["value"]) / 3.6
    kz = kz_at(float(out["h_m"]["value"]), float(wind["alpha"]["value"]), float(wind["zg_m"]["value"]))
    qh = velocity_pressure_pa(v_ms, kz, float(wind["kzt"]["value"]), float(wind["kd"]["value"]))
    p_up = qh * abs(float(wind["gcp"]["value"])) / 1000.0
    net = ASD * p_up - ASD * float(d_kpa or 0.0)
    strip = float(out["strip_m"]["value"])
    pullout = float(out["pullout_kn"]["value"])
    screws = int(m.screws_per_foot)
    s_p = float(out["purlin_spacing_m"]["value"])
    k_std = int(math.floor(cap / s_p + 1e-9))
    if k_std < 1:
        k_std = 1
        out["notes"].append(f"the purlin spacing {s_p:g} m exceeds the maximum foot span {cap:g} m: a foot on every purlin spans more than the rail maker allows (verify)")
    s_std = k_std * s_p
    out.update({"v_ms": v_ms, "kz": kz, "qh_pa": qh, "p_up_kpa": p_up, "t_panel_kn": max(net * area, 0.0), "net_kpa": net, "k_std": k_std, "s_std_m": s_std})
    t_foot_std = max(net, 0.0) * s_std * strip
    t_screw_std = t_foot_std / screws
    out.update({"t_foot_std_kn": t_foot_std, "t_screw_std_kn": t_screw_std, "ratio_std": t_screw_std / pullout, "holds_std": t_screw_std <= pullout + 1e-9})
    if net <= 0:
        out["notes"].append("the dead load exceeds the uplift: no net uplift on the panel")
        s_allow = math.inf
        k_foot = k_std
    else:
        s_allow = screws * pullout / (net * strip)
        k_foot = int(math.floor(min(s_allow, cap) / s_p + 1e-9))
    out["s_allow_m"] = s_allow if math.isfinite(s_allow) else None
    if k_foot < 1:
        # even a foot on every purlin does not hold: the fix is the signing engineer's
        s_foot = s_p
        out["status"] = "fail"
        t_foot = max(net, 0.0) * s_foot * strip
        out.update({"s_foot_m": s_foot, "k_foot": 1, "t_foot_kn": t_foot, "t_screw_kn": t_foot / screws, "ratio": t_foot / screws / pullout})
        out["warnings"].append({"code": "uplift_fail", "hard": True, "message": (
            f"{name}: uplift check FAILED. With a foot on every purlin ({s_p:g} m) each screw carries {t_foot / screws:.2f} kN against the "
            f"{pullout:g} kN allowable withdrawal typed ({out['pullout_kn']['source']}). The fix is more screws per foot or a stronger fastener: "
            f"the signing engineer's. The plans print the check as FAIL; the L-foot count stays the rule's ({r.l_feet_per_rail} per rail).")})
    else:
        s_foot = k_foot * s_p
        out["status"] = "pass"
        t_foot = max(net, 0.0) * s_foot * strip
        out.update({"s_foot_m": s_foot, "k_foot": k_foot, "t_foot_kn": t_foot, "t_screw_kn": t_foot / screws, "ratio": t_foot / screws / pullout})
        if not out["holds_std"]:
            out["notes"].append(f"at the maximum span {s_std:g} m each screw would carry {t_screw_std:.2f} kN, over the {pullout:g} kN figure, so the feet close up to every "
                                f"{_ordinal(k_foot)} purlin ({s_foot:g} m)")
    feet = 0
    for row in rows:
        if row.panels <= 0:
            continue
        per_line = int(math.floor(row.length_m / s_foot + 1e-9)) + 1
        out["rows"].append({"length_m": row.length_m, "panels": row.panels, "feet_per_line": per_line})
        feet += 2 * per_line
    out["feet"] = feet
    out["feet_per_rail"] = int(math.floor(float(r.rail_length_m) / s_foot + 1e-9)) + 1   # on one rail piece, the figure the crew reads
    out["screws"] = feet * screws
    return out


def _ordinal(k: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(k, f"{k}th")


# ---------------------------------------------------------------- the whole job

def uplift_block(doc: AssessmentDoc, rows: list, panel: Item, cfg: PricingConfig) -> dict:
    """pricing.choices.uplift: the wind figures with their sources, one evaluation per face that holds rows, the verdict,
    the warnings (none blocks) and what the BOM's L-foot line should carry."""
    m, r = cfg.mounting, cfg.roles
    province = province_of(doc.lat, doc.lon)
    wind = resolve_wind(doc.wind, province, m)
    by_face: dict[Optional[str], list] = {}
    for row in rows:
        if row.panels > 0:
            by_face.setdefault(row.face_id, []).append(row)
    faces_by_id = {f.id: f for f in doc.faces}
    faces: list[dict] = []
    for fid, face_rows in by_face.items():
        face = faces_by_id.get(fid) if fid else None
        faces.append(evaluate_face(face, merged_construction(face, doc.roof_default), wind, face_rows, panel, cfg))
    statuses = [f["status"] for f in faces]
    if not faces:
        status = "not checked"
    elif any(s == "not checked" for s in statuses):
        status = "not checked"
    elif any(s == "fail" for s in statuses):
        status = "fail"
    else:
        status = "pass"
    missing: list[str] = []
    for f in faces:
        for x in f["missing"]:
            if x not in missing:
                missing.append(x)
    assumptions: list[str] = []
    for f in faces:
        for x in f["assumptions"]:
            if x not in assumptions:
                assumptions.append(x)
    warnings: list[dict] = [w for f in faces for w in f["warnings"]]
    if status == "not checked":
        reason = "; ".join(missing) if missing else "the job has no rows of panels"
        warnings.append({"code": "uplift_not_checked", "message": (
            f"Uplift check not checked: {reason}. The mounting detail sheet prints the chain with the blanks; the L-foot count stays the rule's "
            f"({r.l_feet_per_rail} per rail). Type the figures under {SETTINGS_WHERE} and on the project's roof construction and wind.")})
    rule = sum(f["l_foot_rule"] for f in faces)
    checked = sum(int(f["feet"] or 0) for f in faces) if status == "pass" else None
    bom = checked if status == "pass" else rule
    if status == "pass":
        spacings = sorted({f["s_foot_m"] for f in faces if f.get("s_foot_m")})
        purlins = sorted({f["purlin_spacing_m"]["value"] for f in faces})
        ks = sorted({f["k_foot"] for f in faces if f.get("k_foot")})
        where = ("feet on every purlin" if ks == [1] else f"feet on every {_ordinal(ks[0])} purlin" if len(ks) == 1 else "feet on the purlins (the spacing per face on the mounting detail)")
        note = f"{where} ({', '.join(f'{s:g} m' for s in spacings)}; purlins at {', '.join(f'{p:g} m' for p in purlins)}): the uplift check passed"
        if assumptions:
            note += " on assumptions (see the mounting detail)"
        if checked != rule:
            note += f"; the rule's {r.l_feet_per_rail} per rail would give {rule}"
    elif status == "fail":
        note = f"{r.l_feet_per_rail} per rail; the uplift check FAILED even with a foot on every purlin (the mounting detail): more screws per foot or a stronger fastener, the signing engineer's"
    else:
        note = f"{r.l_feet_per_rail} per rail; the uplift check is not checked ({'; '.join(missing) if missing else 'no rows'}): the rule's count"
    return {
        "status": status, "missing": missing, "assumptions": assumptions, "province": province, "wind": wind, "faces": faces,
        "fastener": {"description": m.fastener_description, "pullout_kn": m.fastener_pullout_kn, "pullout_source": m.fastener_pullout_source,
                     "screws_per_foot": m.screws_per_foot, "foot_spacing_max_m": m.foot_spacing_max_m, "foot_spacing_max_source": m.foot_spacing_max_source,
                     "rail_position_fraction": m.rail_position_fraction, "rail_kg_per_m": m.rail_kg_per_m},
        "l_foot": {"rule": rule, "checked": checked, "bom": bom, "note": note, "screws": sum(int(f["screws"] or 0) for f in faces) if status == "pass" else None},
        "warnings": warnings,
    }


def apply_uplift(doc: AssessmentDoc, rows: list, panel: Item, cfg: PricingConfig, boq) -> dict:
    """Run the check on a BoqResult: writes choices["uplift"], appends its warnings, and sets the L-foot line's count to the
    feet on purlins when the check passed (the rule's count with a note otherwise). Returns the block."""
    block = uplift_block(doc, rows, panel, cfg)
    boq.choices["uplift"] = block
    boq.warnings.extend(block["warnings"])
    lf = block["l_foot"]
    for i, line in enumerate(boq.lines):
        if line.role == "l_foot":
            boq.lines[i] = BomLine(line.code, lf["bom"] if block["status"] == "pass" else line.qty, line.role, lf["note"])
            break
    return block
