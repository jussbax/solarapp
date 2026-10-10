"""Pricing configuration: every number the workbook keeps on its DRIVERS, SUPPLIERS,
ROUTE, LABOR RATES, MOB-DEMOB, TOOLS and JOB sheets, plus the BOQ generator's
role defaults. Stored as one JSON document in the app; seeded from the workbook
by the importer and editable in the app (the app is the master)."""
from __future__ import annotations

import hashlib
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class TruckConfig(BaseModel):
    basis: str = "Isuzu NMR85HS closed van, 14 x 6 x 6 ft box (shadow truck)"
    payload_kg: float = 3000
    cargo_volume_m3: float = 14.274143347
    ownership_per_trip_day: float = 8500
    driver_per_trip_day: float = 1500
    helper_per_trip_day: float = 1000
    diesel_price: float = 100
    fuel_economy_km_per_l: float = 7
    maintenance_per_km: float = 3
    trip_days_per_run: float = 1

    @property
    def running_cost_per_km(self) -> float:
        return self.diesel_price / self.fuel_economy_km_per_l + self.maintenance_per_km


class HandlingConfig(BaseModel):
    helper_day_rate: float = 1000
    typical_job_helper_hours: float = 6
    typical_fill: float = 0.144482896668418  # share of the truck a typical 6 kW job uses

    @property
    def typical_job_cost(self) -> float:
        return self.helper_day_rate / 8.0 * self.typical_job_helper_hours


class RouteConfig(BaseModel):
    """Stops in driving order: base, suppliers (farthest first), site. Matrices are stop x stop."""
    stops: list[str] = Field(default_factory=lambda: ["Pila base", "IAN Solar", "Felicity Solar", "One Point", "Blue Carbon", "Job site"])
    km: list[list[float]] = Field(default_factory=lambda: [
        [0, 110, 90, 70, 55, 10],
        [110, 0, 22, 40, 60, 115],
        [90, 22, 0, 18, 35, 90],
        [70, 40, 18, 0, 20, 70],
        [55, 60, 35, 20, 0, 55],
        [10, 115, 90, 70, 55, 0],
    ])
    toll: list[list[float]] = Field(default_factory=lambda: [
        [0, 1110, 582, 253, 104, 0],
        [1110, 0, 528, 857, 1006, 1110],
        [582, 528, 0, 329, 478, 582],
        [253, 857, 329, 0, 149, 253],
        [104, 1006, 478, 149, 0, 104],
        [0, 1110, 582, 253, 104, 0],
    ])
    base_lat: float = 14.2306   # Pila, Laguna
    base_lon: float = 121.3647
    reference_site_km: float = 10  # base to the reference site, one way
    road_factor: float = 1.3       # straight-line to road km


class CategoryRule(BaseModel):
    name: str
    markup_tier: float
    wastage: float = 0.0


DEFAULT_CATEGORIES = [
    CategoryRule(name="Solar Panel", markup_tier=0.10, wastage=0.0),
    CategoryRule(name="Inverter", markup_tier=0.10, wastage=0.0),
    CategoryRule(name="Battery", markup_tier=0.15, wastage=0.0),
    CategoryRule(name="All-in-one System", markup_tier=0.15, wastage=0.0),
    CategoryRule(name="Mounting", markup_tier=0.30, wastage=0.02),
    CategoryRule(name="Wires and Terminations", markup_tier=0.30, wastage=0.05),
    CategoryRule(name="Protective Devices", markup_tier=0.30, wastage=0.0),
    CategoryRule(name="Enclosures and Raceways", markup_tier=0.30, wastage=0.05),
    CategoryRule(name="Grounding", markup_tier=0.30, wastage=0.02),
    CategoryRule(name="Accessories", markup_tier=0.30, wastage=0.0),
    CategoryRule(name="Consumables", markup_tier=0.30, wastage=0.10),
]

EQUIPMENT_CATEGORIES = ("Solar Panel", "Inverter", "Battery", "All-in-one System")


class LaborRates(BaseModel):
    team_lead_day: float = 3000
    skilled_day: float = 1500
    laborer_day: float = 1000
    allowance_included: float = 150
    owner_day: float = 5000
    paid_hours: float = 8
    nonproductive_hours: float = 1
    pay_unit_days: float = 1.0


class RoofRates(BaseModel):
    setup_mh: float = 2
    mounting_mh_per_panel: float = 0.375
    wiring_mh_per_panel: float = 0.25
    simple_roof_factor: float = 0.75


class GroundTask(BaseModel):
    key: str
    label: str
    mounting_weight: float
    wiring_weight: float
    unit: str


class GroundRates(BaseModel):
    mounting_mh_per_unit: float = 0.893854748603352
    wiring_mh_per_unit: float = 0.43010752688172
    hybrid_pace: float = 0.375001547634115
    tasks: list[GroundTask] = Field(default_factory=lambda: [
        GroundTask(key="hybrid_inverter", label="Hybrid inverter", mounting_weight=2, wiring_weight=2, unit="per inverter"),
        GroundTask(key="gridtie_inverter", label="Grid-tie inverter", mounting_weight=1, wiring_weight=1, unit="per inverter"),
        GroundTask(key="battery_pack", label="Battery pack: anchor and connect", mounting_weight=0.5, wiring_weight=1, unit="per pack"),
        GroundTask(key="enclosure", label="Enclosure (box, DIN rail, ground bar)", mounting_weight=1, wiring_weight=0, unit="per box"),
        GroundTask(key="protective", label="Breaker, SPD or ATS", mounting_weight=0.2, wiring_weight=0.3, unit="per device"),
        GroundTask(key="conduit_m", label="Conduit or cable tray with supports", mounting_weight=0.15, wiring_weight=0, unit="per m"),
        GroundTask(key="wire_m", label="Wire pull and terminate", mounting_weight=0, wiring_weight=0.02, unit="per m"),
        GroundTask(key="mc4_pair", label="String home-run MC4", mounting_weight=0, wiring_weight=0.25, unit="per pair"),
        GroundTask(key="ground_rod", label="Ground rod: drive and bond", mounting_weight=1, wiring_weight=0.5, unit="per rod"),
        GroundTask(key="energize_job", label="Energize and commission: per job", mounting_weight=0, wiring_weight=3, unit="per job"),
        GroundTask(key="energize_inverter", label="Energize and commission: per inverter", mounting_weight=0, wiring_weight=1, unit="per inverter"),
        GroundTask(key="energize_pack", label="Energize and commission: per battery pack", mounting_weight=0, wiring_weight=0.5, unit="per pack"),
    ])

    def mh(self, key: str) -> float:
        t = next((x for x in self.tasks if x.key == key), None)  # a task the owner removed from the table counts no hours
        return 0.0 if t is None else t.mounting_weight * self.mounting_mh_per_unit + t.wiring_weight * self.wiring_mh_per_unit


class HaulingConfig(BaseModel):
    max_kg_per_person: float = 32


class MobDemobConfig(BaseModel):
    vehicle_ownership_per_day: float = 560
    running_cost_per_km: float = 12
    base_to_site_km: float = 10
    toll_per_round_trip: float = 0
    one_way_travel_hours: float = 0.25
    packaging_disposal: float = 500

    @property
    def crew_transport_per_day(self) -> float:
        return self.vehicle_ownership_per_day + 2 * self.base_to_site_km * self.running_cost_per_km + self.toll_per_round_trip


class ToolsConfig(BaseModel):
    charge_per_installation_day: float = 905.624978858076


class JobLevel(BaseModel):
    agent_commission: float = 0.05
    vat: float = 0.12
    freight_markup: float = 0.15
    services_markup: float = 0.30
    ppe_per_person_day: float = 100
    pee_seal: float = 1000
    lgu_permit_cfei: float = 5000
    erc_coc_fee: float = 1500
    bidirectional_meter_fee: float = 3000
    ocm_share: float = 0.5
    round_up_to: float = 100
    quotation_validity_days: int = 15


class JobDefaults(BaseModel):
    roof_factor: float = 0.75
    roof_closed_days: int = 1
    max_days: int = 2
    max_pairs: int = 2
    battery_haul_hours: float = 0.5
    owner_days: float = 0
    extra_km: float = 0
    extra_toll: float = 0


class WiringRules(BaseModel):
    pv_run_m: float = 25            # home run per string, each conductor
    ac_run_m: float = 15            # inverter to distribution board circuits
    grounding_run_m: float = 20
    conduit_m: float = 30
    battery_pairs_per_battery: int = 2
    dc_drop_limit: float = 0.03
    ac_drop_limit: float = 0.03
    ac_voltage: float = 230
    battery_voltage: float = 51.2
    panel_vmp_v: float = 42         # typical for 580-630 W modules
    copper_resistivity: float = 0.0172  # ohm mm2 / m
    continuous_factor: float = 1.25
    thhn_ampacity: dict[str, float] = Field(default_factory=lambda: {"3.5": 20, "5.5": 30, "8.0": 40, "14": 55, "22": 70, "30": 85})  # PEC 60 C column (3.5 mm2 = 20 A, round 3; verify the table edition)
    # Round 13 (docs/audits/round-13/engineer-brief.md, 2.3): the 75 and 90 °C columns the design analysis derates from (the
    # 75 °C column is the terminal rule's), keyed by the same sizes as the 60 °C table. CITED STAND-INS, never values the app
    # ships as fact: the NEC 2014 Table 310.15(B)(16) copper columns on the size mapping the 60 °C table follows (3.5 mm² = 12
    # AWG, 5.5 = 10, 8.0 = 8, 14 = 6, 22 = 4, 30 = 2); verify against PEC 2017 Table 3.10.1.16. The source line prints on the
    # design analysis sheet with "verify" until the owner or the PEE ticks the table confirmed.
    thhn_ampacity_75c: dict[str, float] = Field(default_factory=lambda: {"3.5": 25, "5.5": 35, "8.0": 50, "14": 65, "22": 85, "30": 115})
    thhn_ampacity_90c: dict[str, float] = Field(default_factory=lambda: {"3.5": 30, "5.5": 40, "8.0": 55, "14": 75, "22": 95, "30": 130})
    thhn_ampacity_source: str = "NEC 2014 Table 310.15(B)(16), copper, 60/75/90 °C columns on the mapping 3.5 mm² = 12 AWG, 5.5 = 10, 8.0 = 8, 14 = 6, 22 = 4, 30 = 2; the PEC 2017 equivalent: Table 3.10.1.16"
    thhn_ampacity_verified: bool = False
    battery_cable_ampacity: dict[str, float] = Field(default_factory=lambda: {"16": 100, "25": 140, "35": 170, "50": 210, "70": 270})
    pv_cable_ampacity: dict[str, float] = Field(default_factory=lambda: {"4": 40, "6": 55})
    # AC circuits (round 3, E-04): one breaker per circuit at 1.25 x the circuit current rounded up to the next standard
    # size in this list; the conductor of each side is then sized from its breaker (ampacity at or above it).
    ac_breaker_sizes_a: list[float] = Field(default_factory=lambda: [16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250])
    ac_conductors_per_circuit: int = 2      # line and neutral per circuit; the ground is the grounding run


class StringDesign(BaseModel):
    """The string design's temperatures and the coefficients a panel without its own takes (round 12, brief section 3).
    Every default here is an ASSUMPTION the owner replaces with a measured or a maker's figure; the job's warnings say
    when one was used. The design temperatures are per project the lower (cold) and the higher (hot) of the setting
    and the project's own TMY extremes (compute.py puts them in results["site"])."""
    # ASSUMPTION: the PVGIS typical-year minima of the Laguna and Batangas cells are 19.3–21.9 °C air; a typical year is not a
    # record, so the lowest is floored and the margin below taken: 14 °C. Replace with the PAGASA record low of the station nearest
    # the job when in hand (verify).
    design_cold_c: float = 14
    cold_margin_c: float = 5           # ASSUMPTION: the gap between a typical-year minimum and a record low
    # ASSUMPTION: the TMY maxima (30.5–34.1 °C) plus the module's rise at 1 kW/m² give roughly 60–65 °C; 70 is the conservative envelope
    design_hot_cell_c: float = 70
    # ASSUMPTION (brief 6.5): a conservative envelope for the crystalline-silicon families on the sheet; more negative is
    # conservative at both ends (a higher cold Voc, a lower hot Vmp). The maker's figure on the item replaces it and the warning
    # temp_coeff_default says a default was used.
    temp_coeff_voc_default_pct: float = -0.30
    temp_coeff_pmax_default_pct: float = -0.35   # used for Vmp
    temp_coeff_isc_default_pct: float = 0.05     # informational only (3.3): never stacked on the 1.25 irradiance factor
    # the PV-circuit sizing rule of the PEC's solar PV article (the NEC 690.8 equivalent: verify the clause in the current edition)
    isc_irradiance_factor: float = 1.25
    # the standard DC MCB ratings the suppliers list (verify against the price lists; like wiring.ac_breaker_sizes_a)
    dc_breaker_sizes_a: list[float] = Field(default_factory=lambda: [16, 20, 25, 32, 40, 50, 63])


class DeratingRules(BaseModel):
    """The design analysis sheet's derating (round 13, docs/audits/round-13/engineer-brief.md, 2.3). Every table here is a
    CITED STAND-IN from the NEC edition the PEC follows, never a value the app ships as fact: each carries its source line
    and a `_verified` flag the owner or the PEE ticks once the table is checked against the PEC 2017; the sheet prints the
    source with "verify" until then. Every default temperature is an ASSUMPTION and prints as one."""
    # ASSUMPTION: the PVGIS typical-year air maxima of the Laguna and Batangas cells are 30.5–34.1 °C (round 12); per project the
    # outdoor runs take the higher of this and the project cell's own maximum, ceiled
    ambient_outdoor_c: float = 35
    ambient_indoor_c: float = 30            # ASSUMPTION: the NEC tables' 30 °C base, indoors
    conduit_height_above_roof_mm: float = 25   # ASSUMPTION: a conduit on the rails; picks the rooftop adder band below
    # the rooftop adder bands by height above the roof, °C added to the ambient for a raceway on the roof: the band is the largest
    # key at or below the height in mm. NEC 2014 Table 310.15(B)(3)(c); the NEC 2017 kept only +33 °C for raceways under 22 mm
    # above the roof; verify which the PEC 2017 adopted (brief 6.3 asks which band table the PEE applies)
    rooftop_adder_c: dict[str, float] = Field(default_factory=lambda: {"0": 33, "13": 22, "90": 17, "300": 14, "900": 8})
    rooftop_adder_source: str = "NEC 2014 Table 310.15(B)(3)(c) by height above the roof (0–13 mm +33, 13–90 +22, 90–300 +17, 300–900 +14, above 900 +8 °C); the NEC 2017 keeps only +33 °C under 22 mm; which the PEC 2017 adopted is the open question"
    rooftop_adder_verified: bool = False
    # the temperature correction by the formula the NEC permits in place of its table: F = sqrt((T_insul − T_amb) / (T_insul − 30))
    temperature_correction_source: str = "NEC 310.15(B)(2) formula F = sqrt((T_insulation − T_ambient) / (T_insulation − 30)) in place of Table 310.15(B)(2)(a); the PEC 2017 equivalent clause"
    temperature_correction_verified: bool = False
    # the bundling (adjustment) factor by the count of current-carrying conductors, in percent: the band is the largest key at or
    # below the count. NEC 310.15(B)(3)(a); PEC verify. The neutral of a 2-wire 230 V circuit counts; the EGC does not.
    bundling_factor_pct: dict[str, float] = Field(default_factory=lambda: {"1": 100, "4": 80, "7": 70, "10": 50, "21": 45, "31": 40, "41": 35})
    bundling_factor_source: str = "NEC 310.15(B)(3)(a): 1–3 current-carrying conductors 100 %, 4–6 80 %, 7–9 70 %, 10–20 50 %, 21–30 45 %, 31–40 40 %, 41 and more 35 %; the PEC 2017 equivalent table"
    bundling_factor_verified: bool = False
    # the conduit fill limit in percent by the count of conductors in the raceway: 1 → 53 %, 2 → 31 %, 3 and more → 40 %
    conduit_fill_limit_pct: dict[str, float] = Field(default_factory=lambda: {"1": 53, "2": 31, "3": 40})
    conduit_fill_source: str = "NEC Chapter 9 Table 1 (one conductor 53 %, two 31 %, three or more 40 % of the raceway's inside area); the PEC 2017 equivalent in Chapter 10"
    conduit_fill_verified: bool = False
    # the next-size-up rule: a breaker above the derated ampacity may be the next standard size above it when the rating is at or
    # below this and the circuit is not a multi-outlet branch circuit, and the conductor still carries the load
    next_size_up_max_a: float = 800
    next_size_up_source: str = "NEC 240.4(B): the next standard overcurrent device above the conductor's ampacity, up to 800 A, not on a multi-outlet branch circuit; the PEC 2017 equivalent in Article 2.40"
    next_size_up_verified: bool = False
    # the terminal rule: the conductor's ampacity in the terminal's column (75 °C), uncorrected, covers the design current and the breaker
    terminal_rating_c: float = 75
    terminal_rule_source: str = "NEC 110.14(C): the conductor's ampacity in the 75 °C column, uncorrected, at or above the design current and the breaker; the PEC 2017 equivalent in Article 1.10"
    terminal_rule_verified: bool = False
    # ASSUMPTION for a wire item whose insulation rating is not typed on it: THHN and PV wire are 90 °C types (verify the items)
    default_insulation_c: float = 90
    # ASSUMPTION for an inverter without a fault-current figure on its item: a grid-interactive inverter is current-limited to
    # about 1.5 × its rated output current for one cycle (verify on the datasheet)
    inverter_fault_factor: float = 1.5


class GroundingRules(BaseModel):
    """The grounding conductor sizes the design analysis checks (round 13, brief 2.3). Cited stand-ins with a source and a
    `_verified` flag, like the derating tables."""
    # the equipment grounding conductor by the circuit's overcurrent device rating: the row is the smallest key at or above the
    # OCPD; mm² on the PEC's metric series for the NEC's 14/12/10/8/6/4/3 AWG
    egc_by_ocpd: dict[str, float] = Field(default_factory=lambda: {"15": 2.0, "20": 3.5, "30": 5.5, "40": 5.5, "60": 5.5, "100": 8.0, "200": 14, "300": 22, "400": 30})
    egc_source: str = "NEC 250.122 Table (copper: 15 A 14 AWG, 20 A 12, 30–60 A 10, 100 A 8, 200 A 6, 300 A 4, 400 A 3) on the PEC's metric series; the PEC 2017 equivalent: Table 2.50.1.122"
    egc_verified: bool = False
    # the grounding electrode conductor to a rod electrode need not be larger than this
    gec_rod_max_mm2: float = 14
    gec_source: str = "NEC 250.66(A): the grounding electrode conductor to a rod electrode need not exceed 6 AWG (= 14 mm²) copper; the PEC 2017 equivalent in Article 2.50"
    gec_verified: bool = False


class BoqRoles(BaseModel):
    """Default item codes per role, resolved from the DB at import; editable."""
    rail: str = "BC-MNT-001"
    rail_length_m: float = 2.4
    l_foot: str = "BC-MNT-006"
    l_feet_per_rail: int = 3
    end_clamp: str = "BC-MNT-003"
    mid_clamp: str = "BC-MNT-004"
    splice: str = "BC-MNT-005"
    pv_cable_red: dict[str, str] = Field(default_factory=lambda: {"4": "BC-WIR-001", "6": "BC-WIR-003"})
    pv_cable_black: dict[str, str] = Field(default_factory=lambda: {"4": "BC-WIR-002", "6": "BC-WIR-004"})
    thhn: dict[str, str] = Field(default_factory=lambda: {"5.5": "IAN-WIR-002", "8.0": "IAN-WIR-004", "14": "IAN-WIR-005", "22": "IAN-WIR-007", "30": "IAN-WIR-009"})
    battery_cable_pair: dict[str, str] = Field(default_factory=lambda: {"16": "OP-WIR-005", "25": "OP-WIR-006", "35": "OP-WIR-007", "50": "OP-WIR-008", "70": "OP-WIR-009"})
    mc4_pair: str = "IAN-WIR-026"
    mc4_pairs_per_string: int = 2
    dc_breaker: str = "IAN-PRT-009"
    dc_breaker_pattern: str = "DC BREAKER"    # round 12 (3.2): when the role item's rating is below the string's 1.56 × Isc, the smallest item whose name matches and covers it
    dc_spd: str = "IAN-PRT-018"
    battery_breaker_pattern: str = "BATTERY BREAKER"
    battery_breaker_fallback: str = "IAN-PRT-003"
    ats: str = "OP-PRT-035"
    ats_amps: float = 63
    ac_breaker: str = "IAN-PRT-027"
    ac_breaker_amps: float = 63
    ac_breakers_per_inverter: int = 1          # inverter side: the output circuit to the loads (round 3, E-04; was 4 for every circuit and the disconnect)
    ac_spd: str = "IAN-PRT-035"
    ac_spds_per_inverter: int = 1              # one Type 2 SPD per AC board (round 3, E-06; was 4, one per breaker)
    enclosure: str = "OP-ENC-007"
    enclosures: int = 1                        # one box per inverter, AC and DC protection together (round 3, E-06; was 2)
    cable_tray: str = "OP-ENC-009"
    cable_trays: int = 1
    conduit: str = "IAN-ENC-011"
    ground_rod: str = "OP-GND-001"
    ground_rods: int = 1
    earth_lug: str = "IAN-GND-001"
    earth_lugs: int = 4
    sealant: str = "IAN-CSM-001"
    sealants: int = 2
    max_panels_per_string: int = 10
    # One default inverter per system kind, in parallel units when more is needed; blank = the cheapest that fits.
    # Grid jobs (net metering, with or without a battery) need a grid-interactive unit the DU accepts; the importer
    # sets the grid default to the first grid-interactive hybrid in the workbook (FS-INV-001 in the bundled one).
    default_inverter_code_grid: str = "FS-INV-008"   # the owner's eco-hybrid on every job; it may export (confirmed with the maker)
    default_inverter_code_offgrid: str = "FS-INV-008"   # Felicity 6 kW eco-hybrid, an off-grid type
    inverter_exclude_words: list[str] = Field(default_factory=lambda: ["3P", "3-phase", "high-voltage", "HV"])
    battery_exclude_words: list[str] = Field(default_factory=lambda: ["rack", "controller module", "slave", "per kWh", "12V", "24V", "25.6V", "12 V", "24 V"])
    # ---- round 3 (E-01, E-04, E-06): the parallel rule, the grid-side circuits and the roles the BOM used to omit.
    # A role whose code is blank still puts its line on the BOM, with the quantity and no price, and a warning to add
    # the item on the Materials page: the crew and the PEE see what the design needs, the customer price never
    # carries an invented figure.
    inverter_parallel_tolerance_pct: float = 10   # a requirement this far above one unit's kW keeps one unit (with a warning) rather than two in parallel; 0 = never
    ac_grid_breakers_per_inverter: int = 2        # grid side: the grid-to-inverter feed and the maintenance bypass, sized on the inverter's AC input rating
    ac_disconnect: str = "IAN-PRT-030"            # the visible, lockable AC disconnect for the electric company at the service (verify the DU's requirement)
    ac_disconnects: int = 1
    export_limiter: str = ""                      # optional: the export limiter or CT for the weeks between switch-on and the two-way meter (verify with the DU)
    array_bonding_wire: str = "IAN-WIR-029"       # the equipment grounding conductor along the array (bare copper where the LGU asks; verify the gauge with the PEE)
    bonding_extra_m_per_row: float = 2            # jumpers between the rail lines of a row and to the next row, on top of the row's length
    bonding_lugs_per_panel: int = 1               # panel frame to rail (unless the clamps are listed as bonding clamps)
    bonding_lugs_per_rail_line: int = 1           # each rail line to the grounding conductor (two lines per row)

    @model_validator(mode="before")
    @classmethod
    def _migrate_single_default(cls, data: Any) -> Any:
        """A config saved before the per-kind defaults carried one `default_inverter_code` (an off-grid unit on
        every job); it moves into the off-grid slot and the grid slot takes the class default. A config saved
        before the AC circuit split (round 3) carried the sample job's counts per inverter (4 breakers, 4 SPDs,
        2 enclosures), which the audit showed over-counted; they take the new defaults once, the first time the
        grid-side count is missing."""
        if isinstance(data, dict) and "default_inverter_code" in data:
            data = dict(data)
            old = data.pop("default_inverter_code")
            if "default_inverter_code_offgrid" not in data:
                data["default_inverter_code_offgrid"] = old or ""
        if isinstance(data, dict) and "ac_grid_breakers_per_inverter" not in data:
            data = dict(data)
            for key in ("ac_breakers_per_inverter", "ac_spds_per_inverter", "enclosures"):
                data.pop(key, None)
        return data

    def default_inverter_for(self, kind: str) -> str:
        return self.default_inverter_code_offgrid if kind == "off_grid" else self.default_inverter_code_grid


class PaymentMilestone(BaseModel):
    key: str
    label: str
    share: float = Field(ge=0, le=1)
    event: str = "signing"          # signing, materials_on_site, installation_done, commissioning, meter_installed
    offset_days: int = 0


class PaymentPlan(BaseModel):
    """Customer payments. Milestone shares plus the instalment share should add up to 1."""
    milestones: list[PaymentMilestone] = Field(default_factory=lambda: [
        PaymentMilestone(key="downpayment", label="Downpayment on signing", share=0.5, event="signing"),
        PaymentMilestone(key="delivery", label="On delivery of materials to your house", share=0.4, event="materials_on_site"),
        PaymentMilestone(key="completion", label="On switch-on and testing", share=0.1, event="commissioning"),
    ])
    installments: int = Field(default=0, ge=0)              # number of equal instalments for the balance
    installment_share: float = Field(default=0, ge=0, le=1)  # share of the contract paid by instalments
    installment_interval_days: int = Field(default=30, ge=1)
    installment_start_event: str = "commissioning"
    installment_first_offset_days: int = Field(default=30, ge=0)


class ProgramConfig(BaseModel):
    """Program of works defaults: site day, durations and cash timing. Durations marked as assumptions have no data yet."""
    depart_time: str = "06:00"
    lunch_start: str = "12:00"
    lunch_minutes: int = 60
    travel_speed_kmh: float = 40            # for the extra km beyond the route's reference site
    permit_prep_days: int = 2               # plans, PEE sign and seal
    permit_approval_days: int = 7           # assumption: LGU electrical permit
    cfei_days: int = 5                      # assumption: certificate of final electrical inspection after installation
    netmeter_application_days: int = 30     # assumption: DU evaluation and net metering agreement
    netmeter_meter_days: int = 15           # assumption: DU inspection and bi-directional meter after commissioning
    sourcing_days_before_install: int = 1   # pickup run, cash at the suppliers
    install_gap_after_permit_days: int = 1
    commissioning_offset_days: int = 0      # 0 = on the last installation day
    labour_paid_days_after_job: int = 0
    commission_paid_days_after_job: int = 0
    vat_remit_days_after_completion: int = 30
    # Floors for the hour-by-hour plan only (minutes of wall-clock time per task); the labour price is not changed.
    # Today's rates give a ten-minute commissioning, which no PEE or DU inspector accepts.
    min_task_minutes: dict[str, int] = Field(default_factory=lambda: {"commissioning": 120, "battery": 60, "inverter": 60})
    late_finish_max_minutes: int = 120   # the last priced day may run this long past the usual end before a new day is added
    payment: PaymentPlan = Field(default_factory=PaymentPlan)
    # Hours the customer's power is off on installation day (the inverter is cut over at the panel board): the owner's figure from
    # the crew's practice, printed on the proposal; 0 (blank) prints no length. Not computed anywhere.
    installation_outage_hours: float = Field(default=0, ge=0, le=24)


class SystemLosses(BaseModel):
    """Losses after the panels, as the share of energy that gets through. The simulation is "at the panels"
    (k_site is measured in the plane of the array and contains none of these); the product is applied to the
    per-kWp profile before sizing and economics, so the array is sized on energy at the meter and the customer
    documents print the figure the bill will later show."""
    inverter: float = Field(default=0.96, gt=0, le=1)   # DC to AC conversion, the datasheet's weighted efficiency
    wiring: float = Field(default=0.98, gt=0, le=1)     # DC and AC cable runs, connectors and terminations
    soiling: float = Field(default=0.97, gt=0, le=1)    # dust and dirt between rains; verify locally (rice-field roofs collect more in the dry season)
    other: float = Field(default=0.99, gt=0, le=1)      # module mismatch, availability, anything else after the panels

    @property
    def factor(self) -> float:
        return self.inverter * self.wiring * self.soiling * self.other


class SizingRules(BaseModel):
    """Design choices that are the owner's, not the engine's."""
    # The evenings the battery must carry without sun. 1 = the night deficit of the worst typical day (the rule
    # until now); 2 = twice that, and so on. The hourly-year balance then reports how often it still runs out.
    days_of_autonomy: float = Field(default=1.0, ge=0.5, le=7.0)
    # The panel on every job (round 4). Blank = automatic: of the usable panels in the materials list (active, category
    # Solar Panel, with wattage, length and width) the one that gives the most kWp on each roof, ties to the lower list
    # price per watt. A code (BC-PNL-001) puts that panel on every job; an engineer may still pick another for one
    # project under Design and outputs › System design. A code that is not a usable panel falls back to automatic with a warning.
    panel_code: str = Field(default="", max_length=40)


class EconomicsConfig(BaseModel):
    """Customer economics defaults. The tariff comes from the latest bill when there is one."""
    tariff_php_per_kwh: float = 12.0          # used when the audit has no bill amount
    export_rate_php_per_kwh: float = 6.5      # net metering credit: the DU's blended generation rate, not the retail rate
    tariff_escalation: float = 0.03           # per year
    degradation: float = 0.005                # panel output loss per year
    analysis_years: int = 25
    discount_rate: float = 0.08
    # Battery life for the replacement schedule: 0 = the battery warranty years in the company profile (5 today: the
    # battery datasheets give 5 years, though the supplier price list says 10 for the Felicity FLB line; verify).
    # A number here overrides the warranty. Replaces the fixed 10-year `battery_life_years` of earlier configs, which
    # is dropped on load so the warranty rule applies to every database.
    battery_life_years_override: int = 0
    inverter_life_years: int = 12             # not the warranty (5 years from the maker): the years before the economics replace the inverter
    replacement_labor_php: float = 0          # labor added to each battery or inverter replacement, pesos including VAT; 0 = none (verify)
    om_share_per_year: float = 0.005          # cleaning and checks, share of the contract price per year
    co2_kg_per_kwh: float = 0.71              # Philippine grid emission factor


class QuickConfig(BaseModel):
    """Quick estimate (public, four questions): typical roof and panel, no site measurements."""
    enabled: bool = True
    panel_code: str = "BC-PNL-001"
    k_site: float = 0.95                 # typical site factor seen on measured roofs
    tilt_deg: float = 10
    azimuth_deg: float = 180
    max_panels: int = 40                 # no roof given, so a generous cap
    panels_per_row: int = 8
    peak_factor: float = 2.0             # instantaneous peak over the busiest hour's average
    price_round_to: float = 1000
    max_requests_per_hour: int = 30      # per visitor address


class PricingConfig(BaseModel):
    company_base: str = "PL Development Inc., Pila, Laguna"
    truck: TruckConfig = Field(default_factory=TruckConfig)
    handling: HandlingConfig = Field(default_factory=HandlingConfig)
    route: RouteConfig = Field(default_factory=RouteConfig)
    categories: list[CategoryRule] = Field(default_factory=lambda: list(DEFAULT_CATEGORIES))
    labor: LaborRates = Field(default_factory=LaborRates)
    roof: RoofRates = Field(default_factory=RoofRates)
    ground: GroundRates = Field(default_factory=GroundRates)
    hauling: HaulingConfig = Field(default_factory=HaulingConfig)
    mobdemob: MobDemobConfig = Field(default_factory=MobDemobConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    job: JobLevel = Field(default_factory=JobLevel)
    job_defaults: JobDefaults = Field(default_factory=JobDefaults)
    program: ProgramConfig = Field(default_factory=ProgramConfig)
    economics: EconomicsConfig = Field(default_factory=EconomicsConfig)
    system_losses: SystemLosses = Field(default_factory=SystemLosses)
    sizing: SizingRules = Field(default_factory=SizingRules)
    quick: QuickConfig = Field(default_factory=QuickConfig)
    wiring: WiringRules = Field(default_factory=WiringRules)
    string_design: StringDesign = Field(default_factory=StringDesign)
    # round 13: the design analysis sheet's derating tables and the grounding conductor sizes (Settings › Design analysis)
    derating: DeratingRules = Field(default_factory=DeratingRules)
    grounding: GroundingRules = Field(default_factory=GroundingRules)
    roles: BoqRoles = Field(default_factory=BoqRoles)
    imported_from: Optional[str] = None
    imported_at: Optional[str] = None
    # round 12: when the datasheet workbooks were last imported, and which files (a stamp, like imported_at; never a price)
    datasheets_imported_from: Optional[str] = None
    datasheets_imported_at: Optional[str] = None

    def category(self, name: str) -> CategoryRule:
        for c in self.categories:
            if c.name == name:
                return c
        return CategoryRule(name=name, markup_tier=0.30, wastage=0.0)

    @property
    def productive_hours(self) -> float:
        return self.labor.paid_hours - self.labor.nonproductive_hours - 2 * self.mobdemob.one_way_travel_hours


# Settings that never move a price or a customer document: the website estimate's own knobs and the import stamp.
VERSION_EXCLUDES = {"quick", "imported_from", "imported_at", "datasheets_imported_from", "datasheets_imported_at", "company_base"}


def settings_version(cfg: PricingConfig) -> str:
    """A short fingerprint of every setting that moves a price, the program or the savings. It is stored with a
    priced project's results; when it no longer matches the current settings the project is flagged and a job
    from stage quoted onward is re-priced only on an explicit confirmation."""
    return hashlib.sha256(cfg.model_dump_json(exclude=VERSION_EXCLUDES).encode()).hexdigest()[:16]
