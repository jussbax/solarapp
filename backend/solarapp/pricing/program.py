"""Program of works: schedule, installation days by the hour, and cashflow.

Built from the priced job: the labour calculation gives the man-hours per task,
crew and paid days; the freight run gives the pickup day; the build-up gives
every cost line. Dates hang off the signing date. Durations for permits and the
distribution utility are editable assumptions until the owner has data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from ..schemas import AssessmentDoc
from .config import PaymentPlan, PricingConfig

CUSTOMER_EVENTS = {"signing", "permit_application", "permit_approved", "netmeter_application", "materials_on_site", "installation",
                   "commissioning", "cfei", "meter_installed"}


def _hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _clock(minutes: int) -> str:
    minutes = int(round(minutes))
    return f"{(minutes // 60) % 24:02d}:{minutes % 60:02d}"


def _iso(d: date) -> str:
    return d.isoformat()


@dataclass
class Window:
    """Productive minutes on one day between lunch and day end."""
    day: int
    start: int
    end: int


class Timeline:
    """Walks productive windows across installation days; returns clock segments for a number of work minutes."""

    def __init__(self, windows: list[Window]):
        self.windows = windows
        self.i = 0
        self.pos = windows[0].start if windows else 0

    def now(self) -> tuple[int, int]:
        if self.i >= len(self.windows):
            w = self.windows[-1]
            return w.day, w.end
        return self.windows[self.i].day, self.pos

    def advance_to(self, day: int, minute: int) -> None:
        while self.i < len(self.windows):
            w = self.windows[self.i]
            if w.day < day or (w.day == day and w.end <= minute):
                self.i += 1
                if self.i < len(self.windows):
                    self.pos = self.windows[self.i].start
                continue
            if w.day == day and minute > w.start:
                self.pos = max(self.pos, minute)
            break

    def take(self, minutes: float) -> list[tuple[int, int, int]]:
        """Consume work minutes; returns (day, start, end) segments."""
        segs = []
        left = float(minutes)
        while left > 1e-6:
            if self.i >= len(self.windows):
                # ran out of planned days: extend with a copy of the last window on a new day
                last = self.windows[-1]
                self.windows.append(Window(last.day + 1, last.start, last.end))
                self.pos = last.start
            w = self.windows[self.i]
            avail = w.end - self.pos
            if avail <= 0:
                self.i += 1
                if self.i < len(self.windows):
                    self.pos = self.windows[self.i].start
                continue
            use = min(avail, left)
            segs.append((w.day, int(round(self.pos)), int(round(self.pos + use))))
            self.pos += use
            left -= use
        return segs


def day_windows(cfg: PricingConfig, doc: AssessmentDoc, days: int, extra_km: float) -> tuple[list[Window], dict]:
    """Site day: depart, travel, unload and set up, work with a lunch break, pack up, travel back."""
    pr = cfg.program
    pj = doc.program
    depart = _hhmm(pj.depart_time or pr.depart_time)
    lunch_start = _hhmm(pj.lunch_start or pr.lunch_start)
    lunch = pj.lunch_minutes if pj.lunch_minutes is not None else pr.lunch_minutes
    travel = int(round(60 * (cfg.mobdemob.one_way_travel_hours + (extra_km / pr.travel_speed_kmh if pr.travel_speed_kmh > 0 else 0))))
    setup = int(round(60 * cfg.labor.nonproductive_hours / 2))
    productive = int(round(60 * cfg.productive_hours))
    arrive = depart + travel
    work_start = arrive + setup
    windows: list[Window] = []
    for d in range(max(days, 1)):
        left = productive
        t = work_start
        if t < lunch_start:
            first = min(left, lunch_start - t)
            windows.append(Window(d, t, t + first))
            left -= first
            t = lunch_start + lunch
        else:
            t = max(t, lunch_start + lunch) if t < lunch_start + lunch else t
        if left > 0:
            windows.append(Window(d, t, t + left))
    last_end = max(w.end for w in windows if w.day == 0)
    frame = {
        "depart": _clock(depart), "arrive": _clock(arrive), "work_start": _clock(work_start), "lunch_start": _clock(lunch_start),
        "lunch_end": _clock(lunch_start + lunch), "work_end": _clock(last_end), "pack_up_end": _clock(last_end + setup),
        "back_at_base": _clock(last_end + setup + travel), "travel_minutes": travel, "productive_hours": cfg.productive_hours,
    }
    return windows, frame


def _hourly_grid(day_segments: list[dict], frame: dict, days: int) -> list[dict]:
    """One row per clock hour per day with the activities of each stream (the three longest in that hour, in order)."""
    start_h = _hhmm(frame["depart"]) // 60
    out = []
    for d in range(days):
        todays = [s for s in day_segments if s["day"] == d]
        end_h = int(math.ceil(max(s["end"] for s in todays) / 60)) if todays else start_h + 1
        rows = []
        for h in range(start_h, end_h):
            a, b = h * 60, (h + 1) * 60
            cell = {"time": f"{h:02d}:00"}
            for stream in ("roof", "ground"):
                parts: list[tuple[int, int, str]] = []
                for s in todays:
                    if s["stream"] not in (stream, "all"):
                        continue
                    overlap = min(s["end"], b) - max(s["start"], a)
                    if overlap > 0 and s["task"] not in [x[2] for x in parts]:
                        parts.append((max(s["start"], a), overlap, s["task"]))
                keep = sorted(sorted(parts, key=lambda x: -x[1])[:3], key=lambda x: x[0])
                more = len(parts) - len(keep)
                cell[stream] = " → ".join(x[2] for x in keep) + (f" (+{more} more)" if more > 0 else "")
            rows.append(cell)
        out.append({"day": d + 1, "rows": rows})
    return out


def plan_install_days(pricing: dict, cfg: PricingConfig, doc: AssessmentDoc) -> dict:
    """Roof pairs and the ground crew work in parallel; the roof crew joins the ground tasks when the roof is done."""
    lb = pricing["labor"]
    det = lb.get("detail") or {}
    pairs = int(lb["pairs"])
    persons = int(lb["persons"])
    if pairs <= 0 or persons <= 0:
        return {"days": 0, "segments": [], "hourly": [], "frame": {}, "warnings": [{"code": "no_crew", "message": "No installation crew in the labour calculation."}]}
    roof_persons = 2 * pairs
    ground_persons = max(persons - roof_persons, 1)
    days = max(int(math.ceil(float(lb["days"]) - 1e-9)), 1)
    extra_km = float((pricing.get("job_inputs") or {}).get("extra_km") or 0)
    windows, frame = day_windows(cfg, doc, days, extra_km)
    warnings: list[dict] = []

    # streams: (task label, man-hours)
    roof_tasks = [
        ("Set up rails and L-feet", float(det.get("roof_mount_mh", 0)) * (cfg.roof.setup_mh / (cfg.roof.setup_mh + pricing["takeoff"]["panels"] * cfg.roof.mounting_mh_per_panel)) if pricing["takeoff"]["panels"] else 0.0),
    ]
    mount_total = float(det.get("roof_mount_mh", 0))
    roof_tasks[0] = ("Set up rails and L-feet", roof_tasks[0][1])
    roof_tasks.append(("Mount panels and clamps", mount_total - roof_tasks[0][1]))
    roof_tasks.append(("Roof wiring: strings and home runs", float(det.get("roof_wire_mh", 0))))
    g = det.get("ground", {})
    labels = [
        ("battery_hauling", "Haul the battery to its place"),
        ("hybrid_inverters", "Mount the hybrid inverter"), ("gridtie_inverters", "Mount the grid-tie inverter"),
        ("battery_packs", "Anchor and connect the battery"), ("enclosures", "Mount enclosures, DIN rail and ground bar"),
        ("protective", "Install breakers, SPDs and the ATS"), ("conduit", "Run conduit and cable tray"),
        ("wire", "Pull and terminate wires"), ("mc4", "String home-run MC4 connections"), ("ground_rods", "Drive and bond the ground rod"),
    ]
    ground_tasks = [("Unload and hand off materials", float(lb.get("handoff_mh", 0)))]
    ground_tasks += [(lab, float(g.get(k, 0))) for k, lab in labels if float(g.get(k, 0)) > 0]
    energize = ("Energize, test and commission", float(g.get("energize", 0)))

    segments: list[dict] = []
    roof_tl = Timeline([Window(w.day, w.start, w.end) for w in windows])
    for task, mh in roof_tasks:
        if mh <= 0:
            continue
        for d, a, b in roof_tl.take(mh * 60 / roof_persons):
            segments.append({"day": d, "stream": "roof", "task": task, "start": a, "end": b, "crew": roof_persons})
    roof_done = roof_tl.now()

    ground_tl = Timeline([Window(w.day, w.start, w.end) for w in windows])
    def after(x: tuple[int, int], y: tuple[int, int]) -> bool:
        return x[0] > y[0] or (x[0] == y[0] and x[1] >= y[1])
    for task, mh in ground_tasks + [energize]:
        if mh <= 0:
            continue
        if task == energize[0]:
            # needs the roof strings done and the rest of the ground work finished
            if after(roof_done, ground_tl.now()):
                ground_tl.advance_to(*roof_done)
        left = mh * 60.0
        while left > 1e-6:
            now = ground_tl.now()
            crew = persons if after(now, roof_done) else ground_persons
            if crew == ground_persons:
                # minutes of work possible before the roof crew joins
                probe = Timeline([Window(w.day, w.start, w.end) for w in ground_tl.windows])
                probe.i, probe.pos = ground_tl.i, ground_tl.pos
                mins_until_join = 0.0
                while True:
                    d, p = probe.now()
                    if after((d, p), roof_done) or probe.i >= len(probe.windows):
                        break
                    w = probe.windows[probe.i]
                    cap = (min(w.end, roof_done[1]) if w.day == roof_done[0] else w.end) - probe.pos
                    if cap <= 0:
                        probe.i += 1
                        if probe.i < len(probe.windows):
                            probe.pos = probe.windows[probe.i].start
                        continue
                    mins_until_join += cap
                    probe.pos += cap
                    if probe.pos >= w.end:
                        probe.i += 1
                        if probe.i < len(probe.windows):
                            probe.pos = probe.windows[probe.i].start
                chunk_work = min(left, mins_until_join * crew) if mins_until_join > 0 else left
                if mins_until_join <= 0:
                    crew = persons
                    chunk_work = left
            else:
                chunk_work = left
            for d, a, b in ground_tl.take(chunk_work / crew):
                segments.append({"day": d, "stream": "ground", "task": task, "start": a, "end": b, "crew": crew})
            left -= chunk_work
    finish = max(roof_done, ground_tl.now())
    planned_days = max(max(s["day"] for s in segments) + 1, 1) if segments else days
    if planned_days > days:
        warnings.append({"code": "schedule_overrun", "message": f"The hour-by-hour plan needs {planned_days} day(s) against {days} paid day(s) in the labour calculation; the roof and ground streams are unbalanced."})
    elif finish[0] == planned_days - 1 and finish[1] < _hhmm(frame["work_end"]) - 60:
        warnings.append({"code": "early_finish", "message": f"The crew finishes about {_clock(finish[1])} on the last day; the labour calculation still pays {days} full day(s)."})
    # fixed parts of each day
    for d in range(planned_days):
        segments.append({"day": d, "stream": "all", "task": "Travel from base", "start": _hhmm(frame["depart"]), "end": _hhmm(frame["arrive"]), "crew": persons})
        segments.append({"day": d, "stream": "all", "task": "Set up site, unload", "start": _hhmm(frame["arrive"]), "end": _hhmm(frame["work_start"]), "crew": persons})
        last = d == planned_days - 1
        end_work = finish[1] if last and finish[0] == d else _hhmm(frame["work_end"])
        if end_work > _hhmm(frame["lunch_start"]):
            segments.append({"day": d, "stream": "all", "task": "Lunch", "start": _hhmm(frame["lunch_start"]), "end": _hhmm(frame["lunch_end"]), "crew": persons})
        segments.append({"day": d, "stream": "all", "task": "Pack up, clean site", "start": end_work, "end": end_work + (_hhmm(frame["pack_up_end"]) - _hhmm(frame["work_end"])), "crew": persons})
        segments.append({"day": d, "stream": "all", "task": "Travel back to base", "start": end_work + (_hhmm(frame["pack_up_end"]) - _hhmm(frame["work_end"])), "end": end_work + (_hhmm(frame["back_at_base"]) - _hhmm(frame["work_end"])), "crew": persons})
    segments.sort(key=lambda s: (s["day"], s["start"], s["stream"]))
    for s in segments:
        s["start_time"], s["end_time"] = _clock(s["start"]), _clock(s["end"])
    hourly = _hourly_grid(segments, frame, planned_days)
    return {
        "days": planned_days, "paid_days": days, "crew": {"persons": persons, "roof_pairs": pairs, "roof_persons": roof_persons, "ground_persons": ground_persons, "description": lb.get("crew", "")},
        "finish_time": _clock(finish[1]), "segments": segments, "hourly": hourly, "frame": frame, "warnings": warnings,
        "man_hours": {"roof": lb["roof_mh"], "ground": lb["ground_mh"], "handoff": lb.get("handoff_mh", 0), "total": lb["total_mh"]},
    }


def _plan(cfg: PricingConfig, doc: AssessmentDoc) -> PaymentPlan:
    pay = doc.program.payment
    if pay is not None:
        data = pay if isinstance(pay, dict) else pay.model_dump()
        if data.get("milestones") or data.get("installments"):
            return PaymentPlan.model_validate(data)
    return cfg.program.payment


def build_program(doc: AssessmentDoc, results: dict, cfg: PricingConfig, today: Optional[date] = None) -> dict:
    pricing = results.get("pricing") or {}
    if not pricing.get("available"):
        return {"available": False, "reason": "Price the job first; the program of works is built from the priced bill of materials and labour.", "warnings": []}
    pr, pj = cfg.program, doc.program
    sizing = results.get("sizing") or {}
    net_metering = sizing.get("kind") != "off_grid"
    warnings: list[dict] = []
    assumptions: list[str] = []
    today = today or date.today()
    signing = date.fromisoformat(pj.signing_date) if pj.signing_date else today
    if not pj.signing_date:
        assumptions.append("Signing date not set; today is used.")

    install_plan = plan_install_days(pricing, cfg, doc)
    warnings += install_plan["warnings"]
    n_days = max(install_plan["days"], 1)

    permit_days = pj.permit_approval_days if pj.permit_approval_days is not None else pr.permit_approval_days
    nm_app_days = pj.netmeter_application_days if pj.netmeter_application_days is not None else pr.netmeter_application_days
    nm_meter_days = pj.netmeter_meter_days if pj.netmeter_meter_days is not None else pr.netmeter_meter_days
    assumptions.append(f"LGU electrical permit approval {permit_days} days, CFEI {pr.cfei_days} days after installation (no data yet).")
    if net_metering:
        assumptions.append(f"Net metering: DU application and agreement {nm_app_days} days, inspection and bi-directional meter {nm_meter_days} days after commissioning (no data yet).")

    permit_prep_end = signing + timedelta(days=pr.permit_prep_days)
    permit_approved = permit_prep_end + timedelta(days=permit_days)
    install_start = date.fromisoformat(pj.install_date) if pj.install_date else permit_approved + timedelta(days=pr.install_gap_after_permit_days)
    if install_start < permit_approved:
        warnings.append({"code": "install_before_permit", "message": f"Installation on {install_start.isoformat()} is before the expected permit approval on {permit_approved.isoformat()}."})
    sourcing = install_start - timedelta(days=pr.sourcing_days_before_install)
    install_end = install_start + timedelta(days=n_days - 1)
    commissioning = install_end + timedelta(days=pr.commissioning_offset_days)
    cfei = commissioning + timedelta(days=pr.cfei_days)
    nm_application = signing + timedelta(days=1) if net_metering else None
    nm_agreement = nm_application + timedelta(days=nm_app_days) if nm_application else None
    meter = (max(commissioning, nm_agreement) + timedelta(days=nm_meter_days)) if net_metering and nm_agreement else None
    completion = meter or cfei

    event_dates = {
        "signing": signing, "permit_application": permit_prep_end, "permit_approved": permit_approved, "sourcing": sourcing,
        "materials_on_site": install_start, "installation": install_start, "installation_done": install_end, "commissioning": commissioning, "cfei": cfei,
        "netmeter_application": nm_application, "netmeter_agreement": nm_agreement, "meter_installed": meter, "completion": completion,
    }
    events = [
        {"key": "signing", "label": "Contract signing and downpayment", "date": _iso(signing), "end": None, "kind": "milestone"},
        {"key": "permit_prep", "label": "Electrical plans, signed and sealed by the PEE", "date": _iso(signing), "end": _iso(permit_prep_end), "kind": "task"},
        {"key": "permit_application", "label": "Electrical permit application (city or municipal office)", "date": _iso(permit_prep_end), "end": _iso(permit_approved), "kind": "task"},
        {"key": "permit_approved", "label": "Electrical permit approved", "date": _iso(permit_approved), "end": None, "kind": "milestone"},
    ]
    if net_metering:
        events += [
            {"key": "netmeter_application", "label": "Net metering application with your electric company", "date": _iso(nm_application), "end": _iso(nm_agreement), "kind": "task"},
            {"key": "netmeter_agreement", "label": "Net metering agreement signed", "date": _iso(nm_agreement), "end": None, "kind": "milestone"},
        ]
    events += [
        {"key": "sourcing", "label": "Pickup run: " + ", ".join(pricing["freight"]["stops_on_run"]), "date": _iso(sourcing), "end": None, "kind": "task"},
        {"key": "materials_on_site", "label": "Materials delivered to your house", "date": _iso(install_start), "end": None, "kind": "milestone"},
        {"key": "installation", "label": f"Installation ({n_days} {'day' if n_days == 1 else 'days'}, crew of {install_plan['crew']['persons']})", "date": _iso(install_start), "end": _iso(install_end), "kind": "task"},
        {"key": "commissioning", "label": "System switched on and tested", "date": _iso(commissioning), "end": None, "kind": "milestone"},
        {"key": "cfei", "label": "Final electrical inspection certificate", "date": _iso(cfei), "end": None, "kind": "milestone"},
    ]
    if net_metering:
        events += [
            {"key": "meter_installed", "label": "Electric company inspection; net metering meter installed", "date": _iso(meter), "end": None, "kind": "milestone"},
        ]
    for e in events:
        e["customer"] = e["key"] in CUSTOMER_EVENTS
    events.sort(key=lambda e: e["date"])  # stable: the build order above is the order of a day

    # ---- payments in
    plan = _plan(cfg, doc)
    contract = float(pricing["totals"]["contract_rounded"])
    shares = sum(m.share for m in plan.milestones) + (plan.installment_share if plan.installments > 0 else 0.0)
    scale = 1.0 / shares if shares > 0 else 0.0
    if abs(shares - 1.0) > 1e-6:
        warnings.append({"code": "payment_shares", "message": f"Payment shares add up to {shares * 100:.0f}%; they are scaled to the contract price."})
    payments: list[dict] = []
    for m in plan.milestones:
        if m.share <= 0:
            continue
        base = event_dates.get(m.event) or signing
        d = base + timedelta(days=m.offset_days)
        payments.append({"key": m.key, "label": m.label, "date": _iso(d), "amount": contract * m.share * scale, "share": m.share * scale})
    if plan.installments > 0 and plan.installment_share > 0:
        base = (event_dates.get(plan.installment_start_event) or commissioning) + timedelta(days=plan.installment_first_offset_days)
        each = contract * plan.installment_share * scale / plan.installments
        for i in range(plan.installments):
            d = base + timedelta(days=i * plan.installment_interval_days)
            payments.append({"key": f"installment_{i + 1}", "label": f"Installment {i + 1} of {plan.installments}", "date": _iso(d), "amount": each, "share": plan.installment_share * scale / plan.installments})
    events += [{"key": p["key"], "label": p["label"], "date": p["date"], "end": None, "kind": "payment_in", "customer": True, "amount": p["amount"]} for p in payments]
    events.sort(key=lambda e: (e["date"], 1 if e["kind"] == "payment_in" else 0))  # payments after the day's work

    # ---- cash out
    lines = pricing["lines"]
    # cash at the counter = net price plus payment fee; the landed cost adds internal allocations
    supplier_cash: dict[str, float] = dict(pricing.get("cash_by_supplier") or {})
    if not supplier_cash:
        for l in lines:
            if l.get("found"):
                supplier_cash[l["supplier"]] = supplier_cash.get(l["supplier"], 0.0) + float(l.get("landed", 0))
    fr = pricing["freight"]
    t = cfg.truck
    freight_cash = fr["trips"] * (t.driver_per_trip_day + t.helper_per_trip_day) * t.trip_days_per_run + fr["trips"] * (fr["loop_km"] * (t.diesel_price / t.fuel_economy_km_per_l) + fr["toll"]) if fr["trips"] else 0.0
    freight_noncash = float(fr["freight"]) - freight_cash
    lb = pricing["labor"]
    j = cfg.job
    bu = {x["key"]: x for x in pricing["build_up"]}
    ppe = float(bu.get("ppe", {}).get("direct", 0))
    outflows = [
        {"key": "seal", "label": "PEE sign and seal", "date": _iso(signing), "amount": float(bu.get("seal", {}).get("direct", 0))},
        {"key": "permit", "label": "LGU electrical permit and CFEI fees", "date": _iso(permit_prep_end), "amount": float(bu.get("permit", {}).get("direct", 0))},
    ]
    if net_metering:
        outflows.append({"key": "netmeter_fees", "label": "ERC certificate and bi-directional meter fees", "date": _iso(nm_application), "amount": float(bu.get("erc", {}).get("direct", 0)) + float(bu.get("meter", {}).get("direct", 0))})
    for sup, amt in sorted(supplier_cash.items()):
        outflows.append({"key": f"supplier_{sup}", "label": f"Materials, cash at {sup}", "date": _iso(sourcing), "amount": amt})
    outflows.append({"key": "freight", "label": "Pickup run: driver, helper, diesel and toll", "date": _iso(sourcing), "amount": freight_cash})
    labour_date = install_end + timedelta(days=pr.labour_paid_days_after_job)
    outflows.append({"key": "labour", "label": "Crew wages", "date": _iso(labour_date), "amount": float(lb["labor"])})
    outflows.append({"key": "mobdemob", "label": "Crew transport, packaging disposal, PPE", "date": _iso(labour_date), "amount": float(lb["mobdemob"]) + ppe})
    commission = float(pricing["totals"]["commission"])
    if commission > 0:
        outflows.append({"key": "commission", "label": "Agent commission", "date": _iso(commissioning + timedelta(days=pr.commission_paid_days_after_job)), "amount": commission})
    vat = float(pricing["totals"]["vat"])
    outflows.append({"key": "vat", "label": "VAT remittance", "date": _iso(completion + timedelta(days=pr.vat_remit_days_after_completion)), "amount": vat})
    outflows = [o for o in outflows if o["amount"] > 0]
    noncash = {
        "handling_wastage_storage": sum(float(l.get("landed", 0)) for l in lines if l.get("found")) - sum(supplier_cash.values()),
        "truck_ownership_maintenance": freight_noncash,
        "tools": float(lb["tools"]),
    }

    # ---- running balance
    flows = [{"date": p["date"], "label": p["label"], "inflow": p["amount"], "outflow": 0.0, "kind": "in", "key": p["key"]} for p in payments]
    flows += [{"date": o["date"], "label": o["label"], "inflow": 0.0, "outflow": o["amount"], "kind": "out", "key": o["key"]} for o in outflows]
    flows.sort(key=lambda f: (f["date"], 0 if f["kind"] == "in" else 1))
    bal = 0.0
    lowest = (0.0, _iso(signing))
    for f in flows:
        bal += f["inflow"] - f["outflow"]
        f["balance"] = bal
        if bal < lowest[0]:
            lowest = (bal, f["date"])
    total_in = sum(f["inflow"] for f in flows)
    total_out = sum(f["outflow"] for f in flows)
    # weekly buckets for the chart
    first = date.fromisoformat(flows[0]["date"]) if flows else signing
    weeks: dict[str, dict] = {}
    for f in flows:
        d = date.fromisoformat(f["date"])
        wk = first + timedelta(days=((d - first).days // 7) * 7)
        k = _iso(wk)
        w = weeks.setdefault(k, {"week": k, "inflow": 0.0, "outflow": 0.0, "balance": 0.0})
        w["inflow"] += f["inflow"]
        w["outflow"] += f["outflow"]
        w["balance"] = f["balance"]
    customer_schedule = [{"label": e["label"], "date": e["date"], "end": e["end"]} for e in events if e.get("customer") and e["kind"] != "payment_in"]
    return {
        "available": True,
        "signing_date": _iso(signing), "install_start": _iso(install_start), "install_end": _iso(install_end), "completion": _iso(completion),
        "net_metering": net_metering,
        "events": events,
        "install": install_plan,
        "payments": payments,
        "payment_plan": plan.model_dump(),
        "outflows": outflows,
        "cashflow": {"flows": flows, "weekly": list(weeks.values()), "total_in": total_in, "total_out": total_out, "cash_margin": total_in - total_out,
                     "lowest_balance": lowest[0], "lowest_balance_date": lowest[1], "noncash": noncash, "contract": contract},
        "customer_schedule": customer_schedule,
        "assumptions": assumptions,
        "warnings": warnings,
    }
