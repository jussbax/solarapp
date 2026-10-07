export interface RoofFace {
  id: string
  name: string
  length_m: number
  width_m: number
  tilt_deg: number
  azimuth_deg: number
  panel_count_override: number | null
}

export interface CandidatePanel {
  id: string
  name: string
  watt_peak: number
  length_m: number
  width_m: number
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
  autonomy_days: number
  offgrid_pv_margin: number
  inverter_sizes_kw: number[]
  inverter_surge_factor: number
  pv_ratio_max: number
  battery_module_kwh: number
  battery_dod: number
  battery_efficiency: number
  battery_max_modules: number
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
  audit: EnergyAudit
}

export interface AssessmentSummary {
  id: number
  created_at: string
  updated_at: string
  customer_name: string
  address: string
  has_results: boolean
  results_stale: boolean
  system_kwp: number | null
  annual_kwh: number | null
  panel_count: number | null
}

export interface Warning {
  code: string
  message: string
}

export interface LayoutOption {
  orientation: string
  along_length: number
  along_width: number
  count: number
}

export interface LayoutResult {
  usable_length_m: number
  usable_width_m: number
  options: LayoutOption[]
  best: LayoutOption
  count: number
  override_applied: boolean
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
  offgrid: { autonomy_days: number; pv_margin: number } | null
  battery: { modules: number; module_kwh: number; installed_kwh: number; usable_kwh: number; power_kw: number; depth_of_discharge: number; round_trip_efficiency: number }
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
  comparison: { deviation_pct: number; monthly_deviation_pct: number[]; description: string }
  legacy_method: { monthly_kwh: number; annual_kwh: number; formula: string }
  audit: AuditBlock | null
  sizing: SizingBlock | null
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
}

export const SKY_CONDITIONS = ['clear', 'partly cloudy', 'hazy', 'cloudy', 'overcast']

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
    faces: [{ id: newId(), name: 'Roof 1', length_m: 10, width_m: 6, tilt_deg: 15, azimuth_deg: 180, panel_count_override: null }],
    panels: [{ id: newId(), name: '', watt_peak: 550, length_m: 2.278, width_m: 1.134 }],
    selected_panel_id: null,
    reading_sets: [],
    test_panel_rating_w: 50,
    test_panel_calibration: 1.0,
    setback_m: 0.6,
    gap_m: 0,
    audit: emptyAudit(),
  }
}

export function emptyAudit(): EnergyAudit {
  return {
    appliances: [],
    bills: [],
    reconcile: true,
    system: {
      kind: 'combination',
      autonomy_days: 1.0,
      offgrid_pv_margin: 1.25,
      inverter_sizes_kw: [6, 8, 10, 12],
      inverter_surge_factor: 2.0,
      pv_ratio_max: 1.3,
      battery_module_kwh: 5.12,
      battery_dod: 0.9,
      battery_efficiency: 0.92,
      battery_max_modules: 8,
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
