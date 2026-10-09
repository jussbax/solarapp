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
    grid_interactive: Optional[bool] = None   # inverters: may export (anti-islanding certified); None = unknown
    certifications: str = ""                  # inverters: the listing printed on the proposal and the DU pack

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def price_lines(bom: list[BomLine], catalog: Catalog, cfg: PricingConfig) -> list[PricedLine]:
    out: list[PricedLine] = []
    for line in bom:
        item = catalog.get(line.code)
        if item is None:
            # no such item: the line keeps its role's name so the crew and the PEE read what the design needs, and no price
            name = line.role.replace("_", " ").capitalize() + (" (no item in the materials list)" if line.code.startswith("NO-ITEM-") else " (code not in the materials list)")
            out.append(PricedLine(line.code, line.role, line.note, name, "", "", "", line.qty, 0, 0, 0, 0, 0, 0, 0, None, "", False, found=False))
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
            grid_interactive=item.grid_interactive, certifications=item.certifications or "",
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
    closed_days = max(1, int(job.roof_closed_days or 0))  # the roof closes in at least a day; 0 (the workbook's #DIV/0!) reads as 1
    min_pairs_roof = max(1, int(math.ceil(roof_mh / (2 * prod * closed_days) - 1e-12))) if roof_mh > 0 else 0
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


_RATING_UNITS = {"w": "W", "kw": "kW", "kwh": "kWh"}


def _n(q: float) -> str:
    return f"{int(q)}" if float(q).is_integer() else f"{q:g}"


def _pct(rate: float) -> str:
    """A rate from the settings as the customer reads it: 0.12 -> "12%", 0.125 -> "12.5%"."""
    return f"{rate * 100:g}%"


def customer_item_name(cat: str, cat_lines: list[PricedLine]) -> str:
    """The customer's line for a main item, built from quantity, rating and supplier, never the catalogue string:
    "Solar panels: 6 × 585 W (Blue Carbon)", "Hybrid inverter: 6 kW (Felicity Solar)", "Lithium battery (LiFePO4): 15 kWh (Blue Carbon)"."""
    label = {"Solar Panel": "Solar panels", "Inverter": "Inverter", "Battery": "Battery", "All-in-one System": "All-in-one system"}.get(cat, cat)
    parts = []
    for l in cat_lines:
        unit = _RATING_UNITS.get((l.rating_unit or "").strip().lower(), (l.rating_unit or "").strip())
        who = f" ({l.supplier})" if l.supplier else ""
        n = l.qty
        if cat == "Battery":
            low = l.name.lower()
            label = "Lithium battery (LiFePO4)" if "lifepo" in low else "Lithium battery" if ("lithium" in low or "li-ion" in low) else "Battery"
            if l.rating and unit == "kWh":
                parts.append((f"{n * l.rating:.0f} kWh" if n == 1 else f"{_n(n)} × {l.rating:.0f} kWh ({n * l.rating:.0f} kWh in all)") + who)
                continue
        elif cat == "Inverter":
            label = "Hybrid inverter" if l.is_hybrid_inverter else "Inverter"
        if l.rating and unit:
            rating = f"{l.rating:g} {unit}"
            parts.append((f"{_n(n)} × {rating}" if (cat == "Solar Panel" or n != 1) else rating) + who)
        else:  # no rating on the item: the quantity and the catalogue name are all there is
            parts.append(f"{_n(n)} × {l.name}{who}")
    return f"{label}: " + ", ".join(parts)


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

    # ---- customer sections, in the owner's order: Materials, Labor, Equipment (tools), Tax.
    # Every line is priced for the customer: freight spread over the material lines by truck share,
    # commission over every line in proportion to direct cost, and the rounding pesos on the labour line.
    def comm(d: float) -> float:
        return commission * d / direct if direct > 0 else 0.0
    share_total = sum(l.truck_share for l in lines)
    freight = bl[1]
    # materials by catalogue category, the customer does not get the item list
    cat_order = ["Solar Panel", "Inverter", "Battery", "All-in-one System", "Mounting", "Wires and Terminations", "Protective Devices",
                 "Enclosures and Raceways", "Grounding", "Accessories", "Consumables"]
    cat_label = {"Solar Panel": "Solar panels", "Inverter": "Inverter", "Battery": "Battery", "All-in-one System": "All-in-one system",
                 "Mounting": "Roof mounting rails and clamps", "Wires and Terminations": "Cables and connectors", "Protective Devices": "Breakers and surge protection",
                 "Enclosures and Raceways": "Electrical boxes and conduit", "Grounding": "Grounding (earthing)", "Accessories": "Accessories",
                 "Consumables": "Sealant, fasteners and other small items"}
    by_cat: dict[str, dict] = {}
    for l in lines:
        fshare = (l.truck_share / share_total) if share_total > 0 else 0.0
        amount = l.selling + freight.selling * fshare + comm(l.landed + freight.direct * fshare)
        c = by_cat.setdefault(l.category, {"amount": 0.0, "qty": 0.0, "names": []})
        c["amount"] += amount
        c["qty"] += l.qty
        if l.name and l.name not in c["names"]:
            c["names"].append(l.name)
    mat_items = []
    for cat in cat_order + [c for c in by_cat if c not in cat_order]:
        c = by_cat.get(cat)
        if not c or c["amount"] <= 0:
            continue
        main = cat in EQUIPMENT_CATEGORIES
        label = cat_label.get(cat, cat)
        if main:
            mat_items.append({"key": cat, "name": customer_item_name(cat, [l for l in lines if l.category == cat]), "qty": c["qty"], "unit": "pc", "amount": c["amount"], "main": True})
        else:
            mat_items.append({"key": cat, "name": label, "qty": 1, "unit": "lot", "amount": c["amount"], "main": False})
    crew_text = f"1 team lead, {lb.pairs} skilled {'technician' if lb.pairs == 1 else 'technicians'}, {lb.pairs + 1} helpers" if lb.pairs else ""
    labor_names = {
        "labor": (f"Installation crew: {crew_text}" if crew_text else "Installation labor", lb.days, "day"),
        "mobdemob": ("Crew transport to and from your house", lb.days, "day"),
        "ppe": ("Crew safety gear", lb.person_days, "person-day"),
        "seal": ("Electrical plans, signed and sealed by a Professional Electrical Engineer", 1, "lot"),
        "permit": ("Electrical permit and final inspection certificate (city or municipal office)", 1, "lot"),
        "erc": ("ERC certificate of compliance (required for net metering)", 1, "lot"),
        "meter": ("Two-way meter from your electric company (net metering)", 1, "lot"),
    }
    labor_items = []
    for x in bl[2:]:
        if x.key == "tools" or x.selling <= 0:
            continue
        name, qty, unit = labor_names.get(x.key, (x.label, 1, "lot"))
        labor_items.append({"key": x.key, "name": name, "qty": qty, "unit": unit, "amount": x.selling + comm(x.direct)})
    tools_line = next(x for x in bl if x.key == "tools")
    equip_items = [{"key": "tools", "name": "Installation tools", "qty": lb.days, "unit": "day", "amount": tools_line.selling + comm(tools_line.direct)}] if tools_line.selling > 0 else []
    materials = sum(i["amount"] for i in mat_items)
    labor_sec = sum(i["amount"] for i in labor_items)
    equipment = sum(i["amount"] for i in equip_items)
    subtotal = materials + labor_sec + equipment
    # VAT on the contract as the customer pays it: the rounded total is VAT-inclusive, so VAT = total x rate / (1 + rate)
    # and the base is the rest; the rounding pesos (the base less the ex-VAT sum) sit on the crew line, so
    # "VAT, 12% of the amounts above" is true to the peso and a VAT worked back from the total gives the same figure.
    tax = rounded * j.vat / (1 + j.vat)
    rounding = (rounded - tax) - subtotal
    labor_sec += rounding
    if labor_items:
        labor_items[0]["amount"] += rounding
    vat_pct = _pct(j.vat)
    sections = [
        {"key": "materials", "label": "Materials", "amount": materials, "items": mat_items},
        {"key": "labor", "label": "Installation and permits", "amount": labor_sec, "items": labor_items},
        {"key": "equipment", "label": "Installation tools", "amount": equipment, "items": equip_items},
        {"key": "tax", "label": f"VAT ({vat_pct})", "amount": tax, "items": [{"key": "vat", "name": f"VAT, {vat_pct} of the amounts above", "qty": 1, "unit": "lot", "amount": tax}]},
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
        # The three figures the proposal prints as its own rows (the owner's decision: a before-VAT and an after-VAT
        # price on every proposal): the contract price before VAT, the VAT at the settings' rate, and the total.
        # Commission is inside every line at the settings' rate on every job; nothing of it reaches this block.
        "customer": {"sections": sections, "total": rounded, "subtotal_ex_vat": rounded - tax, "vat": tax, "vat_rate": j.vat, "vat_label": f"VAT ({vat_pct})"},
        "job_inputs": job.__dict__.copy(),
    }
