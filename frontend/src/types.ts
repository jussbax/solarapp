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
  module_temp_c: number
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
  }
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
      { irradiance_wm2: 0, power_w: 0, module_temp_c: 0 },
      { irradiance_wm2: 0, power_w: 0, module_temp_c: 0 },
      { irradiance_wm2: 0, power_w: 0, module_temp_c: 0 },
    ],
  }
}
