import { useEffect, useState } from 'react'
import { api } from '../api'
import type { PricingBlock, PricingChoices, PricingConfig, Results, SizingBlock } from '../types'

/** Settings is a menu of pages, one route each: picking an entry shows that page alone. The six pricing entries share
 * one draft of the pricing config; a pricing section the entries do not name lands at the end of System design under
 * "Other settings", so a section added later is never lost. `owner` entries are hidden from an engineer. */
export interface SettingsEntry {
  id: string
  route: string
  label: string
  /** One line under the title (the phone list shows it under the label). */
  lead: string
  owner?: boolean
  /** The pricing config sections this page edits, in page order. */
  sections?: string[]
}

export const SETTINGS_ENTRIES: SettingsEntry[] = [
  { id: 'company', route: '/settings/company', label: 'Company', lead: 'Who you are on the documents: profile, the signing engineer, contact line, warranties, where to pay.' },
  { id: 'website', route: '/settings/website', label: 'Website', lead: 'The estimate page and the booking form: links, brands, privacy line, and what the public estimate assumes.', owner: true },
  { id: 'materials', route: '/settings/pricing/materials', label: 'Materials and markup', lead: 'What each item sells for: markup and wastage by category, the job-level fees and VAT, the wiring rules, the string design and the items the generator picks.', owner: true, sections: ['categories', 'job', 'wiring', 'string_design', 'roles'] },
  { id: 'labor', route: '/settings/pricing/labor', label: 'Labor and crew', lead: 'Day rates, the roof and ground work behind the man-hours, hauling, crew transport, tools, and the job defaults a project starts from.', owner: true, sections: ['labor', 'job_defaults', 'roof', 'ground', 'hauling', 'mobdemob', 'tools'] },
  { id: 'freight', route: '/settings/pricing/freight', label: 'Freight and the truck', lead: 'The base, the truck and its running cost, handling at base, and the route with its km and toll between stops.', owner: true, sections: ['company_base', 'truck', 'handling', 'route'] },
  { id: 'program', route: '/settings/pricing/program', label: 'Program of works', lead: 'The site day, the durations the schedule assumes, the payment terms a proposal starts from, and when money moves.', owner: true, sections: ['program'] },
  { id: 'savings', route: '/settings/pricing/savings', label: 'Customer savings', lead: 'Tariff, export credit, price rise, the analysis period and the lifetimes the customer savings count on.', owner: true, sections: ['economics'] },
  { id: 'system', route: '/settings/pricing/system', label: 'System design', lead: "Losses after the panels, how many evenings the battery must carry, and the power factors the plans' schedule of loads prints as assumptions.", owner: true, sections: ['system_losses', 'sizing', 'loads'] },
  { id: 'account', route: '/settings/account', label: 'Your account', lead: 'Your password, two-step verification, security keys and devices.' },
  { id: 'people', route: '/settings/people', label: 'People', lead: 'Who can sign in to the back office.', owner: true },
  { id: 'data', route: '/settings/data', label: 'Weather and data', lead: 'The weather dataset every calculation runs on.' },
]

/** The pricing section the Website page edits beside the profile fields (the public estimate's assumptions). */
export const WEBSITE_SECTION = 'quick'

/** The entry a settings path belongs to, for the top bar's page name and the menu's current mark. */
export function settingsEntryFor(pathname: string): SettingsEntry | undefined {
  return SETTINGS_ENTRIES.find((e) => pathname === e.route || pathname.startsWith(e.route + '/'))
}

/** Round for display: a value shown with `decimals` places, trailing zeros dropped (12.5, 12, 0.89). */
export const roundTo = (v: number, decimals: number) => {
  const f = 10 ** decimals
  return Math.round(v * f) / f
}

/** Axis ticks in thousands: "1.5k" when the step is under a thousand, "2k" otherwise. */
export const kTick = (v: number) => (Math.abs(v) < 1000 ? String(v) : Number.isInteger(v / 1000) ? `${v / 1000}k` : `${(v / 1000).toFixed(1)}k`)

/** The pricing settings as the defaults the project inputs fall back to; null until loaded or when the server refuses. */
export function usePricingDefaults(): PricingConfig | null {
  const [cfg, setCfg] = useState<PricingConfig | null>(null)
  useEffect(() => {
    api
      .pricingConfig()
      .then(setCfg)
      .catch(() => setCfg(null))
  }, [])
  return cfg
}

const positive = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) && v > 0 ? v : null)

/** The battery the customer is sold, in nominal kWh as the proposal prints it: the BOM's battery (the server's own
 * nominal figure where it carries one, else the chosen option's rating times its units, else the priced line), and
 * only without pricing the sized figure. */
export function batteryNominalKwh(results: Results): number {
  const pricing = results.pricing
  const sizing = results.sizing
  if (pricing?.available) {
    const p = pricing as PricingBlock & { battery_nominal_kwh?: unknown; customer_battery_kwh?: unknown }
    const direct = positive(p.battery_nominal_kwh) ?? positive(p.customer_battery_kwh)
    if (direct != null) return direct
    const ch = (pricing.choices ?? {}) as PricingChoices & { battery_nominal_kwh?: unknown }
    const fromChoices = positive(ch.battery_nominal_kwh)
    if (fromChoices != null) return fromChoices
    const opt = ch.battery_options?.find((o) => o.code === ch.battery_code)
    const units = ch.battery_units ?? 0
    if (opt && units > 0) return opt.rating_kwh * units
    const line = (pricing.lines ?? []).find((l) => l.role === 'battery' && l.found)
    if (line && /kwh/i.test(line.rating_unit ?? '') && line.rating) return line.rating * line.qty
    if (ch.battery_code == null && units === 0 && sizing?.kind === 'net_metering') return 0
  }
  const b = (sizing?.battery ?? {}) as SizingBlock['battery'] & { nominal_kwh?: unknown }
  return positive(b.nominal_kwh) ?? positive(b.installed_kwh) ?? 0
}
