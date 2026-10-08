export type Goal = 'net_metering' | 'combination' | 'off_grid'
export type Pattern = 'morning' | 'balanced' | 'evening'

export interface Town {
  name: string
  province: string
  lat: number
  lon: number
}

export interface PublicProfile {
  company_name: string
  address: string
  phone: string
  messenger: string
  facebook: string
  email: string
  owner_name: string
  pee_name: string
  pee_license: string
  service_area: string
  brands: string
  warranty_workmanship_years: string
  warranty_panels_product_years: string
  warranty_panels_performance_years: string
  warranty_inverter_years: string
  warranty_battery_years: string
  callback_promise: string
  privacy_note: string
}

export interface EstimateStatus {
  enabled: boolean
  data: boolean
  profile: PublicProfile
  warranty: string[]
  towns: Town[]
  public_url: string
}

export interface LeadSource {
  utm_source: string
  utm_medium: string
  utm_campaign: string
  utm_content: string
  fbclid: string
  referrer: string
  page: string
}

export interface EstimateRequest {
  goal: Goal
  town: string
  province: string
  lat: number | null
  lon: number | null
  monthly_kwh: number | null
  monthly_php: number | null
  pattern: Pattern
}

export interface Variant {
  goal: Goal
  goal_label: string
  location: { distance_km: number; sun_kwh_per_kwp_year: number; road_km: number | null }
  system: { panels: number; panel_wp: number; panel_name: string; kwp: number; inverter_kw: number; inverter_units: number; battery_kwh: number; roof_area_m2: number; roof_limited: boolean }
  production: {
    annual_kwh: number
    monthly_kwh: number[]
    coverage_pct: number
    self_consumption_pct: number
    annual_export_kwh: number
    annual_import_kwh: number
    annual_unserved_kwh: number
    annual_consumption_kwh: number
    production_vs_use_pct: number
  }
  price: { total: number; materials: number; labor: number; equipment: number; tax: number; price_per_wp: number; battery_part: number }
  economics: {
    bill_before_monthly: number
    bill_after_monthly: number
    savings_monthly: number
    savings_year1: number
    payback_years: number | null
    lifetime_net: number
    analysis_years: number
    irr: number | null
    co2_t_per_year: number
  } | null
}

export interface EstimateResult extends Variant {
  inputs: { goal: Goal; goal_label: string; pattern: Pattern; pattern_label: string; monthly_kwh: number; tariff_php_per_kwh: number; lat: number; lon: number; town: string; province: string; place: string; in_area: boolean }
  alternative: Variant | null
  assumptions: string[]
  warnings: string[]
}

export interface LeadRequest extends EstimateRequest {
  name: string
  contact: string
  address: string
  preferred_time: string
  consent: boolean
  website: string
  source: LeadSource
  estimate: { goal: Goal; panels: number; kwp: number; battery_kwh: number; price: number; bill_before_monthly: number | null; bill_after_monthly: number | null; payback_years: number | null }
}
