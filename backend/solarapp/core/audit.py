"""Energy audit: appliances with usage windows become hourly load profiles,
then the profile is reconciled with the electricity bill.

Conventions (DECISIONS.md, energy audit section):

* A usage window has a start and an end time, the weekdays it applies to and
  the months it applies to. An end at or before the start crosses midnight;
  equal start and end means 24 hours. Duration is derived, never typed.
* Average draw inside a window = nameplate input watts x quantity x duty
  factor. The duty factor defaults from the appliance category and is
  editable per appliance. Nameplate without a duty factor overstates
  cycling loads (refrigerators, aircon, thermostat heaters) badly.
* Peak load for inverter sizing follows the field sheet's hour table: for
  each hour, every appliance whose window touches that hour is added at
  quantity x nameplate x duty factor; the peak is the largest hour over the
  week and the twelve months. The table itself is returned for the peak day.
* Reconciliation with the bill: appliances in "uncertain" categories are
  scaled first, within a floor and a nameplate ceiling, then any remaining
  gap is spread proportionally over all existing appliances. Future
  appliances never count against the bill; a future appliance whose type the
  household already has inherits that type's scale (a planned second aircon
  behaves like the existing one), otherwise it is used as typed.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

MINUTES = 1440
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
UNCERTAIN_FLOOR = 0.15  # never scale an uncertain appliance below this share of its default average
GAP_WARN_PCT = 10.0


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    duty: float
    uncertain: bool
    w_min: Optional[float]
    w_max: Optional[float]
    start_multiplier: float  # inrush of one unit relative to nameplate, for the inverter surge check
    note: str


_C = Category
CATEGORIES: dict[str, Category] = {c.id: c for c in [
    _C("refrigerator", "Refrigerator", 0.35, True, 60, 400, 3.0, "Compressor runs 33-40% of the time in a typical kitchen; inverter models run longer at lower power with a similar average."),
    _C("freezer", "Chest freezer", 0.40, True, 60, 400, 3.0, "Slightly higher duty than a refrigerator."),
    _C("aircon_inverter", "Aircon, inverter", 0.55, True, 300, 3500, 1.0, "Full input during pull-down, then 30-50% of rated at the setpoint; 55% over a long window in Philippine heat."),
    _C("aircon_non_inverter", "Aircon, non-inverter", 0.70, True, 400, 3500, 3.0, "Compressor cycles on and off; 60-80% duty at usual setpoints in the tropics."),
    _C("fan", "Electric fan", 0.80, False, 20, 150, 1.0, "Nameplate is top speed; medium speed draws about 80%."),
    _C("lighting", "Lighting", 1.00, False, 3, 100, 1.0, "Draws nameplate while on."),
    _C("tv", "Television", 0.80, False, 30, 300, 1.0, "Nameplate is maximum; typical picture draws about 80%."),
    _C("computer_desktop", "Desktop computer", 0.60, False, 100, 500, 1.0, "Power supply rating is far above typical draw."),
    _C("laptop", "Laptop", 0.50, False, 30, 120, 1.0, "Adapter rating is about twice the average draw."),
    _C("phone_charger", "Phone or tablet charger", 0.50, False, 5, 30, 1.0, "Full charge rate only for part of the charge."),
    _C("router_network", "Router or modem", 1.00, False, 5, 30, 1.0, "Constant small load."),
    _C("security_camera", "Security camera or DVR", 1.00, False, 3, 60, 1.0, "Constant small load."),
    _C("rice_cooker", "Rice cooker", 0.50, False, 300, 1500, 1.0, "Full power while cooking, then a small keep-warm element; enter the cooking window only."),
    _C("electric_kettle", "Electric kettle", 0.35, False, 1000, 3000, 1.0, "Full power only for the few minutes of each boil inside the window."),
    _C("coffee_maker", "Coffee maker", 0.60, False, 500, 1500, 1.0, "Brewing at full power, then a warming plate."),
    _C("microwave", "Microwave oven", 1.00, False, 600, 1500, 1.0, "Draws nameplate while running; windows are minutes long."),
    _C("induction_cooker", "Induction or electric cooker", 0.70, False, 1000, 2500, 1.0, "Power level is usually below maximum."),
    _C("oven_toaster", "Oven or toaster", 0.60, False, 500, 2500, 1.0, "Thermostat cycling once hot."),
    _C("water_dispenser", "Hot and cold water dispenser", 0.08, True, 300, 700, 1.0, "Measured units use 0.7-1.1 kWh per day on a 24 hour window, about 8% of a 500 W nameplate."),
    _C("water_heater_tankless", "Shower water heater, tankless", 1.00, False, 3000, 6000, 1.0, "Draws nameplate while the shower runs; enter shower windows."),
    _C("water_heater_storage", "Storage water heater", 0.30, True, 1000, 3000, 1.0, "Thermostat cycling to hold temperature."),
    _C("washing_machine", "Washing machine", 0.60, False, 250, 2500, 2.0, "Motor alternates agitate, pause and spin; models with a water heater carry a 2000 W class nameplate that is only drawn on hot cycles."),
    _C("dryer", "Clothes dryer", 0.80, False, 1500, 3000, 1.0, "Heater cycles near the end of the cycle."),
    _C("steam_iron", "Flat or steam iron", 0.50, False, 1000, 2200, 1.0, "Thermostat cycling, about half the time on."),
    _C("water_pump", "Water pump", 0.60, True, 250, 1500, 3.0, "Pressure pumps cycle; enter the hours water is being used."),
    _C("pressure_washer", "Pressure washer", 0.80, False, 1200, 2500, 3.0, "Near nameplate while spraying."),
    _C("sterilizer", "Sterilizer or bottle warmer", 0.80, False, 300, 800, 1.0, "Heater runs most of a short cycle."),
    _C("ev_charger", "Electric vehicle charger", 1.00, False, 1500, 7500, 1.0, "Draws nameplate until the vehicle is charged."),
    _C("dehumidifier", "Dehumidifier or air purifier", 0.60, False, 50, 600, 1.0, "Compressor or fan cycling."),
    _C("other", "Other", 1.00, False, None, None, 1.0, "No default knowledge; nameplate is used."),
]}


def category(cid: str) -> Category:
    return CATEGORIES.get(cid, CATEGORIES["other"])


def categories_for_ui() -> list[dict]:
    return [
        {"id": c.id, "label": c.label, "duty": c.duty, "uncertain": c.uncertain, "w_min": c.w_min, "w_max": c.w_max, "note": c.note}
        for c in CATEGORIES.values()
    ]


def parse_hhmm(value: str) -> int:
    h, m = value.strip().split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 24 and 0 <= m < 60) or (h == 24 and m != 0):
        raise ValueError(f"bad time {value!r}")
    return (h * 60 + m) % MINUTES


def window_mask(start: str, end: str) -> np.ndarray:
    """Boolean minute mask over one day. end <= start wraps past midnight; equal means 24 h."""
    s, e = parse_hhmm(start), parse_hhmm(end)
    mask = np.zeros(MINUTES, dtype=bool)
    if s == e:
        mask[:] = True
    elif e > s:
        mask[s:e] = True
    else:
        mask[s:] = True
        mask[:e] = True
    return mask


@dataclass
class Window:
    start: str
    end: str
    days: list[int] = field(default_factory=lambda: list(range(7)))      # 0 = Monday
    months: list[int] = field(default_factory=lambda: list(range(1, 13)))


@dataclass
class Appliance:
    id: str
    name: str
    category: str
    input_power_w: float
    quantity: int = 1
    duty_factor: Optional[float] = None   # None = category default
    status: str = "existing"              # existing | future | retiring
    windows: list[Window] = field(default_factory=list)

    @property
    def cat(self) -> Category:
        return category(self.category)

    @property
    def duty(self) -> float:
        return float(self.duty_factor) if self.duty_factor is not None else self.cat.duty

    @property
    def uncertain(self) -> bool:
        return self.cat.uncertain


@dataclass
class ApplianceProfile:
    """Per-appliance weekly shapes, before any scaling."""
    appliance: Appliance
    energy_wh: np.ndarray        # [12, 7, 24] Wh per hour at duty (zero in months not active)
    active_hour: np.ndarray      # [12, 7, 24] True when the appliance is on at any minute of the hour
    hours_per_day: float         # average over the week, months where active
    days_per_week: int           # weekdays with any usage
    hours_per_use_day: float     # average hours on the days it runs
    warnings: list[dict]

    @property
    def duty_watts(self) -> float:
        return self.appliance.quantity * self.appliance.input_power_w * self.appliance.duty


def build_profile(a: Appliance) -> ApplianceProfile:
    energy = np.zeros((12, 7, 24), dtype=np.float64)
    warnings: list[dict] = []
    avg_w = a.quantity * a.input_power_w * a.duty
    on_minutes = np.zeros((12, 7, MINUTES), dtype=bool)
    for w in a.windows:
        try:
            mask = window_mask(w.start, w.end)
        except ValueError as e:
            warnings.append({"code": "bad_window", "message": f"{a.name}: {e}"})
            continue
        for m in w.months:
            for d in w.days:
                if 1 <= m <= 12 and 0 <= d <= 6:
                    on_minutes[m - 1, d] |= mask
    if not a.windows:
        warnings.append({"code": "no_windows", "message": f"{a.name}: no usage window, so it adds nothing. Add a window or remove the appliance."})
    minutes_per_hour = on_minutes.reshape(12, 7, 24, 60).sum(axis=3)
    energy = minutes_per_hour / 60.0 * avg_w
    active_hour = minutes_per_hour > 0
    active_months = on_minutes.reshape(12, -1).any(axis=1)
    hours_by_day = on_minutes.reshape(12, 7, MINUTES).sum(axis=2) / 60.0           # [12, 7]
    hours = hours_by_day.mean(axis=1)                                               # per month, averaged over the week
    hours_per_day = float(hours[active_months].mean()) if active_months.any() else 0.0
    use_days = hours_by_day.max(axis=0) > 0                                         # [7] weekdays with any usage
    days_per_week = int(use_days.sum())
    hours_per_use_day = float(hours_by_day[active_months][:, use_days].mean()) if (active_months.any() and days_per_week) else 0.0
    c = a.cat
    if c.w_min is not None and c.w_max is not None and a.input_power_w > 0:
        if a.input_power_w > c.w_max * 1.5 or a.input_power_w < c.w_min / 1.5:
            warnings.append({
                "code": "nameplate_out_of_range",
                "message": f"{a.name}: {a.input_power_w:g} W is outside the usual {c.w_min:g}-{c.w_max:g} W for {c.label.lower()}; check the nameplate.",
            })
    return ApplianceProfile(a, energy, active_hour, hours_per_day, days_per_week, hours_per_use_day, warnings)


@dataclass
class Bill:
    id: str
    billing_month: str          # "YYYY-MM"
    kwh: float
    days: Optional[int] = None  # billing period length; defaults to the calendar month
    amount_php: Optional[float] = None
    utility: str = ""

    @property
    def month(self) -> int:
        return int(self.billing_month.split("-")[1])

    @property
    def year(self) -> int:
        return int(self.billing_month.split("-")[0])

    @property
    def period_days(self) -> int:
        if self.days:
            return int(self.days)
        return calendar.monthrange(self.year, self.month)[1]


@dataclass
class AuditResult:
    appliances: list[dict]
    load_kw: np.ndarray                 # [12, 24] average kW for sizing (existing + future, reconciled)
    load_kw_unreconciled: np.ndarray    # [12, 24]
    peak_kw: float                      # hour-table peak: largest hour of summed duty-weighted draws
    peak_avg_kw: float                  # highest hourly average of energy (for reference)
    peak_detail: dict                   # when the peak hour occurs and which appliances form it
    hour_table: list[dict]              # the peak day's 24 rows: appliances and totals
    largest_motor_kw: float
    largest_motor_multiplier: float
    daily_kwh_by_month: list[float]     # sizing set, reconciled
    annual_kwh: float
    audit_vs_bill: Optional[dict]
    warnings: list[dict]
    future_daily_kwh: float
    weekday_profiles_kw: dict           # month -> [7][24] kW for charts (sizing set)


def _daily_kwh(energy: np.ndarray) -> np.ndarray:
    """[12, 7, 24] Wh -> [12] kWh per day averaged over the week."""
    return energy.sum(axis=2).mean(axis=1) / 1000.0


def run_audit(appliances: list[Appliance], bills: list[Bill], reconcile: bool = True) -> AuditResult:
    profiles = [build_profile(a) for a in appliances]
    warnings: list[dict] = [w for p in profiles for w in p.warnings]

    existing = [p for p in profiles if p.appliance.status in ("existing", "retiring")]
    sizing_set = [p for p in profiles if p.appliance.status in ("existing", "future")]

    # --- reconciliation with the bill(s), on the existing set
    scale: dict[str, float] = {p.appliance.id: 1.0 for p in profiles}
    audit_vs_bill: Optional[dict] = None
    valid_bills = [b for b in bills if b.kwh > 0]
    if not valid_bills:
        warnings.append({"code": "no_bills", "message": "No bill entered, so the audit is used as typed. Add the latest bill to check it against real usage."})
    elif existing:
        billed = sum(b.kwh for b in valid_bills)
        est_u = est_f = 0.0
        per_app_est: dict[str, float] = {}
        for p in existing:
            daily = _daily_kwh(p.energy_wh)
            e = sum(daily[b.month - 1] * b.period_days for b in valid_bills)
            per_app_est[p.appliance.id] = e
            if p.appliance.uncertain:
                est_u += e
            else:
                est_f += e
        audit_total = est_u + est_f
        gap_pct = ((audit_total - billed) / billed * 100.0) if billed > 0 else 0.0
        s_u = s_all = 1.0
        floor_hit = ceiling_hit = False
        if reconcile and audit_total > 0:
            if est_u > 0:
                wanted = (billed - est_f) / est_u
                ceiling = min(1.0 / p.appliance.duty for p in existing if p.appliance.uncertain)
                s_u = min(max(wanted, UNCERTAIN_FLOOR), ceiling)
                floor_hit = wanted < UNCERTAIN_FLOOR
                ceiling_hit = wanted > ceiling
            after_u = est_f + s_u * est_u
            s_all = billed / after_u if after_u > 0 else 1.0
            s_u, s_all = float(s_u), float(s_all)
            for p in existing:
                scale[p.appliance.id] = s_all * (s_u if p.appliance.uncertain else 1.0)
            existing_categories = {p.appliance.category for p in existing}
            for p in profiles:
                if p.appliance.status == "future" and p.appliance.category in existing_categories:
                    scale[p.appliance.id] = s_all * (s_u if p.appliance.uncertain else 1.0)
        if abs(gap_pct) > GAP_WARN_PCT:
            direction = "over" if gap_pct > 0 else "under"
            warnings.append({"code": "audit_gap", "message": f"The audit as typed is {abs(gap_pct):.0f}% {'above' if direction == 'over' else 'below'} the bill ({audit_total:,.0f} vs {billed:,.0f} kWh). Reconciliation scales it to the bill."})
        if floor_hit:
            warnings.append({"code": "reconcile_floor", "message": f"Uncertain appliances were scaled down to the {UNCERTAIN_FLOOR:.0%} floor and the remaining gap was spread over every appliance. Re-check the aircon and refrigerator hours."})
        if ceiling_hit:
            warnings.append({"code": "reconcile_ceiling", "message": "Uncertain appliances reached nameplate; the remaining gap was spread over every appliance. Something may be missing from the audit."})
        audit_vs_bill = {
            "billed_kwh": float(billed),
            "audit_kwh": float(audit_total),
            "gap_pct": float(gap_pct),
            "uncertain_kwh": float(est_u),
            "fixed_kwh": float(est_f),
            "scale_uncertain": float(s_u),
            "scale_all": float(s_all),
            "reconciled": bool(reconcile and audit_total > 0),
            "bills": [{"billing_month": b.billing_month, "kwh": b.kwh, "days": b.period_days,
                       "audit_kwh": float(sum(_daily_kwh(p.energy_wh)[b.month - 1] * b.period_days for p in existing)),
                       "reconciled_kwh": float(sum(_daily_kwh(p.energy_wh)[b.month - 1] * b.period_days * scale[p.appliance.id] for p in existing))}
                      for b in valid_bills],
        }

    # --- sizing set profiles
    load_wh = np.zeros((12, 7, 24))
    load_wh_raw = np.zeros((12, 7, 24))
    hour_table_w = np.zeros((12, 7, 24))   # the field sheet's table: duty-weighted draw of every appliance touching the hour
    for p in sizing_set:
        load_wh += p.energy_wh * scale[p.appliance.id]
        load_wh_raw += p.energy_wh
        hour_table_w += p.active_hour * p.duty_watts
    load_kw = load_wh.mean(axis=1) / 1000.0
    load_kw_raw = load_wh_raw.mean(axis=1) / 1000.0
    daily = load_kw.sum(axis=1)
    annual = float(sum(d * n for d, n in zip(daily, DAYS_IN_MONTH)))
    peak_kw = float(hour_table_w.max()) / 1000.0 if sizing_set else 0.0
    peak_avg_kw = float(load_kw.max()) if sizing_set else 0.0
    peak_detail: dict = {}
    hour_table: list[dict] = []
    if sizing_set and peak_kw > 0:
        m_i, d_i, h_i = (int(x) for x in np.unravel_index(int(np.argmax(hour_table_w)), hour_table_w.shape))
        for h in range(24):
            apps = [{"name": p.appliance.name, "watts": float(p.duty_watts)} for p in sizing_set if p.active_hour[m_i, d_i, h]]
            apps.sort(key=lambda c: -c["watts"])
            hour_table.append({"hour": h, "label": f"{h:02d}:00-{(h + 1) % 24:02d}:00", "total_w": float(hour_table_w[m_i, d_i, h]), "appliances": apps})
        peak_detail = {
            "month": m_i + 1, "weekday": WEEKDAYS[d_i], "hour": h_i, "label": hour_table[h_i]["label"],
            "kw": peak_kw, "contributors": hour_table[h_i]["appliances"],
        }
    motors = [(p.appliance.input_power_w * p.appliance.cat.start_multiplier / 1000.0, p.appliance.input_power_w / 1000.0, p.appliance.cat.start_multiplier) for p in sizing_set if p.appliance.cat.start_multiplier > 1.0]
    if motors:
        _, largest_kw, mult = max(motors)
    else:
        largest_kw, mult = 0.0, 1.0

    # --- per appliance table (bill month if there is a bill, else annual average)
    ref_month = valid_bills[0].month - 1 if valid_bills else None
    total_rec = 0.0
    rows = []
    for p in profiles:
        d = _daily_kwh(p.energy_wh)
        kwh_day = float(d[ref_month]) if ref_month is not None and d[ref_month] > 0 else float(d[d > 0].mean()) if (d > 0).any() else 0.0
        rec = kwh_day * scale[p.appliance.id]
        if p.appliance.status in ("existing", "future"):
            total_rec += rec
        rows.append({
            "id": p.appliance.id, "name": p.appliance.name, "category": p.appliance.category, "category_label": p.appliance.cat.label,
            "status": p.appliance.status, "quantity": p.appliance.quantity, "input_power_w": p.appliance.input_power_w,
            "duty_factor": p.appliance.duty, "duty_is_default": p.appliance.duty_factor is None, "uncertain": p.appliance.uncertain,
            "hours_per_day": float(p.hours_per_day), "days_per_week": p.days_per_week, "hours_per_use_day": float(p.hours_per_use_day),
            "kwh_per_day_audit": float(kwh_day), "kwh_per_day_reconciled": float(rec),
            "scale": float(scale[p.appliance.id]), "scale_inherited": bool(p.appliance.status == "future" and scale[p.appliance.id] != 1.0),
            "warnings": p.warnings,
        })
    for r in rows:
        r["share_pct"] = float(r["kwh_per_day_reconciled"] / total_rec * 100.0) if (total_rec > 0 and r["status"] in ("existing", "future")) else 0.0

    future_daily = float(sum(_daily_kwh(p.energy_wh).max() * scale[p.appliance.id] for p in profiles if p.appliance.status == "future"))
    weekday_profiles = {m + 1: (load_wh[m] / 1000.0).round(4).tolist() for m in range(12)}

    return AuditResult(
        appliances=rows, load_kw=load_kw, load_kw_unreconciled=load_kw_raw, peak_kw=peak_kw, peak_avg_kw=peak_avg_kw,
        peak_detail=peak_detail, hour_table=hour_table,
        largest_motor_kw=largest_kw, largest_motor_multiplier=mult,
        daily_kwh_by_month=[float(x) for x in daily], annual_kwh=annual, audit_vs_bill=audit_vs_bill,
        warnings=warnings, future_daily_kwh=future_daily, weekday_profiles_kw=weekday_profiles,
    )
