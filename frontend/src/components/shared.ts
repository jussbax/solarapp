import { useEffect, useState } from 'react'
import { api } from '../api'
import type { PricingBlock, PricingChoices, PricingConfig, Results, SizingBlock } from '../types'

/** The pricing settings in the groups the owner looks for them under; a section the map does not name lands in
 * "Other settings" at the end, so a section added later is never lost. The ids are the Settings index's anchors. */
export const PRICING_GROUPS: { id: string; label: string; lead: string; sections: string[] }[] = [
  { id: 'pricing-materials', label: 'Materials and markup tiers', lead: 'What each item sells for: the markup tier and wastage per category, the job-level markups, VAT and rounding, the parts the generator picks, and the wiring rules.', sections: ['categories', 'job', 'roles', 'wiring'] },
  { id: 'pricing-labor', label: 'Labor and crew', lead: 'Day rates, the roof and ground work rates behind the man-hours, hauling, crew transport, tools, and the job defaults a project starts from.', sections: ['labor', 'job_defaults', 'roof', 'ground', 'hauling', 'mobdemob', 'tools'] },
  { id: 'pricing-freight', label: 'Freight and the truck', lead: 'The base, the truck and its running cost, handling at base, and the route with its km and toll matrices.', sections: ['company_base', 'truck', 'handling', 'route'] },
  { id: 'pricing-program', label: 'Program of works', lead: 'The site day, the durations the schedule assumes, when money moves, and the payment terms a proposal starts from.', sections: ['program'] },
  { id: 'pricing-economics', label: 'Economics and warranties', lead: 'Tariff, export credit, price rise, the analysis period and the lifetimes the customer savings count on.', sections: ['economics'] },
  { id: 'pricing-system', label: 'System design and the website estimate', lead: 'Losses after the panels, how many evenings the battery must carry, and the typical roof the public estimate assumes.', sections: ['system_losses', 'sizing', 'quick'] },
]

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

type Week = { week: string; inflow: number; outflow: number; balance: number }
const dayIndex = (iso: string) => {
  const [y, m, dd] = iso.slice(0, 10).split('-').map(Number)
  return Math.floor(Date.UTC(y, m - 1, dd) / 86400000)
}
const isoDay = (i: number) => new Date(i * 86400000).toISOString().slice(0, 10)

/** Every week from the first flow to the last, so the cashflow chart is to scale: a week with no flow carries the balance. */
export function fillWeeks(weekly: Week[]): Week[] {
  if (weekly.length < 2) return weekly
  const sorted = [...weekly].sort((a, b) => a.week.localeCompare(b.week))
  const byDay = new Map(sorted.map((w) => [dayIndex(w.week), w]))
  const first = dayIndex(sorted[0].week)
  const last = dayIndex(sorted[sorted.length - 1].week)
  const out: Week[] = []
  let balance = 0
  const seen = new Set<number>()
  for (let i = first; i <= last; i += 7) {
    const w = byDay.get(i)
    if (w) {
      balance = w.balance
      seen.add(i)
      out.push(w)
    } else out.push({ week: isoDay(i), inflow: 0, outflow: 0, balance })
  }
  // a week off the seven-day grid (never in the server's buckets, kept for safety) goes in by date
  for (const w of sorted) if (!seen.has(dayIndex(w.week))) out.push(w)
  return out.sort((a, b) => a.week.localeCompare(b.week))
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
