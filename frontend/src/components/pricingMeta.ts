/** The pricing settings as the owner reads them: every setting's label, unit, decimals and help (META), the section
 * headings and sub-blocks, the shared draft's context, and the index "Find a setting" searches. Data and functions
 * only; the components are in PricingSettings.tsx. */
import { createContext, useContext, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { PricingConfig } from '../types'
import { SETTINGS_ENTRIES, WEBSITE_SECTION, type SettingsEntry } from './shared'

/* ---------- what each section and setting is called, with its unit, decimals and help ---------- */

export const OTHER_GROUP = { id: 'other', label: 'Other settings', lead: 'Sections added since the pages above were drawn.' }

/** Section headings as the pages print them (short: the page name already says the rest). */
export const SECTION_LABELS: Record<string, string> = {
  company_base: 'Company base', truck: 'Truck', handling: 'Handling at base', route: 'Route', categories: 'Markup and wastage by category',
  labor: 'Labor day rates', roof: 'Roof work', ground: 'Ground work', hauling: 'Hauling', mobdemob: 'Crew transport', tools: 'Tools', job: 'Fees, markups and VAT',
  job_defaults: 'Job defaults', wiring: 'Wiring rules', roles: 'Items the generator uses', program: 'Program of works', economics: 'Customer savings',
  system_losses: 'Losses after the panels', sizing: 'Battery autonomy', quick: 'Estimate page',
}
export const SKIP = new Set(['imported_from', 'imported_at'])
/** Percentages are stored as fractions (0.12) and edited as percent (12). */
export const PCT_KEYS = new Set([
  'vat', 'agent_commission', 'freight_markup', 'services_markup', 'ocm_share', 'tariff_escalation', 'degradation', 'discount_rate', 'om_share_per_year',
  'dc_drop_limit', 'ac_drop_limit', 'installment_share', 'dealer_discount', 'payment_fee', 'wastage', 'markup', 'roof_factor', 'k_site',
  'inverter', 'wiring', 'soiling', 'other',
])
export const TIME_KEYS = new Set(['depart_time', 'lunch_start'])
/** Keys the grid does not print as cells: the base pin is drawn with the company base, the late finish row sits in the minutes table. */
export const HIDDEN = new Set(['route.base_lat', 'route.base_lon', 'program.late_finish_max_minutes'])

export interface SettingMeta {
  label: string
  /** Beside the control, twelve characters at most; a longer qualifier goes in the help line. */
  unit?: string
  /** Decimals shown; when absent, derived from the unit (money 0, hours 2, percent 1, ...). */
  decimals?: number
  /** One short line under the control. */
  help?: string
  /** The long explanation, behind the "?". */
  about?: string
  /** A constant the owner never edits (shown, not typed). */
  readOnly?: boolean
  /** Two columns wide (long codes and names). */
  wide?: boolean
}

export const VAT_ABOUT = 'The proposal prints "VAT (12%)" from this figure, worked out on the rounded contract (VAT = total × rate ÷ (1 + rate)), so the before-VAT price, the VAT and the total agree to the peso.'

/** Every pricing setting: label, unit, decimals and the one-line help, with the long text behind the "?". */
export const META: Record<string, SettingMeta> = {
  // the fees, markups and VAT
  'job.agent_commission': { label: 'Commission', unit: '%', help: 'Of the direct cost', about: 'Paid in cash after the job. Every job carries it (no per-job switch); nothing of it reaches the customer documents.' },
  'job.vat': { label: 'VAT', unit: '%', about: VAT_ABOUT },
  'job.freight_markup': { label: 'Freight markup', unit: '%' },
  'job.services_markup': { label: 'Services markup', unit: '%', help: 'Labor, permits, tools' },
  'job.ppe_per_person_day': { label: 'Safety gear', unit: '₱ a day', help: 'Per person on site' },
  'job.pee_seal': { label: 'PEE sign and seal', unit: '₱' },
  'job.lgu_permit_cfei': { label: 'Electrical permit and final inspection', unit: '₱' },
  'job.erc_coc_fee': { label: 'ERC Certificate of Compliance', unit: '₱' },
  'job.bidirectional_meter_fee': { label: 'Net metering meter', unit: '₱' },
  'job.ocm_share': { label: 'Overhead share of markup', unit: '%' },
  'job.round_up_to': { label: 'Round the contract up to', unit: '₱' },
  'job.quotation_validity_days': { label: 'Proposal valid for', unit: 'days' },
  // labor day rates
  'labor.team_lead_day': { label: 'Team lead', unit: '₱ a day' },
  'labor.skilled_day': { label: 'Skilled technician', unit: '₱ a day' },
  'labor.laborer_day': { label: 'Helper', unit: '₱ a day' },
  'labor.allowance_included': { label: 'Allowance included', unit: '₱ a day', help: 'Part of each day rate' },
  'labor.owner_day': { label: 'Owner on site', unit: '₱ a day' },
  'labor.paid_hours': { label: 'Paid hours', unit: 'h a day', decimals: 1 },
  'labor.nonproductive_hours': { label: 'Non-productive hours', unit: 'h a day', decimals: 1 },
  'labor.pay_unit_days': { label: 'Pay unit', unit: 'days', decimals: 0, about: 'Labor is paid in whole units of this many days.' },
  // job defaults
  'job_defaults.roof_factor': { label: 'Roof productivity factor', unit: '%' },
  'job_defaults.roof_closed_days': { label: 'Days the roof is closed', unit: 'days' },
  'job_defaults.max_days': { label: 'Max installation days', unit: 'days' },
  'job_defaults.max_pairs': { label: 'Max roof pairs', unit: 'pairs' },
  'job_defaults.battery_haul_hours': { label: 'Battery haul', unit: 'h' },
  'job_defaults.owner_days': { label: 'Owner days on site', unit: 'days' },
  'job_defaults.extra_km': { label: 'Extra km', unit: 'km', help: 'One way' },
  'job_defaults.extra_toll': { label: 'Extra toll', unit: '₱' },
  // roof, ground, hauling, crew transport, tools
  'roof.setup_mh': { label: 'Roof set-up', unit: 'h', help: 'Once per roof' },
  'roof.mounting_mh_per_panel': { label: 'Mounting', unit: 'h per panel' },
  'roof.wiring_mh_per_panel': { label: 'Wiring', unit: 'h per panel' },
  'roof.simple_roof_factor': { label: 'Simple-roof factor', unit: '×', about: 'The share of the man-hours a simple roof takes.' },
  'ground.mounting_mh_per_unit': { label: 'Mounting', unit: 'h per unit', help: 'Per weighted task unit' },
  'ground.wiring_mh_per_unit': { label: 'Wiring', unit: 'h per unit', help: 'Per weighted task unit' },
  'ground.hybrid_pace': { label: 'Hybrid pace', unit: '×', about: 'Ground work runs at this share of the pace when there is an inverter or a battery to connect.' },
  'ground.tasks': { label: 'Ground tasks', help: 'Weight × rate = man-hours', about: 'Each task is a weight on the mounting and wiring rates above, per unit of what the design counts (an inverter, a metre of conduit, a job). The key under the name is what the engine looks up; a task you add is kept but only counted once the engine knows its key.' },
  'hauling.max_kg_per_person': { label: 'Carried per person', unit: 'kg', help: 'Heaviest pack ÷ this' },
  'mobdemob.vehicle_ownership_per_day': { label: 'Vehicle ownership', unit: '₱ a day' },
  'mobdemob.running_cost_per_km': { label: 'Running cost', unit: '₱ per km' },
  'mobdemob.base_to_site_km': { label: 'Base to site', unit: 'km', help: 'To the reference site' },
  'mobdemob.toll_per_round_trip': { label: 'Toll', unit: '₱', help: 'Per round trip' },
  'mobdemob.one_way_travel_hours': { label: 'Travel, one way', unit: 'h', help: 'Off the productive day' },
  'mobdemob.packaging_disposal': { label: 'Packaging disposal', unit: '₱ per job' },
  'tools.charge_per_installation_day': { label: 'Tool charge', unit: '₱ a day', help: 'Per installation day' },
  // the truck, handling at base, the route
  'truck.basis': { label: 'Truck', help: 'For your notes; prints nowhere', wide: true },
  'truck.payload_kg': { label: 'Payload', unit: 'kg' },
  'truck.cargo_volume_m3': { label: 'Cargo volume', unit: 'm³' },
  'truck.ownership_per_trip_day': { label: 'Truck ownership', unit: '₱ a day', help: 'Per trip day' },
  'truck.driver_per_trip_day': { label: 'Driver', unit: '₱ a day', help: 'Per trip day' },
  'truck.helper_per_trip_day': { label: 'Helper', unit: '₱ a day', help: 'Per trip day' },
  'truck.diesel_price': { label: 'Diesel', unit: '₱ per liter' },
  'truck.fuel_economy_km_per_l': { label: 'Fuel economy', unit: 'km per liter' },
  'truck.maintenance_per_km': { label: 'Maintenance', unit: '₱ per km' },
  'truck.trip_days_per_run': { label: 'Trip days per run', unit: 'days' },
  'handling.helper_day_rate': { label: 'Helper', unit: '₱ a day' },
  'handling.typical_job_helper_hours': { label: 'Helper hours, typical job', unit: 'h', decimals: 1 },
  'handling.typical_fill': { label: 'Typical fill', unit: '×', about: 'The share of the truck a typical 6 kW job uses; handling at base is charged in that proportion.' },
  'route.stops': { label: 'Stops, in driving order', help: 'First your base, last the job site', about: 'The pickup run visits the suppliers between the base and the site. Adding or removing a stop adds or removes its row and column in the km and toll tables below; the arrows reorder all three together.' },
  'route.km': { label: 'Km between stops', unit: 'km' },
  'route.toll': { label: 'Toll between stops', unit: '₱' },
  'route.base_lat': { label: 'Base latitude', unit: '°', decimals: 4 },
  'route.base_lon': { label: 'Base longitude', unit: '°', decimals: 4 },
  'route.reference_site_km': { label: 'Base to reference site', unit: 'km', help: 'One way', about: 'The route is costed to this reference site; a job adds the extra km its pin is beyond it.' },
  'route.road_factor': { label: 'Road factor', unit: '×', help: 'Straight line × this' },
  // wiring rules
  'wiring.pv_run_m': { label: 'PV run per string', unit: 'm' },
  'wiring.ac_run_m': { label: 'AC run', unit: 'm' },
  'wiring.grounding_run_m': { label: 'Grounding run', unit: 'm' },
  'wiring.conduit_m': { label: 'Conduit', unit: 'm' },
  'wiring.battery_pairs_per_battery': { label: 'Cable pairs per battery', unit: 'pairs' },
  'wiring.dc_drop_limit': { label: 'DC voltage drop limit', unit: '%' },
  'wiring.ac_drop_limit': { label: 'AC voltage drop limit', unit: '%' },
  'wiring.ac_voltage': { label: 'AC voltage', unit: 'V' },
  'wiring.battery_voltage': { label: 'Battery voltage', unit: 'V' },
  'wiring.panel_vmp_v': { label: 'Panel Vmp', unit: 'V' },
  'wiring.copper_resistivity': { label: 'Copper resistivity', unit: 'Ω·mm²/m', decimals: 4, readOnly: true, about: 'A physical constant: the resistance of a copper conductor per metre and per mm² of section. Set by the developer; the voltage drop check uses it.' },
  'wiring.continuous_factor': { label: 'Continuous-current factor', unit: '×', help: '1.25 per the code' },
  'wiring.thhn_ampacity': { label: 'THHN ampacity', unit: 'A', help: 'PEC 60 °C column' },
  'wiring.battery_cable_ampacity': { label: 'Battery cable ampacity', unit: 'A' },
  'wiring.pv_cable_ampacity': { label: 'PV cable ampacity', unit: 'A' },
  'wiring.ac_breaker_sizes_a': { label: 'Standard AC breaker sizes', unit: 'A', help: 'Next size at or above 1.25 × the circuit current', about: 'Each AC circuit gets the next size at or above 1.25 × its current; the conductor is then sized from the breaker.' },
  'wiring.ac_conductors_per_circuit': { label: 'Conductors per AC circuit', unit: 'pcs', help: 'Line and neutral', about: 'Line and neutral (2); the ground is the grounding run. Multiplies the AC run per circuit.' },
  // the items the generator uses: plain names; the key itself is shown in small print under the label
  'roles.rail': { label: 'Mounting rail', help: 'Two lines per row' },
  'roles.rail_length_m': { label: 'Rail length', unit: 'm' },
  'roles.l_foot': { label: 'L-foot (roof attachment)' },
  'roles.l_feet_per_rail': { label: 'L-feet per rail', unit: 'pcs' },
  'roles.end_clamp': { label: 'End clamp', help: 'Four per row' },
  'roles.mid_clamp': { label: 'Mid clamp', help: 'Two per panel gap' },
  'roles.splice': { label: 'Rail splice', help: 'One per rail joint' },
  'roles.pv_cable_red': { label: 'PV cable, red, by size', unit: 'Code' },
  'roles.pv_cable_black': { label: 'PV cable, black, by size', unit: 'Code' },
  'roles.thhn': { label: 'THHN wire, by size', unit: 'Code', help: 'AC circuits and grounding' },
  'roles.battery_cable_pair': { label: 'Battery cable lug pair, by size', unit: 'Code' },
  'roles.mc4_pair': { label: 'MC4 connector pair' },
  'roles.mc4_pairs_per_string': { label: 'MC4 pairs per string', unit: 'pairs' },
  'roles.dc_breaker': { label: 'DC breaker', help: 'One per string' },
  'roles.dc_spd': { label: 'DC surge protector', help: 'One per MPPT in use', about: 'One per MPPT input in use (the MPPT count on the inverter item); one per inverter when the count is not on file.' },
  'roles.battery_breaker_pattern': { label: 'Battery breaker: words in the item name', help: 'Smallest match covering 1.25 × the battery current', about: 'The generator picks the smallest breaker whose name matches and whose amps cover 1.25 × the inverter battery current.', wide: true },
  'roles.battery_breaker_fallback': { label: 'Battery breaker: item when none matches' },
  'roles.ats': { label: 'Transfer switch (ATS)' },
  'roles.ats_amps': { label: 'ATS rating', unit: 'A' },
  'roles.ac_breaker': { label: 'AC breaker', help: 'One per AC circuit', about: 'One per AC circuit, rated at the next standard size above 1.25 × the circuit current (the note on the BOM line says which). When the item is not listed in that size the BOM warns.' },
  'roles.ac_breaker_amps': { label: 'AC breaker rating', unit: 'A' },
  'roles.ac_breakers_per_inverter': { label: 'Inverter-side AC circuits', unit: 'per inverter', help: 'Output to the loads', about: 'The inverter output to the loads (1), each with its breaker, sized on the output current.' },
  'roles.ac_spd': { label: 'AC surge protector' },
  'roles.ac_spds_per_inverter': { label: 'AC surge protectors', unit: 'per board', help: 'One Type 2 a board' },
  'roles.enclosure': { label: 'Enclosure', help: 'One per inverter', about: 'AC and DC protection together.' },
  'roles.enclosures': { label: 'Enclosures', unit: 'per inverter' },
  'roles.cable_tray': { label: 'Cable tray' },
  'roles.cable_trays': { label: 'Cable trays', unit: 'per job' },
  'roles.conduit': { label: 'Conduit' },
  'roles.ground_rod': { label: 'Ground rod' },
  'roles.ground_rods': { label: 'Ground rods', unit: 'per job' },
  'roles.earth_lug': { label: 'Earth lug' },
  'roles.earth_lugs': { label: 'Earth lugs', unit: 'per job' },
  'roles.sealant': { label: 'Sealant' },
  'roles.sealants': { label: 'Sealant tubes', unit: 'per job' },
  'roles.max_panels_per_string': { label: 'Max panels per string', unit: 'panels' },
  'roles.default_inverter_code_grid': { label: 'Default inverter for net metering', help: 'Grid type only', about: 'Must be marked grid-interactive on the Materials page (the electric company asks for the anti-islanding listing). Set at import to the first grid-interactive hybrid in the workbook; blank = the cheapest grid-interactive unit that fits. Parallel units as needed.' },
  'roles.default_inverter_code_offgrid': { label: 'Default inverter for off-grid', help: 'Blank = cheapest', about: 'Felicity 6 kW eco-hybrid by default; blank = the cheapest hybrid that fits. Parallel units as needed.' },
  'roles.inverter_exclude_words': { label: 'Inverter names to skip', help: 'Never picked as the inverter', about: 'Items whose name carries one of these words are never picked as the inverter.' },
  'roles.battery_exclude_words': { label: 'Battery names to skip', help: 'Never picked as the battery', about: 'Items whose name carries one of these words are never picked as the battery.' },
  'roles.inverter_parallel_tolerance_pct': { label: 'Inverter overshoot tolerance', unit: '%', decimals: 1, help: '0 = never tolerate', about: "When the sizing asks for a little more than one unit gives (within this share), one unit is kept with a warning instead of two in parallel. Above it the cheapest single unit that fits is used (the default's brand on ties), then parallel units. 0 = never tolerate; verify the unit's overload rating on the datasheet." },
  'roles.ac_grid_breakers_per_inverter': { label: 'Grid-side AC circuits', unit: 'per inverter', help: 'Feed and bypass', about: "The grid feed to the inverter's AC input and the maintenance bypass (2), each with its breaker, sized on the inverter's AC input (pass-through) rating when the item carries it, else on its output." },
  'roles.ac_disconnect': { label: 'AC disconnect (DU)', help: 'At the service', about: "The visible, lockable AC disconnect for the electric company at the service; rated at least the grid-side breaker. Verify the DU's requirement." },
  'roles.ac_disconnects': { label: 'AC disconnects', unit: 'per job' },
  'roles.placard': { label: 'Placards and labels', help: 'Blank = no price', about: 'PV system labels and placards at the service, the disconnect, the inverter and the DC box; verify what the LGU and the DU ask for. Blank = no item yet: the BOM carries the line without a price and warns.' },
  'roles.placard_sets': { label: 'Placard sets', unit: 'per job' },
  'roles.monitoring': { label: 'Monitoring dongle', help: 'One per inverter', about: "One per inverter; it must match the inverter's brand. Blank = no item yet: the BOM carries the line without a price and warns." },
  'roles.export_limiter': { label: 'Export limiter', help: 'Net metering only', about: "Priced on net-metering jobs when set: the export limit between switch-on and the two-way meter (verify the DU's rule). Blank = none priced, with a warning on net-metering jobs." },
  'roles.array_bonding_wire': { label: 'Array bonding conductor', help: 'Along the rails', about: 'The equipment grounding conductor along the array: the rail-line length of every row plus the jumpers. Bare copper where the LGU asks; verify the gauge with the PEE.' },
  'roles.bonding_extra_m_per_row': { label: 'Bonding jumpers per row', unit: 'm', help: 'Jumpers per row', about: "Added to each row's rail-line length for the jumpers between the two rail lines and to the next row." },
  'roles.bonding_lugs_per_panel': { label: 'Bonding lugs', unit: 'per panel', help: '0 if the clamps bond', about: 'Panel frame to rail, unless the clamps are listed as bonding clamps (then 0). Added to the earth-lug line.' },
  'roles.bonding_lugs_per_rail_line': { label: 'Bonding lugs', unit: 'per rail line', help: 'Two lines per row', about: 'Each rail line to the grounding conductor; two lines per row. Added to the earth-lug line.' },
  'roles.l_foot_fastener': { label: 'L-foot fastener', help: 'Blank = no price', about: 'The screws or bolts that fix each L-foot into the purlin; BC-MNT-006 lists none. Blank = no item yet: the BOM carries the line without a price and warns.' },
  'roles.fasteners_per_l_foot': { label: 'Fasteners', unit: 'per L-foot', help: 'Per the rail manual' },
  // the program of works
  'program.depart_time': { label: 'Leave base at' },
  'program.lunch_start': { label: 'Lunch at' },
  'program.lunch_minutes': { label: 'Lunch break', unit: 'minutes' },
  'program.travel_speed_kmh': { label: 'Travel speed', unit: 'km/h', decimals: 0 },
  'program.installation_outage_hours': { label: 'Power off on installation day', unit: 'h', decimals: 1, help: '0 = not on the proposal', about: "Hours the customer's power is off on installation day while the inverter is connected to the panel board; fill in from your crew's practice. Printed on the proposal; 0 (blank) = not stated." },
  'program.permit_prep_days': { label: 'Plans and PEE seal', unit: 'days' },
  'program.permit_approval_days': { label: 'Electrical permit approval', unit: 'days', help: 'Assumption', about: 'Until you have data.' },
  'program.cfei_days': { label: 'Final inspection certificate', unit: 'days', help: 'After installation' },
  'program.netmeter_application_days': { label: 'Net metering application and agreement', unit: 'days', help: 'Assumption' },
  'program.netmeter_meter_days': { label: 'Inspection and net metering meter', unit: 'days', help: 'After switch-on' },
  'program.sourcing_days_before_install': { label: 'Pickup run before installation', unit: 'days' },
  'program.install_gap_after_permit_days': { label: 'Installation after the permit', unit: 'days' },
  'program.commissioning_offset_days': { label: 'Switch-on after the last installation day', unit: 'days' },
  'program.min_task_minutes': { label: 'Minimum task durations', unit: 'minutes', help: 'Floors for the hour-by-hour plan', about: 'A floor for the hour-by-hour plan (commissioning, battery, inverter), in minutes; the labor price is not changed. When the floors push the plan past the priced days the program warns. The late finish allowance is how long the crew may stay past the usual end of the last priced day to finish the same day (default 120); only beyond this does the plan add a day.' },
  'program.late_finish_max_minutes': { label: 'Late finish allowance', unit: 'minutes', help: 'Before the plan adds a day' },
  'program.payment': { label: 'Payment terms', help: 'What a proposal starts from' },
  'program.labour_paid_days_after_job': { label: 'Labor paid after the job', unit: 'days' },
  'program.commission_paid_days_after_job': { label: 'Commission paid after the job', unit: 'days' },
  'program.vat_remit_days_after_completion': { label: 'VAT remitted after completion', unit: 'days' },
  // customer savings
  'economics.tariff_php_per_kwh': { label: 'Tariff without a bill', unit: '₱ per kWh', help: 'When the audit has no bill' },
  'economics.export_rate_php_per_kwh': { label: 'Net metering credit', unit: '₱ per kWh', help: "The DU's generation rate", about: "The electric company's generation rate, lower than the tariff." },
  'economics.tariff_escalation': { label: 'Electricity price rise', unit: '% a year' },
  'economics.degradation': { label: 'Panel output loss', unit: '% a year' },
  'economics.analysis_years': { label: 'Analysis period', unit: 'years' },
  'economics.discount_rate': { label: 'Discount rate', unit: '%' },
  'economics.battery_life_years_override': { label: 'Battery life', unit: 'years', help: '0 = the battery warranty', about: '0 = the battery warranty years in the company profile (Settings › Company), 5 today: the battery datasheets give 5 years, though the supplier price list says 10 for the Felicity FLB line (verify). The savings view replaces the battery at this interval, at the customer price including VAT.' },
  'economics.inverter_life_years': { label: 'Inverter life', unit: 'years', help: 'Not the warranty', about: 'Not the warranty (5 years from the maker, in the company profile): the years before the savings view replaces the inverter, at the customer price including VAT. 12 is the figure carried so far; verify against the datasheet.' },
  'economics.replacement_labor_php': { label: 'Labor per replacement', unit: '₱', help: 'With VAT; 0 = none', about: 'Added to each battery or inverter replacement in the savings view; 0 = none. Verify against your crew rates.' },
  'economics.om_share_per_year': { label: 'Upkeep', unit: '% a year', help: 'Of the contract price' },
  'economics.co2_kg_per_kwh': { label: 'Grid emission factor', unit: 'kg CO₂/kWh' },
  // losses after the panels and sizing
  'system_losses.inverter': { label: 'Inverter', unit: '% kept', help: 'Datasheet efficiency' },
  'system_losses.wiring': { label: 'Wiring', unit: '% kept', help: 'Cables and terminations' },
  'system_losses.soiling': { label: 'Soiling', unit: '% kept', help: 'Dust between rains', about: 'Dust and dirt on the panels between rains; verify locally (a rice-field roof collects more in the dry season).' },
  'system_losses.other': { label: 'Other', unit: '% kept', help: 'Mismatch, availability', about: 'Module mismatch, availability and anything else after the panels. The four multiply: the array is sized on energy at the meter and the customer documents print that figure.' },
  'sizing.days_of_autonomy': { label: 'Days of autonomy', unit: 'evenings', decimals: 1, help: 'Evenings without sun', about: 'The evenings the battery must carry without sun; your choice. 1 = the night deficit of the worst typical day (the rule until now), 2 = twice that. The balance over a real year of weather then reports how often it still runs out.' },
  // the website estimate
  'quick.enabled': { label: 'Estimate page' },
  'quick.panel_code': { label: 'Panel used', help: 'A materials-list code' },
  'quick.k_site': { label: 'Typical site factor', unit: '%' },
  'quick.tilt_deg': { label: 'Typical roof pitch', unit: '°', decimals: 0 },
  'quick.azimuth_deg': { label: 'Typical roof facing', unit: '°', decimals: 0 },
  'quick.max_panels': { label: 'Most panels an estimate may use', unit: 'panels' },
  'quick.panels_per_row': { label: 'Panels per row', unit: 'panels' },
  'quick.peak_factor': { label: 'Peak over the busiest hour', unit: '×' },
  'quick.price_round_to': { label: 'Round the price up to', unit: '₱' },
  'quick.max_requests_per_hour': { label: 'Estimates per browser', unit: 'per hour' },
  // whole sections that are one value
  'company_base.value': { label: 'Base name', help: 'Where the route starts', wide: true },
  'categories.value': { label: 'Markup and wastage by category' },
}

/** Sections whose keys are catalogue roles: the key is shown in small print under the plain name. */
export const KEYED_SECTIONS = new Set(['roles'])
export const SECTION_NOTES: Record<string, string> = {
  roles: 'Each role names the materials-list code the generator uses for that item; change a code to swap the item. The size tables map a wire size in mm² to its code. Counts and patterns are the rules beside them.',
  categories: 'The markup tier and the wastage allowance for every item in a category, by the category name on the Materials page. A category that is not listed takes 30% markup and no wastage.',
  system_losses: 'The share of energy that gets through each stage after the panels; the four multiply.',
}
/** A section printed as several blocks with their own headings, each holding the keys named; the rest follow unheaded. */
export const SUBBLOCKS: Record<string, { title: string; keys: string[]; headed?: boolean }[]> = {
  program: [
    { title: 'Site day', keys: ['depart_time', 'lunch_start', 'lunch_minutes', 'travel_speed_kmh', 'installation_outage_hours'] },
    { title: 'Permits and durations', keys: ['permit_prep_days', 'permit_approval_days', 'cfei_days', 'netmeter_application_days', 'netmeter_meter_days', 'sourcing_days_before_install', 'install_gap_after_permit_days', 'commissioning_offset_days'] },
    // a block that is one table carries one heading: its own label, printed as the heading (with its "?")
    { title: 'Minimum task durations', keys: ['min_task_minutes'], headed: true },
    { title: 'Payment terms', keys: ['payment'], headed: true },
    { title: 'Cash timing', keys: ['labour_paid_days_after_job', 'commission_paid_days_after_job', 'vat_remit_days_after_completion'] },
  ],
}
/** Keys whose block label is printed as the block's heading. */
export const HEADED = new Set(Object.entries(SUBBLOCKS).flatMap(([sec, blocks]) => blocks.filter((b) => b.headed).flatMap((b) => b.keys.map((k) => `${sec}.${k}`))))
export const TASK_LABELS: Record<string, string> = { commissioning: 'Commissioning', battery: 'Battery', inverter: 'Inverter' }

/** Decimals for a unit when the META entry names none: money whole pesos, rates per kWh or km 2, hours 2, counts 0. */
export function unitDecimals(unit: string | undefined, pct: boolean): number {
  if (pct) return 1
  if (!unit) return 2
  if (/kWh|per km|per liter/.test(unit) && unit.startsWith('₱')) return 2
  if (unit.startsWith('₱')) return 0
  if (unit === '%' || unit.startsWith('% ')) return 1
  if (unit === 'h' || unit.startsWith('h ')) return 2
  if (/^(days|pcs|panels|pairs|per |minutes|years|evenings|strings|payments|rows|A$|W$|km\/h)/.test(unit)) return 0
  if (unit === 'm') return 2
  if (unit === 'km' || unit === 'km per liter' || unit === 'kg' || unit === 'V' || unit === 'kW' || unit === 'kWh') return 1
  if (unit === 'm³' || unit === '×' || unit === 'kWp' || unit.startsWith('kg CO')) return 2
  if (unit === '°') return 4
  return 2
}
export const decimalsFor = (meta: SettingMeta | undefined, pct: boolean) => meta?.decimals ?? unitDecimals(meta?.unit, pct)

export function titleCase(k: string) {
  return k.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
}
export const isMatrix = (v: unknown): v is number[][] => Array.isArray(v) && v.length > 0 && v.every((r) => Array.isArray(r) && r.every((x) => typeof x === 'number'))
export const isPrimList = (v: unknown): v is (string | number)[] => Array.isArray(v) && v.every((x) => typeof x === 'string' || typeof x === 'number')
export const isPrimDict = (v: unknown): v is Record<string, string | number> => !!v && typeof v === 'object' && !Array.isArray(v) && Object.values(v as object).every((x) => typeof x === 'string' || typeof x === 'number')
export interface CategoryRule {
  name: string
  markup_tier: number
  wastage: number
}
export const isCategoryList = (v: unknown): v is CategoryRule[] => Array.isArray(v) && v.every((r) => r && typeof r === 'object' && typeof (r as CategoryRule).name === 'string' && typeof (r as CategoryRule).markup_tier === 'number')
export interface GroundTask {
  key: string
  label: string
  mounting_weight: number
  wiring_weight: number
  unit: string
}
export const isTaskList = (v: unknown): v is GroundTask[] => Array.isArray(v) && v.every((r) => r && typeof r === 'object' && typeof (r as GroundTask).key === 'string' && typeof (r as GroundTask).mounting_weight === 'number')
export const pctIn = (v: number) => Math.round(v * 10000) / 100
export const fieldId = (section: string, key: string) => `cfg-${section}-${key}`.replace(/[^A-Za-z0-9_-]/g, '-')
export const labelOf = (section: string, key: string) => META[`${section}.${key}`]?.label ?? titleCase(key)
export const slug = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'task'
export const numericKey = (k: string) => /^[\d.]+$/.test(k)
export const sortedSizes = (keys: string[]) => (keys.every(numericKey) ? [...keys].sort((a, b) => parseFloat(a) - parseFloat(b)) : keys)

export interface Draft {
  cfg: PricingConfig | null
  saved: PricingConfig | null
  error: string | null
  msg: string | null
  busy: boolean
  dirtySections: string[]
  dirty: boolean
  undo: { left: number } | null
  setField: (section: string, key: string, value: unknown) => void
  setSection: (section: string, value: unknown) => void
  save: () => Promise<boolean>
  discard: () => void
  reset: () => Promise<void>
  undoReset: () => Promise<void>
}
export const DraftCtx = createContext<Draft | null>(null)
export const UNDO_SECONDS = 10

export function usePricingDraft(): Draft {
  const d = useContext(DraftCtx)
  if (!d) throw new Error('usePricingDraft needs a PricingDraftProvider')
  return d
}

/** The entry a pricing section is shown on (the website estimate's section lives on the Website page). */
export function entryOfSection(sec: string): SettingsEntry {
  if (sec === WEBSITE_SECTION) return SETTINGS_ENTRIES.find((e) => e.id === 'website')!
  return SETTINGS_ENTRIES.find((e) => e.sections?.includes(sec)) ?? SETTINGS_ENTRIES.find((e) => e.id === 'system')!
}
/** The pages (by entry id) that have unsaved pricing edits. */
export function dirtyEntryIds(dirtySections: string[]): Set<string> {
  return new Set(dirtySections.map((s) => entryOfSection(s).id))
}

/* ---------- find a setting across the pages ---------- */

export interface FindRow {
  /** The element to scroll to (its id). */
  id: string
  /** The find parameter that names it ("job.vat"). */
  find: string
  label: string
  /** "Materials and markup › Fees, markups and VAT" */
  where: string
  route: string
  hay: string
}

export function blockTitleOf(sec: string, key: string): string | undefined {
  return SUBBLOCKS[sec]?.find((b) => b.keys.includes(key))?.title
}

/** Every setting on the pricing pages (and the one-value sections) as a row the menu's search can list. */
export function settingsIndex(cfg: PricingConfig | null): FindRow[] {
  if (!cfg) return []
  const rows: FindRow[] = []
  for (const sec of Object.keys(cfg)) {
    if (SKIP.has(sec)) continue
    const entry = entryOfSection(sec)
    const v = cfg[sec]
    const secLabel = SECTION_LABELS[sec] ?? titleCase(sec)
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      for (const key of Object.keys(v as object)) {
        if (HIDDEN.has(`${sec}.${key}`)) continue
        const meta = META[`${sec}.${key}`]
        const label = labelOf(sec, key)
        const block = blockTitleOf(sec, key)
        const where = `${entry.label} › ${block ?? secLabel}`
        rows.push({ id: fieldId(sec, key), find: `${sec}.${key}`, label, where, route: entry.route, hay: `${label} ${key} ${meta?.help ?? ''} ${meta?.about ?? ''} ${secLabel} ${entry.label}`.toLowerCase() })
      }
    } else {
      const label = META[`${sec}.value`]?.label ?? secLabel
      rows.push({ id: fieldId(sec, 'value'), find: `${sec}.value`, label, where: entry.label, route: entry.route, hay: `${label} ${sec} ${secLabel} ${entry.label}`.toLowerCase() })
    }
  }
  return rows
}

export function findSettings(rows: FindRow[], needle: string): FindRow[] {
  const q = needle.trim().toLowerCase()
  if (!q) return []
  const words = q.split(/\s+/)
  return rows.filter((r) => words.every((w) => r.hay.includes(w)))
}

/** On a page opened with ?find=section.key (or a word): open the fold it sits in, scroll it under the top and ring it. */
export function useFindTarget(ready: boolean, rowsOnPage: FindRow[]) {
  const [params] = useSearchParams()
  const find = params.get('find')
  useEffect(() => {
    if (!ready || !find) return
    const row = rowsOnPage.find((r) => r.find === find) ?? findSettings(rowsOnPage, find)[0]
    const id = row?.id ?? (document.getElementById(find) ? find : null)
    if (!id) return
    const t = window.setTimeout(() => {
      const el = document.getElementById(id)
      if (!el) return
      const target = (el.closest('.field') as HTMLElement | null) ?? el
      const fold = target.closest('details')
      if (fold && !fold.open) fold.open = true
      target.scrollIntoView({ block: 'center' })
      target.classList.add('ring')
      window.setTimeout(() => target.classList.remove('ring'), 2200)
    }, 60)
    return () => window.clearTimeout(t)
  }, [ready, find, rowsOnPage])
}

