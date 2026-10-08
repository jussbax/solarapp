"""System sizing from the reconciled load profile and the roof's production profile.

All systems are hybrid inverters. The owner chooses off-grid (full battery,
no grid import; surplus beyond the battery is lost), net metering, or net
metering with a battery.

* Production is taken at the meter: the caller applies the system losses
  (inverter, wiring, soiling, other) to the per-kWp profile before sizing,
  so the array is sized on the energy the bill will later show.
* Faces: when an allocation plan is given, the sized panels are placed on the
  roof best face first (highest specific yield), whole rows from the eave,
  and the system's production is the sum over the panels on each face, not
  the whole-roof blend.
* PV, grid modes: the smallest whole number of panels whose annual production
  at the meter covers the annual consumption (net-zero annual energy), capped
  by the roof.
* PV, off-grid: the worst month's typical day must produce the day's
  consumption times a design margin; more panels are added until the balance
  leaves nothing unserved, first over the typical days and then over the real
  hourly year, up to what the roof holds.
* Battery: usable capacity equal to the energy it must deliver on the typical
  day with the largest unmet load (hours where solar is short), divided by the
  one-way efficiency, over the twelve months, times the days of autonomy (the
  evenings it must carry without sun; the owner's setting, default one).
  Reported in kWh, usable and nominal at the depth of discharge, no module
  rounding.
* The hourly year: with the real 8,760-hour production series the balance is
  run over the whole year with the battery state carried from hour to hour,
  and the result reports the loss-of-load hours and days and the unserved
  kWh (off-grid) or the hours the grid steps in (hybrid). Month totals and the
  typical-day charts then come from that run.
* Inverter: smallest catalogue size that covers the nameplate coincident
  peak, the surge of the largest motor at the stated surge factor, and the
  PV array at the allowed PV-to-inverter ratio. Parallel units if needed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .audit import DAYS_IN_MONTH

SYSTEM_KINDS = ("off_grid", "net_metering", "combination")
GRID_EXPORT_KINDS = ("net_metering", "combination")
FLOWS = ("direct", "charge", "discharge", "soc", "export", "curtailed", "imported")


@dataclass
class BatterySpec:
    depth_of_discharge: float = 0.85
    round_trip_efficiency: float = 0.92
    max_c_rate: float = 0.5          # kW of charge or discharge per kWh installed
    days_of_autonomy: float = 1.0    # evenings the battery must carry without sun (1 = the worst typical night)


@dataclass
class OffGridRules:
    pv_margin: float = 1.25      # worst-month production over consumption, a cloudy-spell safety factor


@dataclass
class InverterRules:
    sizes_kw: list[float] = field(default_factory=lambda: [6.0, 8.0, 10.0, 12.0])
    surge_factor: float = 2.0        # 200% of rated
    pv_ratio_max: float = 1.3        # PV kWp per inverter kW


@dataclass
class FaceSlot:
    """One roof face as the sizing sees it: how many panels it holds and what each of them makes."""
    face_id: str
    name: str
    capacity: int
    profile_per_panel: np.ndarray                 # [12, 24] kW per panel, at the panels
    rows: list[int] = field(default_factory=list)  # fitted rows from the eave, panels per row
    hourly_per_panel: Optional[np.ndarray] = None  # [N] kW per panel over the real year, at the panels
    specific_yield_kwh_per_kwp: float = 0.0


@dataclass
class AllocationPlan:
    """Where the sized panels go: faces in order of specific yield, whole rows from the eave."""
    slots: list[FaceSlot]
    loss_factor: float = 1.0
    hour_month: Optional[np.ndarray] = None   # [N] local month 1-12 of each hour of the year
    hour_local: Optional[np.ndarray] = None   # [N] local hour 0-23

    @property
    def capacity(self) -> int:
        return sum(s.capacity for s in self.slots)

    @property
    def has_year(self) -> bool:
        return self.hour_month is not None and self.hour_local is not None and all(s.hourly_per_panel is not None for s in self.slots)

    def allocate(self, n_panels: int) -> list[tuple[FaceSlot, int]]:
        out: list[tuple[FaceSlot, int]] = []
        left = max(int(n_panels), 0)
        for s in self.slots:
            take = min(s.capacity, left)
            if take > 0:
                out.append((s, take))
            left -= take
            if left <= 0:
                break
        return out

    def production(self, n_panels: int) -> tuple[np.ndarray, Optional[np.ndarray]]:
        """Typical-day [12, 24] kW and the hourly year [N] kW at the meter for n panels on their faces."""
        prof = np.zeros((12, 24))
        year = np.zeros(len(self.hour_month)) if self.has_year else None
        for s, take in self.allocate(n_panels):
            prof += take * s.profile_per_panel
            if year is not None:
                year += take * s.hourly_per_panel
        prof *= self.loss_factor
        if year is not None:
            year *= self.loss_factor
        return prof, year

    def rows_used(self, slot: FaceSlot, take: int) -> list[int]:
        rows, left = [], take
        for r in slot.rows:
            if left <= 0:
                break
            rows.append(min(r, left))
            left -= rows[-1]
        if left > 0:
            rows.append(left)
        return rows


def plan_from_faces(faces: list[dict], loss_factor: float, hour_month: Optional[np.ndarray] = None, hour_local: Optional[np.ndarray] = None) -> AllocationPlan:
    """Build the plan from per-face simulation data: each dict carries face_id, name, panel_count (what the face
    holds), hourly_profile_kw [12][24] for that count, specific_yield_kwh_per_kwp, rows (fitted rows from the
    eave) and, when available, hourly_kw [N] for that count. Faces are ordered by specific yield, best first."""
    slots: list[FaceSlot] = []
    for f in faces:
        n = int(f.get("panel_count") or 0)
        if n <= 0:
            continue
        prof = np.asarray(f["hourly_profile_kw"], float) / n
        year = f.get("hourly_kw")
        slots.append(FaceSlot(
            face_id=str(f["face_id"]), name=str(f.get("name") or f["face_id"]), capacity=n, profile_per_panel=prof,
            rows=[int(r) for r in (f.get("rows") or []) if int(r) > 0],
            hourly_per_panel=(np.asarray(year, float) / n) if year is not None else None,
            specific_yield_kwh_per_kwp=float(f.get("specific_yield_kwh_per_kwp") or 0.0),
        ))
    slots.sort(key=lambda s: -s.specific_yield_kwh_per_kwp)
    return AllocationPlan(slots, loss_factor, hour_month, hour_local)


@dataclass
class DayBalance:
    load: np.ndarray
    production: np.ndarray
    direct: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    soc: np.ndarray
    export: np.ndarray
    curtailed: np.ndarray
    imported: np.ndarray


def balance_day(load_kw: np.ndarray, prod_kw: np.ndarray, usable_kwh: float, power_kw: float, kind: str, eff_rt: float) -> DayBalance:
    """Steady-state hourly balance of one typical day (the day is repeated until the battery state settles)."""
    eff = math.sqrt(max(eff_rt, 1e-6))
    soc = 0.0
    n = 24
    arrays = {k: np.zeros(n) for k in FLOWS}
    for cycle in range(4):
        for h in range(n):
            p, l = float(prod_kw[h]), float(load_kw[h])
            direct = min(p, l)
            surplus, deficit = p - direct, l - direct
            charge = discharge = 0.0
            if usable_kwh > 0:
                charge = min(surplus, (usable_kwh - soc) / eff, power_kw)
                soc += charge * eff
                discharge = min(deficit, soc * eff, power_kw)
                soc -= discharge / eff
            rest = surplus - charge
            export = rest if kind in GRID_EXPORT_KINDS else 0.0
            curtailed = rest - export
            imported = deficit - discharge
            if cycle == 3:
                arrays["direct"][h], arrays["charge"][h], arrays["discharge"][h] = direct, charge, discharge
                arrays["soc"][h], arrays["export"][h], arrays["curtailed"][h], arrays["imported"][h] = soc, export, curtailed, imported
    return DayBalance(load=np.asarray(load_kw, float), production=np.asarray(prod_kw, float), **arrays)


def balance_year(load_kw: np.ndarray, prod_kw: np.ndarray, usable_kwh: float, power_kw: float, kind: str, eff_rt: float) -> dict[str, np.ndarray]:
    """Hour-by-hour balance over the real year with the battery state carried from hour to hour. The year is run
    twice and the second pass is reported, so the starting state is the one the previous year leaves behind."""
    eff = math.sqrt(max(eff_rt, 1e-6))
    load = [float(x) for x in np.asarray(load_kw, float)]
    prod = [float(x) for x in np.asarray(prod_kw, float)]
    n = len(load)
    export_ok = kind in GRID_EXPORT_KINDS
    has_battery = usable_kwh > 0
    out = {k: [0.0] * n for k in FLOWS}
    soc = 0.0
    for cycle in range(2):
        record = cycle == 1
        for h in range(n):
            p, l = prod[h], load[h]
            if p >= l:
                direct, surplus, deficit = l, p - l, 0.0
            else:
                direct, surplus, deficit = p, 0.0, l - p
            charge = discharge = 0.0
            if has_battery:
                if surplus > 0.0:
                    charge = min(surplus, (usable_kwh - soc) / eff, power_kw)
                    soc += charge * eff
                elif deficit > 0.0:
                    discharge = min(deficit, soc * eff, power_kw)
                    soc -= discharge / eff
            rest = surplus - charge
            if record:
                out["direct"][h] = direct
                out["charge"][h] = charge
                out["discharge"][h] = discharge
                out["soc"][h] = soc
                out["export"][h] = rest if export_ok else 0.0
                out["curtailed"][h] = 0.0 if export_ok else rest
                out["imported"][h] = deficit - discharge
    res = {k: np.asarray(v, float) for k, v in out.items()}
    res["load"], res["production"] = np.asarray(load, float), np.asarray(prod, float)
    return res


def _clean(kwh: float) -> float:
    """Drop floating-point residue so an exactly sized battery reads as zero unserved."""
    return kwh if kwh > 1e-6 else 0.0


def pick_inverter(required_kw: float, rules: InverterRules) -> tuple[float, int]:
    sizes = sorted(rules.sizes_kw)
    for s in sizes:
        if s >= required_kw - 1e-9:
            return s, 1
    biggest = sizes[-1]
    return biggest, int(math.ceil(required_kw / biggest))


def _day_index(hour_local: np.ndarray) -> np.ndarray:
    """Which local day each hour belongs to: a new day starts at every local midnight."""
    return np.cumsum(np.asarray(hour_local) == 0)


def size_system(
    load_kw: np.ndarray,            # [12, 24] kW
    prod_per_kwp_kw: np.ndarray,    # [12, 24] kW per kWp of the roof's selected configuration, at the meter
    roof_max_panels: int,
    panel_wp: float,
    kind: str,
    peak_load_kw: float,
    largest_motor_kw: float,
    largest_motor_multiplier: float,
    battery: BatterySpec | None = None,
    inverter: InverterRules | None = None,
    offgrid: OffGridRules | None = None,
    plan: AllocationPlan | None = None,
) -> dict:
    battery = battery or BatterySpec()
    inverter = inverter or InverterRules()
    offgrid = offgrid or OffGridRules()
    if kind not in SYSTEM_KINDS:
        raise ValueError(f"unknown system kind {kind!r}")
    load = np.asarray(load_kw, float)
    per_kwp = np.asarray(prod_per_kwp_kw, float)
    days = np.array(DAYS_IN_MONTH, float)
    warnings: list[dict] = []
    off_grid = kind == "off_grid"
    with_battery = kind in ("off_grid", "combination")
    panel_kwp = panel_wp / 1000.0
    autonomy = max(float(battery.days_of_autonomy), 0.0)
    loss_factor = plan.loss_factor if plan is not None else 1.0

    annual_consumption = float((load.sum(axis=1) * days).sum())
    yield_per_kwp = float((per_kwp.sum(axis=1) * days).sum())
    roof_max_kwp = roof_max_panels * panel_wp / 1000.0
    daily_load = load.sum(axis=1)
    daily_yield = per_kwp.sum(axis=1)
    use_year = plan is not None and plan.has_year
    if use_year:
        hour_month = np.asarray(plan.hour_month, int)
        hour_local = np.asarray(plan.hour_local, int)
        load_year = load[hour_month - 1, hour_local]
        day_idx = _day_index(hour_local)

    def production_for(n_panels: int) -> tuple[np.ndarray, Optional[np.ndarray]]:
        if plan is not None:
            return plan.production(n_panels)
        return per_kwp * (n_panels * panel_kwp), None

    def annual_kwh(n_panels: int) -> float:
        prof, year = production_for(n_panels)
        return float(year.sum()) if year is not None else float((prof.sum(axis=1) * days).sum())

    # ---- target array
    if off_grid:
        ratios = [offgrid.pv_margin * dl / dy for dl, dy in zip(daily_load, daily_yield) if dy > 0]
        target_kwp = max(ratios) if ratios else 0.0
        target_panels = int(math.ceil(target_kwp / panel_kwp - 1e-9)) if panel_kwp > 0 else 0
    else:
        target_kwp = annual_consumption / yield_per_kwp if yield_per_kwp > 0 else 0.0
        target_panels = int(math.ceil(target_kwp / panel_kwp - 1e-9)) if panel_kwp > 0 else 0
        if plan is not None and target_panels > 0:
            # the blend is only a first guess: the panels sit on the best faces first, so find the smallest count
            # whose production on those faces covers the year, within the roof
            n = max(min(target_panels, roof_max_panels), 1)
            while n < roof_max_panels and annual_kwh(n) < annual_consumption - 1e-6:
                n += 1
            while n > 1 and annual_kwh(n - 1) >= annual_consumption - 1e-6:
                n -= 1
            if annual_kwh(n) >= annual_consumption - 1e-6:
                target_panels = n
                target_kwp = n * panel_kwp
            else:  # even the full roof falls short: report the need from the blend
                target_panels = max(target_panels, roof_max_panels + 1)
    panels = max(min(target_panels, roof_max_panels), 0)

    def battery_for(prod_: np.ndarray, kwp_: float) -> tuple[float, float, float]:
        usable_ = 0.0
        if with_battery and kwp_ > 0:
            big = 1e6
            one_way = math.sqrt(max(battery.round_trip_efficiency, 1e-6))
            # with an unlimited battery, the day's discharge is the unmet load solar can shift; the stored energy
            # needed for it is that discharge over the one-way efficiency; the autonomy multiplies it
            needs = [float(balance_day(load[m], prod_[m], big, big, kind, battery.round_trip_efficiency).discharge.sum()) / one_way for m in range(12)]
            usable_ = (max(needs) if needs else 0.0) * autonomy
        installed_ = usable_ / battery.depth_of_discharge if battery.depth_of_discharge > 0 else usable_
        return usable_, installed_, installed_ * battery.max_c_rate

    def run(n_panels: int, year: bool) -> dict:
        """Battery for this array, then the hourly balance: over the real year when asked and available, else
        over every month's typical day."""
        kwp_ = n_panels * panel_kwp
        prod_, prod_year = production_for(n_panels)
        usable_, installed_, power_ = battery_for(prod_, kwp_)
        monthly_, profiles_ = [], {}
        tot_ = {k: 0.0 for k in ("consumption", "production", "direct", "charge", "discharge", "export", "curtailed", "imported")}
        hourly_block = None
        if year and use_year and prod_year is not None:
            b = balance_year(load_year, prod_year, usable_, power_, kind, battery.round_trip_efficiency)
            keys = {"consumption": "load", "production": "production", "direct": "direct", "charge": "charge", "discharge": "discharge", "export": "export", "curtailed": "curtailed", "imported": "imported"}
            for m in range(12):
                sel = hour_month == m + 1
                sums = {k: float(b[src][sel].sum()) for k, src in keys.items()}
                row = {
                    "month": m + 1, "days": int(days[m]),
                    "consumption_kwh": sums["consumption"], "production_kwh": sums["production"],
                    "direct_kwh": sums["direct"], "battery_kwh": sums["discharge"],
                    "export_kwh": sums["export"], "curtailed_kwh": sums["curtailed"],
                    "import_kwh": 0.0 if off_grid else _clean(sums["imported"]),
                    "unserved_kwh": _clean(sums["imported"]) if off_grid else 0.0,
                }
                monthly_.append(row)
                for k in tot_:
                    tot_[k] += _clean(sums[k]) if k == "imported" else sums[k]
                prof = {}
                for name, src in (("load", "load"), ("production", "production"), ("direct", "direct"), ("charge", "charge"), ("discharge", "discharge"), ("soc", "soc"), ("export", "export"), ("curtailed", "curtailed"), ("imported", "imported")):
                    arr = b[src]
                    prof[name] = [round(float(arr[sel & (hour_local == h)].mean()), 4) if (sel & (hour_local == h)).any() else 0.0 for h in range(24)]
                profiles_[m + 1] = prof
            short = b["imported"] > 1e-6
            hours = int(short.sum())
            days_short = int(len(np.unique(day_idx[short]))) if hours else 0
            by_month = [{"month": m + 1, "hours": int((short & (hour_month == m + 1)).sum()), "kwh": float(b["imported"][short & (hour_month == m + 1)].sum())} for m in range(12)]
            worst = max(by_month, key=lambda x: x["kwh"]) if hours else None
            hourly_block = {
                "available": True, "hours": int(len(load_year)),
                "loss_of_load_hours": hours, "loss_of_load_days": days_short, "unserved_kwh": _clean(float(b["imported"][short].sum())),
                "meaning": "unserved" if off_grid else "grid_covered", "worst_month": worst["month"] if worst else None, "months": by_month,
            }
        else:
            for m in range(12):
                b = balance_day(load[m], prod_[m], usable_, power_, kind, battery.round_trip_efficiency)
                row = {
                    "month": m + 1, "days": int(days[m]),
                    "consumption_kwh": float(b.load.sum() * days[m]), "production_kwh": float(b.production.sum() * days[m]),
                    "direct_kwh": float(b.direct.sum() * days[m]), "battery_kwh": float(b.discharge.sum() * days[m]),
                    "export_kwh": float(b.export.sum() * days[m]), "curtailed_kwh": float(b.curtailed.sum() * days[m]),
                    "import_kwh": 0.0 if off_grid else _clean(float(b.imported.sum() * days[m])),
                    "unserved_kwh": _clean(float(b.imported.sum() * days[m])) if off_grid else 0.0,
                }
                monthly_.append(row)
                for k, key in (("consumption", "consumption_kwh"), ("production", "production_kwh"), ("direct", "direct_kwh"), ("discharge", "battery_kwh"), ("export", "export_kwh"), ("curtailed", "curtailed_kwh")):
                    tot_[k] += row[key]
                tot_["imported"] += _clean(float(b.imported.sum() * days[m]))
                tot_["charge"] += float(b.charge.sum() * days[m])
                profiles_[m + 1] = {
                    "load": b.load.round(4).tolist(), "production": b.production.round(4).tolist(), "direct": b.direct.round(4).tolist(),
                    "charge": b.charge.round(4).tolist(), "discharge": b.discharge.round(4).tolist(), "soc": b.soc.round(4).tolist(),
                    "export": b.export.round(4).tolist(), "curtailed": b.curtailed.round(4).tolist(), "imported": b.imported.round(4).tolist(),
                }
        return {"kwp": kwp_, "usable": usable_, "installed": installed_, "power": power_, "monthly": monthly_, "profiles": profiles_, "tot": tot_, "hourly_year": hourly_block}

    r = run(panels, year=False)
    autonomy_met = True
    if off_grid:
        # add panels until the typical days leave nothing unserved, within the roof
        while r["tot"]["imported"] > 1e-6 and panels < roof_max_panels:
            panels += 1
            r = run(panels, year=False)
        # the worst month must keep the design margin on the faces the panels actually occupy
        while panels < roof_max_panels and any(m["production_kwh"] < offgrid.pv_margin * m["consumption_kwh"] - 1e-6 for m in r["monthly"]):
            panels += 1
            r = run(panels, year=False)
        if use_year:
            # then over the real year: the battery sized for the autonomy must never run out
            r = run(panels, year=True)
            while r["tot"]["imported"] > 1e-6 and panels < roof_max_panels:
                panels += 1
                r = run(panels, year=True)
            autonomy_met = r["tot"]["imported"] <= 1e-6
        roof_limited = r["tot"]["imported"] > 1e-6 or target_panels > roof_max_panels
    else:
        roof_limited = target_panels > roof_max_panels
        if use_year:
            r = run(panels, year=True)
    kwp = r["kwp"]
    usable, installed, battery_power = r["usable"], r["installed"], r["power"]
    monthly, profiles, tot = r["monthly"], r["profiles"], r["tot"]
    hourly_year = r["hourly_year"] or {"available": False}

    if roof_limited and off_grid:
        warnings.append({"code": "roof_limited", "message": f"Off-grid needs about {max(target_kwp, kwp):.1f} kWp but the roof holds {roof_max_kwp:.2f} kWp. About {tot['imported']:,.0f} kWh a year would go unserved. Consider net metering with a battery, or cutting load."})
    elif roof_limited:
        warnings.append({"code": "roof_limited", "message": f"Net-zero needs about {target_kwp:.1f} kWp but the roof holds {roof_max_kwp:.2f} kWp; the system is sized to what the roof can provide."})
    if off_grid and use_year and not autonomy_met:
        hy = hourly_year
        warnings.append({"code": "autonomy_not_met", "message": (
            f"Even with the full roof ({panels} panels) and a battery for {autonomy:g} {'evening' if autonomy == 1 else 'evenings'} without sun, "
            f"a real year of weather leaves about {hy['loss_of_load_hours']} hours on {hy['loss_of_load_days']} days without power "
            f"({hy['unserved_kwh']:,.0f} kWh). A bigger battery (more days of autonomy under Pricing settings › System sizing), less load, or net metering with a battery would close it.")})
    elif off_grid and use_year and autonomy_met and panels > target_panels:
        warnings.append({"code": "autonomy_panels", "message": f"The real year of weather needed {panels - target_panels} more {'panel' if panels - target_panels == 1 else 'panels'} than the typical days to keep the battery from running out."})
    if panels == 0:
        warnings.append({"code": "no_pv", "message": "Nothing to size: no panels fit, or the audit has no consumption."})

    served = tot["direct"] + tot["discharge"]
    coverage_pct = served / tot["consumption"] * 100.0 if tot["consumption"] > 0 else 0.0
    self_consumption_pct = (tot["direct"] + tot["charge"]) / tot["production"] * 100.0 if tot["production"] > 0 else 0.0
    net_kwh = served - tot["consumption"] if off_grid else tot["production"] - tot["consumption"]

    # --- faces the system uses
    faces_block = None
    if plan is not None:
        faces_block = []
        for s, take in plan.allocate(panels):
            kwh = float((s.profile_per_panel.sum(axis=1) * days).sum()) * take * loss_factor
            if s.hourly_per_panel is not None:
                kwh = float(s.hourly_per_panel.sum()) * take * loss_factor
            faces_block.append({
                "face_id": s.face_id, "name": s.name, "panels": take, "capacity": s.capacity, "rows": plan.rows_used(s, take),
                "kwp": take * panel_kwp, "annual_kwh": kwh, "specific_yield_kwh_per_kwp": s.specific_yield_kwh_per_kwp,
            })

    # --- inverter
    surge_req = (peak_load_kw + largest_motor_kw * (largest_motor_multiplier - 1.0)) / inverter.surge_factor if inverter.surge_factor > 0 else peak_load_kw
    pv_req = kwp / inverter.pv_ratio_max if inverter.pv_ratio_max > 0 else kwp
    required = max(peak_load_kw, surge_req, pv_req)
    inv_kw, inv_units = pick_inverter(required, inverter) if required > 0 else (min(inverter.sizes_kw), 1)
    if inv_units > 1:
        warnings.append({"code": "inverter_parallel", "message": f"The load needs {required:.1f} kW, more than the largest inverter in the list, so {inv_units} × {inv_kw:g} kW in parallel are used."})
    binding = "peak load" if required == peak_load_kw else ("motor surge" if required == surge_req else "PV array")

    return {
        "kind": kind,
        "annual_consumption_kwh": annual_consumption,
        "annual_yield_kwh_per_kwp": yield_per_kwp,
        "loss_factor": loss_factor,
        "target_kwp": target_kwp,
        "target_panels": target_panels,
        "roof_max_panels": roof_max_panels,
        "roof_max_kwp": roof_max_kwp,
        "roof_limited": roof_limited,
        "panels": panels,
        "kwp": kwp,
        "annual_production_kwh": tot["production"],
        "annual_production_dc_kwh": tot["production"] / loss_factor if loss_factor > 0 else tot["production"],
        "system_yield_kwh_per_kwp": tot["production"] / kwp if kwp > 0 else 0.0,   # on the faces the panels occupy, at the meter
        "coverage_pct": coverage_pct,
        "self_consumption_pct": self_consumption_pct,
        "annual_direct_kwh": tot["direct"],
        "annual_battery_kwh": tot["discharge"],
        "annual_export_kwh": tot["export"],
        "annual_curtailed_kwh": tot["curtailed"],
        "annual_import_kwh": 0.0 if off_grid else tot["imported"],
        "annual_unserved_kwh": tot["imported"] if off_grid else 0.0,
        "net_annual_kwh": net_kwh,
        "offgrid": {"pv_margin": offgrid.pv_margin} if off_grid else None,
        "battery": {
            "usable_kwh": usable, "installed_kwh": installed, "power_kw": battery_power,
            "depth_of_discharge": battery.depth_of_discharge, "round_trip_efficiency": battery.round_trip_efficiency,
            "days_of_autonomy": autonomy if with_battery else None,
        },
        "inverter": {
            "size_kw": inv_kw, "units": inv_units, "required_kw": required, "binding": binding,
            "peak_load_kw": peak_load_kw, "surge_requirement_kw": surge_req, "pv_requirement_kw": pv_req,
            "largest_motor_kw": largest_motor_kw, "largest_motor_multiplier": largest_motor_multiplier,
            "surge_factor": inverter.surge_factor, "pv_ratio_max": inverter.pv_ratio_max, "sizes_kw": inverter.sizes_kw,
        },
        "faces": faces_block,
        "hourly_year": hourly_year,
        "monthly": monthly,
        "profiles": profiles,
        "warnings": warnings,
    }
