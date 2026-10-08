export type FaceShape = 'rect' | 'hip' | 'tri'
export type WallEdge = 'eave' | 'ridge' | 'left' | 'right'

export interface WallObstacle {
  id: string
  edge: WallEdge
  height_m: number
  gap_m: number
}

export interface ShadeObstacle {
  id: string
  label: string
  direction_deg: number
  elevation_deg: number
  width_deg: number
  share: number
}

export interface RoofFace {
  id: string
  name: string
  shape: FaceShape
  length_m: number
  width_m: number
  ridge_m: number | null
  tilt_deg: number
  azimuth_deg: number
  panels_left_out: number
  panel_count_override: number | null
  walls: WallObstacle[]
  obstacles: ShadeObstacle[]
}

export interface ShadeFace {
  walls: { id: string; edge: WallEdge; side_deg: number; height_m: number; gap_m: number; strip_m: number | null; strip_all_m: number | null; whole_face: boolean }[]
  obstacles: { id: string; label: string; direction_deg: number; elevation_deg: number; width_deg: number; cls: 'clear' | 'small' | 'main'; text: string }[]
  shade_loss_pct?: number
}

export interface CandidatePanel {
  id: string
  name: string
  watt_peak: number
  length_m: number
  width_m: number
  code?: string | null
}

export interface Reading {
  irradiance_wm2: number
  power_w: number
  module_temp_c: number | null
}

export interface ReadingSet {
  id: string
  face_id: string | null
  label: string
  measured_at: string | null
  ambient_temp_c: number | null
  sky_condition: string
  readings: Reading[]
}

export interface UsageWindow {
  start: string
  end: string
  days: number[]
  months: number[]
}

export type ApplianceStatus = 'existing' | 'future' | 'retiring'

export interface ApplianceEntry {
  id: string
  name: string
  brand: string
  model: string
  category: string
  input_power_w: number
  quantity: number
  duty_factor: number | null
  status: ApplianceStatus
  windows: UsageWindow[]
  notes: string
}

export interface BillEntry {
  id: string
  billing_month: string
  kwh: number
  days: number | null
  amount_php: number | null
  utility: string
}

export type SystemKind = 'off_grid' | 'net_metering' | 'combination'

export interface SystemSettings {
  kind: SystemKind
  offgrid_pv_margin: number
  inverter_sizes_kw: number[]
  inverter_surge_factor: number
  pv_ratio_max: number
  battery_dod: number
  battery_efficiency: number
}

export interface EnergyAudit {
  appliances: ApplianceEntry[]
  bills: BillEntry[]
  reconcile: boolean
  system: SystemSettings
}

export interface ApplianceCategory {
  id: string
  label: string
  duty: number
  uncertain: boolean
  w_min: number | null
  w_max: number | null
  note: string
}

export interface CatalogItem {
  id: number
  name: string
  brand: string
  model: string
  category: string
  input_power_w: number
  use_count: number
}

export interface AssessmentDoc {
  customer_name: string
  address: string
  notes: string
  lat: number | null
  lon: number | null
  faces: RoofFace[]
  panels: CandidatePanel[]
  selected_panel_id: string | null
  reading_sets: ReadingSet[]
  test_panel_rating_w: number
  test_panel_calibration: number
  setback_m: number
  gap_m: number
  /** Printed on the roof check card; blank means the card's own default line. */
  card_next_step: string
  audit: EnergyAudit
  pricing: PricingJob
  program: ProgramJob
  economics: EconomicsJob
}

export interface EconomicsJob {
  tariff_php_per_kwh: number | null
  export_rate_php_per_kwh: number | null
  tariff_escalation: number | null
  degradation: number | null
  analysis_years: number | null
  discount_rate: number | null
  battery_life_years: number | null
  inverter_life_years: number | null
  om_per_year: number | null
}

export function emptyEconomicsJob(): EconomicsJob {
  return { tariff_php_per_kwh: null, export_rate_php_per_kwh: null, tariff_escalation: null, degradation: null, analysis_years: null, discount_rate: null, battery_life_years: null, inverter_life_years: null, om_per_year: null }
}

export interface EconomicsBlock {
  available: boolean
  reason?: string
  warnings: Warning[]
  assumptions?: {
    tariff_php_per_kwh: number; tariff_source: string; export_rate_php_per_kwh: number; tariff_escalation: number; degradation: number; analysis_years: number
    discount_rate: number; battery_life_years: number; inverter_life_years: number; om_per_year: number; battery_replacement_cost: number; inverter_replacement_cost: number; co2_kg_per_kwh: number
  }
  contract?: number
  kind?: SystemKind
  monthly?: { month: number; consumption_kwh: number; solar_used_kwh: number; export_kwh: number; import_kwh: number; unserved_kwh: number; bill_before: number; bill_after: number; savings: number }[]
  bill_today_monthly?: number
  bill_today_kwh?: number
  includes_future_loads?: boolean
  bill_before_monthly?: number
  bill_after_monthly?: number
  savings_monthly?: number
  year1?: { savings: number; solar_used_kwh: number; export_kwh: number; export_credit: number; import_kwh: number; production_kwh: number }
  years?: { year: number; production_kwh: number; savings: number; costs: number; net: number; cumulative: number; discounted_cumulative: number; note: string }[]
  payback_years?: number | null
  discounted_payback_years?: number | null
  npv?: number
  irr?: number | null
  lifetime_savings?: number
  lifetime_costs?: number
  lifetime_net?: number
  lifetime_production_kwh?: number
  lcoe_php_per_kwh?: number | null
  co2_t_per_year?: number
}

export type JobStage = 'lead' | 'contacted' | 'assessed' | 'quoted' | 'signed' | 'sourcing' | 'installing' | 'commissioned' | 'net_metering' | 'closed'
export const JOB_STAGES: { id: JobStage; label: string }[] = [
  { id: 'lead', label: 'Lead' }, { id: 'contacted', label: 'Contacted' }, { id: 'assessed', label: 'Assessed' }, { id: 'quoted', label: 'Quoted' }, { id: 'signed', label: 'Signed' }, { id: 'sourcing', label: 'Sourcing' },
  { id: 'installing', label: 'Installing' }, { id: 'commissioned', label: 'Commissioned' }, { id: 'net_metering', label: 'Net metering' }, { id: 'closed', label: 'Closed' },
]

export interface PaymentMilestone {
  key: string
  label: string
  share: number
  event: string
  offset_days: number
}

export interface PaymentPlan {
  milestones: PaymentMilestone[]
  installments: number
  installment_share: number
  installment_interval_days: number
  installment_start_event: string
  installment_first_offset_days: number
}

export interface ProgramJob {
  stage: JobStage
  signing_date: string | null
  install_date: string | null
  depart_time: string | null
  lunch_start: string | null
  lunch_minutes: number | null
  permit_approval_days: number | null
  netmeter_application_days: number | null
  netmeter_meter_days: number | null
  payment: PaymentPlan | null
}

export function emptyProgramJob(): ProgramJob {
  return {
    stage: 'assessed', signing_date: null, install_date: null, depart_time: null, lunch_start: null, lunch_minutes: null,
    permit_approval_days: null, netmeter_application_days: null, netmeter_meter_days: null, payment: null,
  }
}

export interface ProgramEvent {
  key: string
  label: string
  date: string
  end: string | null
  kind: 'milestone' | 'task' | 'payment_in'
  customer: boolean
  amount?: number
}

export interface ProgramSegment {
  day: number
  stream: 'roof' | 'ground' | 'all'
  task: string
  start: number
  end: number
  crew: number
  start_time: string
  end_time: string
}

export interface CashFlow {
  date: string
  label: string
  inflow: number
  outflow: number
  kind: 'in' | 'out'
  key: string
  balance: number
}

export interface ProgramBlock {
  available: boolean
  reason?: string
  warnings: Warning[]
  signing_date?: string
  install_start?: string
  install_end?: string
  completion?: string
  net_metering?: boolean
  events?: ProgramEvent[]
  install?: {
    days: number
    paid_days: number
    crew: { persons: number; roof_pairs: number; roof_persons: number; ground_persons: number; description: string }
    finish_time: string
    segments: ProgramSegment[]
    hourly: { day: number; rows: { time: string; roof: string; ground: string }[] }[]
    frame: Record<string, string | number>
    warnings: Warning[]
    man_hours: { roof: number; ground: number; handoff: number; total: number }
  }
  payments?: { key: string; label: string; date: string; amount: number; share: number }[]
  payment_plan?: PaymentPlan
  outflows?: { key: string; label: string; date: string; amount: number }[]
  cashflow?: {
    flows: CashFlow[]
    weekly: { week: string; inflow: number; outflow: number; balance: number }[]
    total_in: number
    total_out: number
    cash_margin: number
    lowest_balance: number
    lowest_balance_date: string
    noncash: { handling_wastage_storage: number; truck_ownership_maintenance: number; tools: number }
    contract: number
  }
  customer_schedule?: { label: string; date: string; end: string | null }[]
  assumptions?: string[]
}

export interface BomEdit {
  code: string
  qty: number
  note: string
}

export interface PricingJob {
  inverter_code: string | null
  battery_code: string | null
  strings_override: number | null
  max_panels_per_string: number | null
  roof_factor: number | null
  roof_closed_days: number | null
  max_days: number | null
  max_pairs: number | null
  owner_days: number | null
  extra_km: number | null
  extra_toll: number | null
  pv_run_m: number | null
  ac_run_m: number | null
  grounding_run_m: number | null
  conduit_m: number | null
  bom_edits: BomEdit[]
  bom_extra: BomEdit[]
}

export function emptyPricingJob(): PricingJob {
  return {
    inverter_code: null, battery_code: null, strings_override: null, max_panels_per_string: null, roof_factor: null, roof_closed_days: null,
    max_days: null, max_pairs: null, owner_days: null, extra_km: null, extra_toll: null, pv_run_m: null, ac_run_m: null, grounding_run_m: null,
    conduit_m: null, bom_edits: [], bom_extra: [],
  }
}

export interface MaterialItem {
  code: string
  category: string
  supplier: string
  name: string
  spec: string
  unit: string
  sold_as: string
  list_price: number
  rating: number | null
  rating_unit: string
  weight_kg: number
  volume_m3: number
  weight_source: string
  storage: number
  price_list_date: string
  remarks: string
  panel_length_m: number | null
  panel_width_m: number | null
  active: boolean
  updated_at?: string
}

export interface MaterialSupplier {
  name: string
  pickup_address: string
  dealer_discount: number
  payment_fee: number
  delivers_free: boolean
  price_list_date: string
  prices_note: string
  warranty: string
  remarks: string
}

export interface PricingStatus {
  item_count: number
  supplier_count: number
  imported_from: string | null
  imported_at: string | null
  seed_available: boolean
}

export interface ImportReport {
  added: number
  updated: number
  suppliers: number
  warnings: string[]
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type PricingConfig = Record<string, any>

export interface PricedLine {
  code: string
  qty: number
  role: string
  note: string
  found: boolean
  name: string
  category: string
  supplier: string
  unit: string
  rating: number | null
  rating_unit: string
  landed_unit: number
  markup_tier: number
  landed: number
  markup: number
  selling: number
  truck_share: number
  weight_kg: number
}

export interface BuildUpLine {
  key: string
  label: string
  direct: number
  tier: number
  markup: number
  selling: number
  pass_through: boolean
}

export interface PricingBlock {
  available: boolean
  reason?: string
  warnings: Warning[]
  panel?: { code: string; name: string; watt_peak: number }
  lines?: PricedLine[]
  generated_bom?: { code: string; qty: number; role: string; note: string }[]
  missing_codes?: string[]
  takeoff?: Record<string, number>
  freight?: { stops_on_run: string[]; legs: { from: string; to: string; km: number; toll: number }[]; loop_km: number; toll: number; run_cost: number; truck_share: number; trips: number; freight: number }
  labor?: Record<string, number | string | boolean | unknown[]>
  build_up?: BuildUpLine[]
  totals?: { direct: number; markup: number; markup_over_direct: number; selling: number; commission: number; contract_ex_vat: number; vat: number; contract: number; contract_rounded: number; ocm: number; op: number; kwp: number; price_per_wp: number | null; materials_landed: number; materials_selling: number }
  customer?: { sections: { key: string; label: string; amount: number; items: { key: string; name: string; qty: number; unit: string; amount: number; main?: boolean }[] }[]; total: number; subtotal_ex_vat: number; vat: number }
  job_inputs?: Record<string, number | boolean>
  choices?: {
    strings: number; panels_per_string: number; string_current_a: number; string_voltage_v: number; pv_gauge: string; pv_drop: number
    ac_current_a: number; ac_gauge: string; ac_drop: number; inverter_code: string | null; inverter_units?: number; battery_code: string | null; battery_units: number
    rows: { panels: number; length_m: number }[]
    inverter_options?: { code: string; name: string; rating_kw: number; supplier: string; landed: number }[]
    battery_options?: { code: string; name: string; rating_kwh: number; units: number; total_kwh: number; supplier: string; landed: number }[]
  }
  pin_distance?: { straight_km: number; road_km: number; reference_site_km: number; extra_km: number } | null
  quotation_validity_days?: number
}

export interface AssessmentSummary {
  id: number
  created_at: string
  updated_at: string
  customer_name: string
  address: string
  has_results: boolean
  results_stale: boolean
  stage: JobStage
  contract_php: number | null
  system_kwp: number | null
  annual_kwh: number | null
  panel_count: number | null
  kind: string | null
  lead_contact: string | null
  lead_town: string | null
  lead_source: string | null
  lead_estimate: { goal: string; panels: number; kwp: number; battery_kwh: number; price: number; bill_before_monthly: number | null; bill_after_monthly: number | null; payback_years: number | null } | null
}

export interface Funnel {
  days: number
  estimates: number
  leads: number
  visits: number
  proposals: number
  signed: number
  estimates_by_source: Record<string, number>
}

export interface Warning {
  code: string
  message: string
  /** Set on warnings about one roof face (face_no_fit), so the face card can show them inline. */
  face_id?: string | null
}

export interface LayoutOption {
  orientation: string
  along_length: number
  along_width: number
  count: number
  rows: number[]
}

export interface LayoutResult {
  usable_length_m: number
  usable_width_m: number
  options: LayoutOption[]
  best: LayoutOption
  count: number
  override_applied: boolean
  shape: FaceShape
  gross: number
  left_out: number
  cuts: { eave: number; ridge: number; left: number; right: number }
}

export interface PanelResult {
  panel: CandidatePanel
  faces: Record<string, LayoutResult>
  total_count: number
  system_kwp: number
  best: boolean
}

export interface ReadingSetResult {
  label: string
  face_id: string | null
  k_raw_values: number[]
  k_raw: number
  eta_rel_values: number[]
  k_site_values: number[]
  k_site: number
  avg_irradiance_wm2: number
  irradiance_spread_fraction: number
  avg_module_temp_c: number
  module_temp_source: string
  ambient_temp_c: number | null
  ambient_source: string
  rise_per_kw_values: number[]
  rise_per_kw: number | null
  rise_is_plausible: boolean
  warnings: Warning[]
  low_confidence: boolean
  valid: boolean
}

export interface FaceSimulation {
  face_id: string
  name: string
  tilt_deg: number
  azimuth_deg: number
  panel_count: number
  monthly_kwh: number[]
  annual_kwh: number
  monthly_poa_kwh_m2: number[]
  psh_per_day: number[]
  annual_poa_kwh_m2: number
  avg_psh_per_day: number
  specific_yield_kwh_per_kwp: number
}

export interface SimulationResult {
  faces: FaceSimulation[]
  monthly_kwh: number[]
  annual_kwh: number
  avg_monthly_kwh: number
  days_in_month: number[]
  monthly_ghi_kwh_m2: number[]
  ghi_psh_per_day: number[]
  annual_ghi_kwh_m2: number
  total_panels: number
  system_kwp: number
  k_site: number
  thermal: string
}

export interface ApplianceResult {
  id: string
  name: string
  category: string
  category_label: string
  status: ApplianceStatus
  quantity: number
  input_power_w: number
  duty_factor: number
  duty_is_default: boolean
  uncertain: boolean
  hours_per_day: number
  days_per_week: number
  hours_per_use_day: number
  kwh_per_day_audit: number
  kwh_per_day_reconciled: number
  scale: number
  scale_inherited: boolean
  share_pct: number
  warnings: Warning[]
}

export interface AuditBlock {
  appliances: ApplianceResult[]
  daily_kwh_by_month: number[]
  annual_kwh: number
  peak_kw: number
  peak_avg_kw: number
  peak_detail: { month: number; weekday: string; hour: number; label: string; kw: number; contributors: { name: string; watts: number }[] }
  hour_table: { hour: number; label: string; total_w: number; appliances: { name: string; watts: number }[] }[]
  largest_motor_kw: number
  largest_motor_multiplier: number
  audit_vs_bill: {
    billed_kwh: number
    audit_kwh: number
    gap_pct: number
    uncertain_kwh: number
    fixed_kwh: number
    scale_uncertain: number
    scale_all: number
    reconciled: boolean
    bills: { billing_month: string; kwh: number; days: number; audit_kwh: number; reconciled_kwh: number }[]
  } | null
  future_daily_kwh: number
  load_profile_kw: number[][]
  load_profile_unreconciled_kw: number[][]
  weekday_profiles_kw: Record<string, number[][]>
  warnings: Warning[]
}

export interface DayProfile {
  load: number[]
  production: number[]
  direct: number[]
  charge: number[]
  discharge: number[]
  soc: number[]
  export: number[]
  curtailed: number[]
  imported: number[]
}

export interface SizingBlock {
  kind: SystemKind
  annual_consumption_kwh: number
  annual_yield_kwh_per_kwp: number
  target_kwp: number
  target_panels: number
  roof_max_panels: number
  roof_max_kwp: number
  roof_limited: boolean
  panels: number
  kwp: number
  annual_production_kwh: number
  coverage_pct: number
  self_consumption_pct: number
  annual_direct_kwh: number
  annual_battery_kwh: number
  annual_export_kwh: number
  annual_curtailed_kwh: number
  annual_import_kwh: number
  annual_unserved_kwh: number
  net_annual_kwh: number
  offgrid: { pv_margin: number } | null
  battery: { usable_kwh: number; installed_kwh: number; power_kw: number; depth_of_discharge: number; round_trip_efficiency: number }
  inverter: { size_kw: number; units: number; required_kw: number; binding: string; peak_load_kw: number; surge_requirement_kw: number; pv_requirement_kw: number; largest_motor_kw: number; largest_motor_multiplier: number; surge_factor: number; pv_ratio_max: number; sizes_kw: number[] }
  monthly: { month: number; days: number; consumption_kwh: number; production_kwh: number; direct_kwh: number; battery_kwh: number; export_kwh: number; curtailed_kwh: number; import_kwh: number; unserved_kwh: number }[]
  profiles: Record<string, DayProfile>
  warnings: Warning[]
}

export interface Results {
  computed_at: string
  months: string[]
  dataset: { id: string; lat: number; lon: number; elevation_m: number; radiation_db: string; distance_km: number; synthetic: boolean; source: string | null }
  panels: PanelResult[]
  selected_panel_id: string
  best_panel: { id: string; name: string; watt_peak: number; count: number; system_kwp: number }
  k: {
    sets: ReadingSetResult[]
    selected_set_index: number | null
    k_site: number
    k_raw: number
    thermal: string
    thermal_kind: string
    rise_c_per_kw: number | null
  }
  production: SimulationResult
  reference: SimulationResult
  shade: Record<string, ShadeFace>
  comparison: { deviation_pct: number; monthly_deviation_pct: number[]; description: string }
  legacy_method: { monthly_kwh: number; annual_kwh: number; formula: string }
  audit: AuditBlock | null
  sizing: SizingBlock | null
  pricing: PricingBlock | null
  program: ProgramBlock | null
  economics: EconomicsBlock | null
  nasa_reference: {
    point: { lat: number; lon: number; distance_km: number }
    nasa_ghi_psh: (number | null)[]
    pvgis_ghi_psh: number[]
    monthly_diff_pct: (number | null)[]
    nasa_annual_psh: number | null
    pvgis_annual_psh: number
    annual_diff_pct: number | null
  } | null
  warnings: Warning[]
}

export interface AssessmentOut {
  id: number
  created_at: string
  updated_at: string
  doc: AssessmentDoc
  results: Results | null
  results_stale: boolean
}

export interface DataStatus {
  pvgis: { available: boolean; synthetic: boolean; source: string | null; radiation_db: string | null; downloaded_at: string | null; cell_count: number; skipped_count: number }
  nasa: { available: boolean; point_count: number; source?: string }
}

export interface AppSettings {
  company_name: string
  company_contact: string
  [key: string]: string
}

/** Company profile fields, in Settings order. Mirrors backend profile.PROFILE_FIELDS. */
export const PROFILE_FIELDS: { key: string; label: string; hint?: string }[] = [
  { key: 'company_name', label: 'Company name' },
  { key: 'company_contact', label: 'Contact line on documents', hint: 'Address, phone, email, as one line under the company name.' },
  { key: 'address', label: 'Office address' },
  { key: 'phone', label: 'Phone or mobile' },
  { key: 'messenger', label: 'Messenger link', hint: 'https://m.me/yourpage' },
  { key: 'facebook', label: 'Facebook page link' },
  { key: 'email', label: 'Email' },
  { key: 'owner_name', label: "Owner's name", hint: 'Signs the proposal; named in the booking thank-you.' },
  { key: 'pee_name', label: 'Professional Electrical Engineer' },
  { key: 'pee_license', label: 'PEE licence number (PRC)' },
  { key: 'service_area', label: 'Where you install', hint: 'e.g. Laguna and Batangas' },
  { key: 'brands', label: 'Brands you install', hint: 'One line, e.g. Blue Carbon TOPCon panels, Felicity hybrid inverters, LiFePO4 batteries' },
  { key: 'warranty_workmanship_years', label: 'Workmanship warranty (years)' },
  { key: 'warranty_panels_product_years', label: 'Panel product warranty (years)' },
  { key: 'warranty_panels_performance_years', label: 'Panel performance warranty (years)' },
  { key: 'warranty_inverter_years', label: 'Inverter warranty (years)' },
  { key: 'warranty_battery_years', label: 'Battery warranty (years)' },
  { key: 'payment_details', label: 'Where to pay', hint: 'Bank or GCash details printed in the proposal acceptance block.' },
  { key: 'callback_promise', label: 'After a booking, you reach out', hint: 'e.g. within one working day' },
  { key: 'privacy_note', label: 'Privacy line under the booking form' },
]

export const SKY_CONDITIONS = ['clear', 'partly cloudy', 'hazy', 'cloudy', 'overcast']

export function newFace(name: string): RoofFace {
  return { id: newId(), name, shape: 'rect', length_m: 10, width_m: 6, ridge_m: null, tilt_deg: 15, azimuth_deg: 180, panels_left_out: 0, panel_count_override: null, walls: [], obstacles: [] }
}

export function newId(): string {
  return Math.random().toString(36).slice(2, 10)
}

export function emptyDoc(): AssessmentDoc {
  return {
    customer_name: '',
    address: '',
    notes: '',
    lat: null,
    lon: null,
    faces: [newFace('Roof 1')],
    panels: [{ id: newId(), name: '', watt_peak: 550, length_m: 2.278, width_m: 1.134 }],
    selected_panel_id: null,
    reading_sets: [],
    test_panel_rating_w: 50,
    test_panel_calibration: 1.0,
    setback_m: 0.6,
    gap_m: 0,
    card_next_step: '',
    audit: emptyAudit(),
    pricing: emptyPricingJob(),
    program: emptyProgramJob(),
    economics: emptyEconomicsJob(),
  }
}

export function emptyAudit(): EnergyAudit {
  return {
    appliances: [],
    bills: [],
    reconcile: true,
    system: {
      kind: 'combination',
      offgrid_pv_margin: 1.25,
      inverter_sizes_kw: [6, 8, 10, 12],
      inverter_surge_factor: 2.0,
      pv_ratio_max: 1.3,
      battery_dod: 0.85,
      battery_efficiency: 0.92,
    },
  }
}

export function newAppliance(): ApplianceEntry {
  return { id: newId(), name: '', brand: '', model: '', category: 'other', input_power_w: 0, quantity: 1, duty_factor: null, status: 'existing', windows: [newWindow()], notes: '' }
}

export function newWindow(): UsageWindow {
  return { start: '18:00', end: '22:00', days: [0, 1, 2, 3, 4, 5, 6], months: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] }
}

export function newBill(): BillEntry {
  const d = new Date()
  d.setMonth(d.getMonth() - 1)
  return { id: newId(), billing_month: d.toISOString().slice(0, 7), kwh: 0, days: null, amount_php: null, utility: '' }
}

export function windowHours(w: UsageWindow): number {
  const [sh, sm] = w.start.split(':').map(Number)
  const [eh, em] = w.end.split(':').map(Number)
  const s = sh * 60 + sm
  const e = eh * 60 + em
  if (s === e) return 24
  return (((e - s) % 1440) + 1440) % 1440 / 60
}

export function newReadingSet(faceId: string | null): ReadingSet {
  const now = new Date()
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
  return {
    id: newId(),
    face_id: faceId,
    label: '',
    measured_at: local,
    ambient_temp_c: null,
    sky_condition: 'clear',
    readings: [
      { irradiance_wm2: 0, power_w: 0, module_temp_c: null },
      { irradiance_wm2: 0, power_w: 0, module_temp_c: null },
      { irradiance_wm2: 0, power_w: 0, module_temp_c: null },
    ],
  }
}

