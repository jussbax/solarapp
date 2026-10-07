"""Pricing engine: a faithful port of the workbook's MATERIALS DB landed cost, the JOB
sheet's freight run and price build-up, and LABOR CALC's crew and days."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .catalog import Catalog, Item
from .config import EQUIPMENT_CATEGORIES, PricingConfig


# ---------------------------------------------------------------- landed cost
@dataclass
class LandedCost:
    net_price: float
    truck_share: float
    handling: float
    wastage: float
    payment_fee: float
    storage: float
    landed: float
    markup_tier: float

    @property
    def selling(self) -> float:
        return self.landed * (1 + self.markup_tier)


def truck_share(item: Item, cfg: PricingConfig) -> float:
    return max(item.weight_kg / cfg.truck.payload_kg, item.volume_m3 / cfg.truck.cargo_volume_m3)


def landed_cost(item: Item, catalog: Catalog, cfg: PricingConfig) -> LandedCost:
    sup = catalog.supplier(item.supplier)
    cat = cfg.category(item.category)
    net = item.list_price * (1 - sup.dealer_discount)
    share = truck_share(item, cfg)
    handling = cfg.handling.typical_job_cost * share / cfg.handling.typical_fill if cfg.handling.typical_fill > 0 else 0.0
    wastage = net * cat.wastage
    fee = net * sup.payment_fee
    landed = net + handling + wastage + fee + item.storage
    return LandedCost(net, share, handling, wastage, fee, item.storage, landed, cat.markup_tier)


# ---------------------------------------------------------------- BOM lines
@dataclass
class BomLine:
    code: str
    qty: float
    role: str = ""
    note: str = ""


@dataclass
class PricedLine:
    code: str
    role: str
    note: str
    name: str
    category: str
    supplier: str
    unit: str
    qty: float
    landed_unit: float
    markup_tier: float
    landed: float
    markup: float
    selling: float
    truck_share: float
    weight_kg: float
    rating: Optional[float]
    rating_unit: str
    is_hybrid_inverter: bool
    found: bool = True

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def price_lines(bom: list[BomLine], catalog: Catalog, cfg: PricingConfig) -> list[PricedLine]:
    out: list[PricedLine] = []
    for line in bom:
        item = catalog.get(line.code)
        if item is None:
            out.append(PricedLine(line.code, line.role, line.note, "Code not found", "", "", "", line.qty, 0, 0, 0, 0, 0, 0, 0, None, "", False, found=False))
            continue
        lc = landed_cost(item, catalog, cfg)
        delivers = catalog.supplier(item.supplier).delivers_free
        landed = line.qty * lc.landed
        markup = landed * lc.markup_tier
        out.append(PricedLine(
            code=item.code, role=line.role, note=line.note, name=item.name, category=item.category, supplier=item.supplier,
            unit=item.unit, qty=line.qty, landed_unit=lc.landed, markup_tier=lc.markup_tier, landed=landed, markup=markup,
            selling=landed + markup, truck_share=0.0 if delivers else line.qty * lc.truck_share, weight_kg=item.weight_kg,
            rating=item.rating, rating_unit=item.rating_unit, is_hybrid_inverter=item.is_hybrid_inverter,
        ))
    return out


# ---------------------------------------------------------------- takeoff (JOB sheet rules)
@dataclass
class Takeoff:
    panels: int = 0
    hybrid_inverters: int = 0
    gridtie_inverters: int = 0
    battery_packs: int = 0
    heaviest_pack_kg: float = 0.0
    enclosures: int = 0
    protective_devices: int = 0
    conduit_m: float = 0.0
    wire_m: float = 0.0
    mc4_pairs: int = 0
    ground_rods: int = 0

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def takeoff_from_lines(lines: list[PricedLine]) -> Takeoff:
    t = Takeoff()
    for l in lines:
        if not l.found:
            continue
        n = l.name.lower()
        q = l.qty
        if l.category == "Solar Panel":
            t.panels += int(round(q))
        if l.is_hybrid_inverter:
            t.hybrid_inverters += int(round(q))
        elif l.category == "Inverter":
            t.gridtie_inverters += int(round(q))
        if l.category == "Battery":
            t.battery_packs += int(round(q))
            t.heaviest_pack_kg = max(t.heaviest_pack_kg, l.weight_kg)
        if l.category == "Enclosures and Raceways":
            if "box" in n or "enclosure" in n:
                t.enclosures += int(round(q))
            if l.unit == "m":
                t.conduit_m += q
            elif "tray" in n and l.unit == "pc":
                t.conduit_m += 2 * q
        if l.category == "Protective Devices":
            t.protective_devices += int(round(q))
        if l.category == "Wires and Terminations" and l.unit == "m":
            t.wire_m += q
        if "mc4" in n:
            t.mc4_pairs += int(round(q))
        if l.category == "Grounding" and "rod" in n:
            t.ground_rods += int(round(q))
    return t


# ---------------------------------------------------------------- freight
@dataclass
class FreightResult:
    stops_on_run: list[str]
    legs: list[dict]
    loop_km: float
    toll: float
    run_cost: float
    truck_share: float
    trips: int
    freight: float

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def freight_for(lines: list[PricedLine], catalog: Catalog, cfg: PricingConfig, extra_km: float = 0.0, extra_toll: float = 0.0) -> FreightResult:
    r = cfg.route
    bought: dict[str, float] = {}
    for l in lines:
        if l.found and l.qty > 0:
            bought[l.supplier] = bought.get(l.supplier, 0.0) + l.qty
    stops = r.stops
    base, site = 0, len(stops) - 1
    on_run = []
    for i in range(1, site):
        name = stops[i]
        if bought.get(name, 0) > 0 and not catalog.supplier(name).delivers_free:
            on_run.append(i)
    seq = [base] + on_run + [site, base]
    legs, km, toll = [], 0.0, 0.0
    for a, b in zip(seq, seq[1:]):
        legs.append({"from": stops[a], "to": stops[b], "km": r.km[a][b], "toll": r.toll[a][b]})
        km += r.km[a][b]
        toll += r.toll[a][b]
    loop_km = km + 2 * extra_km
    toll_total = toll + extra_toll
    t = cfg.truck
    run_cost = (t.ownership_per_trip_day + t.driver_per_trip_day + t.helper_per_trip_day) * t.trip_days_per_run + loop_km * t.running_cost_per_km + toll_total
    share = sum(l.truck_share for l in lines)
    trips = int(math.ceil(share - 1e-12)) if share > 0 else 0
    return FreightResult([stops[i] for i in on_run], legs, loop_km, toll_total, run_cost, share, trips, trips * run_cost)


# ---------------------------------------------------------------- labour (LABOR CALC)
@dataclass
class JobInputs:
    roof_factor: float = 0.75
    roof_closed_days: int = 1
    max_days: int = 2
    max_pairs: int = 2
    battery_haul_hours: float = 0.5
    owner_days: float = 0.0
    extra_km: float = 0.0
    extra_toll: float = 0.0
    net_metering: bool = True


@dataclass
class LaborResult:
    roof_mh: float
    ground_mh: float
    handoff_mh: float
    total_mh: float
    ground_pace: float
    carry_crew: int
    options: list[dict]
    pairs: int
    days: float
    persons: int
    crew: str
    labor: float
    person_days: float
    mobdemob: float
    tools: float
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def labor_for(t: Takeoff, cfg: PricingConfig, job: JobInputs) -> LaborResult:
    rf, g, lr = cfg.roof, cfg.ground, cfg.labor
    roof_mount = (rf.setup_mh + t.panels * rf.mounting_mh_per_panel) * job.roof_factor if t.panels > 0 else 0.0
    roof_wire = t.panels * rf.wiring_mh_per_panel * job.roof_factor
    roof_mh = roof_mount + roof_wire
    pace = g.hybrid_pace if (t.hybrid_inverters + t.battery_packs) > 0 else 1.0
    carry = 0 if t.battery_packs == 0 else max(2, int(math.ceil(t.heaviest_pack_kg / cfg.hauling.max_kg_per_person - 1e-12)))
    inverters = t.hybrid_inverters + t.gridtie_inverters
    ground_parts = {
        "hybrid_inverters": t.hybrid_inverters * g.mh("hybrid_inverter") * pace,
        "gridtie_inverters": t.gridtie_inverters * g.mh("gridtie_inverter") * pace,
        "battery_packs": t.battery_packs * g.mh("battery_pack") * pace,
        "enclosures": t.enclosures * g.mh("enclosure") * pace,
        "protective": t.protective_devices * g.mh("protective") * pace,
        "conduit": t.conduit_m * g.mh("conduit_m") * pace,
        "wire": t.wire_m * g.mh("wire_m") * pace,
        "mc4": t.mc4_pairs * g.mh("mc4_pair") * pace,
        "ground_rods": t.ground_rods * g.mh("ground_rod") * pace,
        "energize": ((g.mh("energize_job") + inverters * g.mh("energize_inverter") + t.battery_packs * g.mh("energize_pack")) * pace) if inverters > 0 else 0.0,
        "battery_hauling": carry * job.battery_haul_hours * t.battery_packs,
    }
    ground_mh = sum(ground_parts.values())
    handoff = 2.0 if t.panels > 0 else 0.0  # hand-off: 1 h x 2 persons
    total = roof_mh + ground_mh + handoff
    prod = cfg.productive_hours
    min_pairs_roof = max(1, int(math.ceil(roof_mh / (2 * prod * job.roof_closed_days) - 1e-12))) if roof_mh > 0 else 0
    min_pairs_carry = max(0, int(math.ceil((carry - 2) / 2 - 1e-12))) if carry > 0 else 0
    min_pairs = max(min_pairs_roof, min_pairs_carry)
    unit = lr.pay_unit_days
    transport = cfg.mobdemob.crew_transport_per_day
    options = []
    for p in (1, 2, 3):
        persons = 2 + 2 * p
        days = math.ceil(total / (persons * prod) / unit - 1e-12) * unit if total > 0 else 0
        cost = days * (lr.team_lead_day + p * lr.skilled_day + (p + 1) * lr.laborer_day + transport)
        feasible = p >= min_pairs and p <= job.max_pairs and days <= job.max_days
        options.append({"pairs": p, "persons": persons, "days": days, "cost_with_transport": cost, "feasible": feasible})
    feasible = [o for o in options if o["feasible"]]
    if total <= 0:
        pairs, days = 0, 0.0
    elif feasible:
        best = min(feasible, key=lambda o: (o["cost_with_transport"], o["pairs"]))
        pairs, days = best["pairs"], best["days"]
    else:
        pairs = min(3, max(min_pairs, job.max_pairs))
        days = options[pairs - 1]["days"]
    persons = 2 + 2 * pairs if pairs else 0
    labor = days * (lr.team_lead_day + pairs * lr.skilled_day + (pairs + 1) * lr.laborer_day) + job.owner_days * lr.owner_day if pairs else job.owner_days * lr.owner_day
    person_days = persons * days + job.owner_days
    mob = days * transport + (cfg.mobdemob.packaging_disposal if t.panels > 0 else 0.0) + days * (2 * job.extra_km * cfg.mobdemob.running_cost_per_km + job.extra_toll)
    tools = days * cfg.tools.charge_per_installation_day
    crew = f"1 team lead, {pairs} skilled, {pairs + 1} laborers" if pairs else ""
    return LaborResult(
        roof_mh=roof_mh, ground_mh=ground_mh, handoff_mh=handoff, total_mh=total, ground_pace=pace, carry_crew=carry,
        options=options, pairs=pairs, days=days, persons=persons, crew=crew, labor=labor, person_days=person_days,
        mobdemob=mob, tools=tools,
        detail={"roof_mount_mh": roof_mount, "roof_wire_mh": roof_wire, "ground": ground_parts, "min_pairs": min_pairs,
                "productive_hours": prod, "crew_transport_per_day": transport},
    )


# ---------------------------------------------------------------- build-up and quotation
@dataclass
class BuildUpLine:
    key: str
    label: str
    direct: float
    tier: float
    pass_through: bool = False

    @property
    def markup(self) -> float:
        return self.direct * self.tier

    @property
    def selling(self) -> float:
        return self.direct + self.markup

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "direct": self.direct, "tier": self.tier, "markup": self.markup, "selling": self.selling, "pass_through": self.pass_through}


def price_job(bom: list[BomLine], catalog: Catalog, cfg: PricingConfig, job: JobInputs) -> dict:
    lines = price_lines(bom, catalog, cfg)
    t = takeoff_from_lines(lines)
    fr = freight_for(lines, catalog, cfg, job.extra_km, job.extra_toll)
    lb = labor_for(t, cfg, job)
    j = cfg.job
    mat_direct = sum(l.landed for l in lines)
    mat_markup = sum(l.markup for l in lines)
    bl = [
        BuildUpLine("materials", "Materials (BOM)", mat_direct, (mat_markup / mat_direct) if mat_direct else 0.0),
        BuildUpLine("freight", "Freight", fr.freight, j.freight_markup),
        BuildUpLine("labor", "Labor", lb.labor, j.services_markup),
        BuildUpLine("mobdemob", "Mob/demob", lb.mobdemob, j.services_markup),
        BuildUpLine("tools", "Tools", lb.tools, j.services_markup),
        BuildUpLine("ppe", "PPE", lb.person_days * j.ppe_per_person_day, j.services_markup),
        BuildUpLine("seal", "PEE sign and seal", j.pee_seal if t.panels > 0 else 0.0, j.services_markup),
        BuildUpLine("permit", "LGU electrical permit and CFEI", j.lgu_permit_cfei if t.panels > 0 else 0.0, 0.0, True),
        BuildUpLine("erc", "ERC Certificate of Compliance (net metering)", j.erc_coc_fee if job.net_metering else 0.0, 0.0, True),
        BuildUpLine("meter", "Bi-directional meter difference (net metering)", j.bidirectional_meter_fee if job.net_metering else 0.0, 0.0, True),
    ]
    direct = sum(x.direct for x in bl)
    markup = sum(x.markup for x in bl)
    selling = direct + markup
    commission = direct * j.agent_commission
    ex_vat = selling + commission
    vat = ex_vat * j.vat
    contract = ex_vat + vat
    rounded = math.ceil(contract / j.round_up_to - 1e-9) * j.round_up_to if j.round_up_to > 0 else contract
    ocm = markup * j.ocm_share
    kwp = sum((l.rating or 0) * l.qty for l in lines if l.category == "Solar Panel" and (l.rating_unit or "").upper() == "W") / 1000.0

    # ---- customer sections: Equipment, Materials, Labor, Tax; freight and commission baked in
    equip_lines = [l for l in lines if l.category in EQUIPMENT_CATEGORIES]
    other_lines = [l for l in lines if l.category not in EQUIPMENT_CATEGORIES]
    equip_selling = sum(l.selling for l in equip_lines)
    other_selling = sum(l.selling for l in other_lines)
    share_total = sum(l.truck_share for l in lines)
    freight_selling = bl[1].selling
    equip_freight = freight_selling * (sum(l.truck_share for l in equip_lines) / share_total) if share_total > 0 else 0.0
    other_freight = freight_selling - equip_freight
    services_selling = sum(x.selling for x in bl[2:])
    equip_direct = sum(l.landed for l in equip_lines)
    other_direct = sum(l.landed for l in other_lines)
    def comm(d: float) -> float:
        return commission * d / direct if direct > 0 else 0.0
    services_direct = sum(x.direct for x in bl[2:])
    equipment = equip_selling + equip_freight + comm(equip_direct + bl[1].direct * (sum(l.truck_share for l in equip_lines) / share_total if share_total else 0))
    materials = other_selling + other_freight + comm(other_direct + bl[1].direct * (sum(l.truck_share for l in other_lines) / share_total if share_total else 0))
    labor_sec = services_selling + comm(services_direct)
    subtotal = equipment + materials + labor_sec
    tax = subtotal * j.vat
    rounding = rounded - (subtotal + tax)
    labor_sec += rounding  # keep the rounded contract price; the few pesos sit in the services line
    sections = [
        {"key": "equipment", "label": "Equipment", "amount": equipment, "items": [{"name": l.name, "qty": l.qty, "unit": l.unit} for l in equip_lines]},
        {"key": "materials", "label": "Materials", "amount": materials},
        {"key": "labor", "label": "Labor", "amount": labor_sec},
        {"key": "tax", "label": "Tax (VAT 12%)", "amount": tax},
    ]

    return {
        "lines": [l.to_dict() for l in lines],
        "missing_codes": [l.code for l in lines if not l.found],
        "takeoff": t.to_dict(),
        "freight": fr.to_dict(),
        "labor": lb.to_dict(),
        "build_up": [x.to_dict() for x in bl],
        "totals": {
            "direct": direct, "markup": markup, "markup_over_direct": (markup / direct) if direct else 0.0, "selling": selling,
            "commission": commission, "contract_ex_vat": ex_vat, "vat": vat, "contract": contract, "contract_rounded": rounded,
            "ocm": ocm, "op": markup - ocm, "kwp": kwp, "price_per_wp": (rounded / (kwp * 1000)) if kwp > 0 else None,
            "materials_landed": mat_direct, "materials_selling": mat_direct + mat_markup,
        },
        "customer": {"sections": sections, "total": rounded, "subtotal_ex_vat": subtotal + rounding, "vat": tax},
        "job_inputs": job.__dict__.copy(),
    }
