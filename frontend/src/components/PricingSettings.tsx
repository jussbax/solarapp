import { useEffect, useMemo, useState } from 'react'
import { useBlocker } from 'react-router-dom'
import { api } from '../api'
import type { PaymentPlan, PricingConfig } from '../types'
import { PaymentPlanEditor } from './ProgramSection'
import { fmtDate } from '../fmt'

const SECTION_LABELS: Record<string, string> = {
  company_base: 'Company base',
  truck: 'Truck and freight run', handling: 'Handling at base', route: 'Route: stops, km and toll', categories: 'Categories: wastage and markup tiers',
  labor: 'Labor day rates', roof: 'Roof work', ground: 'Ground work', hauling: 'Hauling', mobdemob: 'Crew transport (mob/demob)', tools: 'Tools', job: 'Job level: fees, markups, VAT, rounding',
  job_defaults: 'Job defaults', wiring: 'Wiring rules and voltage drop', roles: 'BOM item roles (codes the generator uses)',
  program: 'Program of works: site day, durations, payment terms', economics: 'Savings: tariff, export credit, escalation, lifetimes',
  system_losses: 'System losses after the panels (figures at the meter)', sizing: 'System sizing: battery autonomy', quick: 'Website estimate',
}
const SKIP = new Set(['imported_from', 'imported_at'])
// percentages are stored as fractions (0.12) and edited as percent (12)
const PCT_KEYS = new Set([
  'vat', 'agent_commission', 'freight_markup', 'services_markup', 'ocm_share', 'tariff_escalation', 'degradation', 'discount_rate', 'om_share_per_year',
  'dc_drop_limit', 'ac_drop_limit', 'installment_share', 'dealer_discount', 'payment_fee', 'wastage', 'markup', 'roof_factor', 'k_site',
  'inverter', 'wiring', 'soiling', 'other',
])
const TIME_KEYS = new Set(['depart_time', 'lunch_start'])
// label, unit and one-line help for the keys the owner meets most; the rest are title-cased
const META: Record<string, { label: string; unit?: string; help?: string }> = {
  'job.agent_commission': { label: 'Commission', unit: '% of direct cost', help: 'Paid in cash after the job.' },
  'job.vat': { label: 'VAT', unit: '%' },
  'job.freight_markup': { label: 'Freight markup', unit: '%' },
  'job.services_markup': { label: 'Services markup', unit: '%', help: 'On labor, permits and tools.' },
  'job.ppe_per_person_day': { label: 'Safety gear', unit: '₱ per person-day' },
  'job.pee_seal': { label: 'PEE sign and seal', unit: '₱' },
  'job.lgu_permit_cfei': { label: 'Electrical permit and final inspection', unit: '₱' },
  'job.erc_coc_fee': { label: 'ERC Certificate of Compliance', unit: '₱' },
  'job.bidirectional_meter_fee': { label: 'Net metering meter', unit: '₱' },
  'job.ocm_share': { label: 'Overhead share of markup', unit: '%' },
  'job.round_up_to': { label: 'Round the contract up to', unit: '₱' },
  'job.quotation_validity_days': { label: 'Proposal valid for', unit: 'days' },
  'labor.team_lead_day': { label: 'Team lead', unit: '₱ per day' },
  'labor.skilled_day': { label: 'Skilled technician', unit: '₱ per day' },
  'labor.laborer_day': { label: 'Helper', unit: '₱ per day' },
  'labor.allowance_included': { label: 'Allowance included', unit: '₱ per day' },
  'labor.owner_day': { label: 'Owner on site', unit: '₱ per day' },
  'labor.paid_hours': { label: 'Paid hours', unit: 'h per day' },
  'labor.nonproductive_hours': { label: 'Non-productive hours', unit: 'h per day' },
  'tools.charge_per_installation_day': { label: 'Tool charge', unit: '₱ per installation day' },
  'job_defaults.roof_factor': { label: 'Roof productivity factor', unit: '%' },
  'job_defaults.roof_closed_days': { label: 'Days the roof is closed', unit: 'days' },
  'job_defaults.max_days': { label: 'Max installation days', unit: 'days' },
  'job_defaults.max_pairs': { label: 'Max roof pairs' },
  'job_defaults.battery_haul_hours': { label: 'Battery haul', unit: 'h' },
  'job_defaults.owner_days': { label: 'Owner days on site', unit: 'days' },
  'job_defaults.extra_km': { label: 'Extra km (one way)', unit: 'km' },
  'job_defaults.extra_toll': { label: 'Extra toll', unit: '₱' },
  'wiring.pv_run_m': { label: 'PV run per string', unit: 'm' },
  'wiring.ac_run_m': { label: 'AC run', unit: 'm' },
  'wiring.grounding_run_m': { label: 'Grounding run', unit: 'm' },
  'wiring.conduit_m': { label: 'Conduit', unit: 'm' },
  'wiring.dc_drop_limit': { label: 'DC voltage drop limit', unit: '%' },
  'wiring.ac_drop_limit': { label: 'AC voltage drop limit', unit: '%' },
  'wiring.ac_voltage': { label: 'AC voltage', unit: 'V' },
  'wiring.battery_voltage': { label: 'Battery voltage', unit: 'V' },
  'wiring.panel_vmp_v': { label: 'Panel Vmp', unit: 'V' },
  'wiring.continuous_factor': { label: 'Continuous current factor', help: '1.25 per the code.' },
  'wiring.thhn_ampacity': { label: 'THHN ampacity', unit: 'A per mm² size', help: 'PEC 60 °C column.' },
  'wiring.battery_cable_ampacity': { label: 'Battery cable ampacity', unit: 'A per mm² size' },
  'roles.rail_length_m': { label: 'Rail length', unit: 'm' },
  'roles.l_feet_per_rail': { label: 'L-feet per rail' },
  'roles.mc4_pairs_per_string': { label: 'MC4 pairs per string' },
  'roles.default_inverter_code_grid': { label: 'Default inverter for net metering (code)', help: 'Must be marked grid-interactive on the Materials page (the electric company asks for the anti-islanding listing). Set at import to the first grid-interactive hybrid in the workbook; blank = the cheapest grid-interactive unit that fits. Parallel units as needed.' },
  'roles.default_inverter_code_offgrid': { label: 'Default inverter for off-grid (code)', help: 'Felicity 6 kW eco-hybrid by default; blank = the cheapest hybrid that fits. Parallel units as needed.' },
  'program.min_task_minutes': { label: 'Minimum task durations', unit: 'minutes', help: 'A floor for the hour-by-hour plan (commissioning, battery, inverter), in minutes; the labor price is not changed. When the floors push the plan past the priced days the program warns.' },
  'system_losses.inverter': { label: 'Inverter', unit: '% of energy kept', help: 'DC to AC conversion in the inverter: the datasheet\'s weighted efficiency.' },
  'system_losses.wiring': { label: 'Wiring', unit: '% of energy kept', help: 'DC and AC cable runs, connectors and terminations.' },
  'system_losses.soiling': { label: 'Soiling', unit: '% of energy kept', help: 'Dust and dirt on the panels between rains; verify locally (a rice-field roof collects more in the dry season).' },
  'system_losses.other': { label: 'Other', unit: '% of energy kept', help: 'Module mismatch, availability and anything else after the panels. The four multiply: the array is sized on energy at the meter and the customer documents print that figure.' },
  'sizing.days_of_autonomy': { label: 'Days of autonomy', unit: 'evenings', help: 'The evenings the battery must carry without sun; your choice. 1 = the night deficit of the worst typical day (the rule until now), 2 = twice that. The balance over a real year of weather then reports how often it still runs out.' },
  'roles.ac_breaker_amps': { label: 'Default AC breaker', unit: 'A' },
  'program.depart_time': { label: 'Leave base at' },
  'program.lunch_start': { label: 'Lunch at' },
  'program.lunch_minutes': { label: 'Lunch', unit: 'minutes' },
  'program.travel_speed_kmh': { label: 'Travel speed', unit: 'km/h' },
  'program.permit_prep_days': { label: 'Plans and PEE seal', unit: 'days' },
  'program.permit_approval_days': { label: 'Electrical permit approval', unit: 'days', help: 'Assumption until you have data.' },
  'program.cfei_days': { label: 'Final inspection certificate', unit: 'days after installation', help: 'Assumption.' },
  'program.netmeter_application_days': { label: 'Net metering application and agreement', unit: 'days', help: 'Assumption.' },
  'program.netmeter_meter_days': { label: 'Inspection and net metering meter', unit: 'days after switch-on', help: 'Assumption.' },
  'program.sourcing_days_before_install': { label: 'Pickup run before installation', unit: 'days' },
  'program.install_gap_after_permit_days': { label: 'Installation after the permit', unit: 'days' },
  'program.commissioning_offset_days': { label: 'Switch-on after the last installation day', unit: 'days' },
  'program.labour_paid_days_after_job': { label: 'Labor paid after the job', unit: 'days' },
  'program.commission_paid_days_after_job': { label: 'Commission paid after the job', unit: 'days' },
  'program.vat_remit_days_after_completion': { label: 'VAT remitted after completion', unit: 'days' },
  'program.payment': { label: 'Payment terms' },
  'economics.tariff_php_per_kwh': { label: 'Tariff when the audit has no bill', unit: '₱ per kWh' },
  'economics.export_rate_php_per_kwh': { label: 'Net metering credit', unit: '₱ per kWh', help: "The electric company's generation rate, lower than the tariff." },
  'economics.tariff_escalation': { label: 'Electricity price rise', unit: '% a year' },
  'economics.degradation': { label: 'Panel output loss', unit: '% a year' },
  'economics.analysis_years': { label: 'Analysis period', unit: 'years' },
  'economics.discount_rate': { label: 'Discount rate', unit: '%' },
  'economics.battery_life_years': { label: 'Battery life', unit: 'years' },
  'economics.inverter_life_years': { label: 'Inverter life', unit: 'years' },
  'economics.om_share_per_year': { label: 'Upkeep', unit: '% of contract a year' },
  'economics.co2_kg_per_kwh': { label: 'Grid emission factor', unit: 'kg CO2 per kWh' },
  'quick.enabled': { label: 'Estimate page switched on' },
  'quick.panel_code': { label: 'Panel used (code)' },
  'quick.k_site': { label: 'Typical site factor', unit: '%' },
  'quick.tilt_deg': { label: 'Typical roof pitch', unit: '°' },
  'quick.azimuth_deg': { label: 'Typical roof facing', unit: '°' },
  'quick.max_panels': { label: 'Most panels an estimate may use' },
  'quick.panels_per_row': { label: 'Panels per row' },
  'quick.peak_factor': { label: 'Peak over the busiest hour', unit: '×' },
  'quick.price_round_to': { label: 'Round the price up to', unit: '₱' },
  'quick.max_requests_per_hour': { label: 'Estimates per browser per hour' },
  'truck.running_cost_per_km': { label: 'Truck running cost', unit: '₱ per km' },
  'truck.toll_per_round_trip': { label: 'Toll per round trip', unit: '₱' },
  'route.stops': { label: 'Stops in driving order' },
  'route.km': { label: 'Km between stops' },
  'route.toll': { label: 'Toll between stops', unit: '₱' },
}

function titleCase(k: string) {
  return k.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
}
const isMatrix = (v: unknown): v is number[][] => Array.isArray(v) && v.length > 0 && v.every((r) => Array.isArray(r) && r.every((x) => typeof x === 'number'))
const isPrimList = (v: unknown): v is (string | number)[] => Array.isArray(v) && v.every((x) => typeof x === 'string' || typeof x === 'number')
const isPrimDict = (v: unknown): v is Record<string, string | number> => !!v && typeof v === 'object' && !Array.isArray(v) && Object.values(v as object).every((x) => typeof x === 'string' || typeof x === 'number')

export default function PricingSettings() {
  const [cfg, setCfg] = useState<PricingConfig | null>(null)
  const [saved, setSaved] = useState<PricingConfig | null>(null)
  const [open, setOpen] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [jsonDrafts, setJsonDrafts] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .pricingConfig()
      .then((c) => {
        setCfg(c)
        setSaved(c)
      })
      .catch((e) => setError(e.message))
  }, [])

  const dirtySections = useMemo(() => {
    if (!cfg || !saved) return []
    return Object.keys(cfg).filter((k) => !SKIP.has(k) && JSON.stringify(cfg[k]) !== JSON.stringify(saved[k]))
  }, [cfg, saved])
  const dirty = dirtySections.length > 0

  useEffect(() => {
    if (!dirty) return
    const onUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener('beforeunload', onUnload)
    return () => window.removeEventListener('beforeunload', onUnload)
  }, [dirty])
  const blocker = useBlocker(dirty)
  useEffect(() => {
    if (blocker.state !== 'blocked') return
    if (window.confirm('Pricing settings have unsaved changes. Leave without saving?')) blocker.proceed()
    else blocker.reset()
  }, [blocker])

  if (!cfg) return <div className="muted">{error ?? 'Loading pricing settings...'}</div>

  const setField = (section: string, key: string, value: unknown) => setCfg({ ...cfg, [section]: { ...cfg[section], [key]: value } })
  const save = async () => {
    setError(null)
    setBusy(true)
    try {
      for (const [path, text] of Object.entries(jsonDrafts)) {
        const [section, key] = path.split('.')
        try {
          JSON.parse(text)
        } catch {
          throw new Error(`${SECTION_LABELS[section] ?? titleCase(section)} › ${titleCase(key)} is not valid JSON.`)
        }
      }
      const r = await api.savePricingConfig(cfg)
      setCfg(r)
      setSaved(r)
      setJsonDrafts({})
      setMsg('Pricing settings saved. Calculate an assessment again to apply them.')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  const reset = async () => {
    if (!window.confirm('Reset all pricing settings to the built-in workbook defaults? Your edits in every section are lost.')) return
    const r = await api.resetPricingConfig()
    setCfg(r)
    setSaved(r)
    setJsonDrafts({})
    setMsg('Reset to defaults.')
  }
  const discard = () => {
    if (saved) setCfg(saved)
    setJsonDrafts({})
  }

  const renderValue = (section: string, key: string, v: unknown) => {
    const path = `${section}.${key}`
    const meta = META[path]
    if (typeof v === 'number') {
      const pct = PCT_KEYS.has(key)
      return (
        <span className="inline">
          <input
            type="number"
            step="any"
            value={pct ? Math.round(v * 10000) / 100 : v}
            style={{ width: 130 }}
            onChange={(e) => {
              const n = e.target.value === '' ? 0 : Number(e.target.value)
              setField(section, key, pct ? n / 100 : n)
            }}
          />
          {(meta?.unit || pct) && <span className="muted">{meta?.unit ?? '%'}</span>}
        </span>
      )
    }
    if (typeof v === 'boolean') return <input type="checkbox" checked={v} onChange={(e) => setField(section, key, e.target.checked)} style={{ width: 'auto' }} />
    if (typeof v === 'string') {
      if (TIME_KEYS.has(key)) return <input type="time" value={v} style={{ width: 150 }} onChange={(e) => setField(section, key, e.target.value)} />
      return <input value={v} onChange={(e) => setField(section, key, e.target.value)} />
    }
    if (section === 'program' && key === 'payment') {
      return <PaymentPlanEditor plan={v as PaymentPlan} defaults={v as PaymentPlan} onChange={(p) => p && setField(section, key, p)} hideDefaultLink />
    }
    if (isMatrix(v)) {
      const stops: string[] = Array.isArray(cfg[section]?.stops) ? (cfg[section].stops as string[]) : v.map((_, i) => `#${i + 1}`)
      return (
        <div className="table-wrap scroll-x">
          <div className="scroll-note muted">Scroll sideways to see every stop.</div>
          <table className="matrix">
            <thead>
              <tr>
                <th></th>
                {stops.map((s, j) => (
                  <th key={j} className="num">
                    {s}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {v.map((row, i) => (
                <tr key={i}>
                  <th>{stops[i] ?? `#${i + 1}`}</th>
                  {row.map((x, j) => (
                    <td key={j} className="num">
                      <input
                        type="number"
                        step="any"
                        value={x}
                        style={{ width: 72 }}
                        onChange={(e) => {
                          const next = v.map((r) => [...r])
                          next[i][j] = e.target.value === '' ? 0 : Number(e.target.value)
                          setField(section, key, next)
                        }}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }
    if (isPrimList(v)) {
      const numeric = v.every((x) => typeof x === 'number')
      return (
        <input
          value={jsonDrafts[path] ?? v.join(', ')}
          onChange={(e) => {
            setJsonDrafts({ ...jsonDrafts, [path]: e.target.value })
            const parts = e.target.value.split(',').map((x) => x.trim()).filter(Boolean)
            setField(section, key, numeric ? parts.map(Number).filter((n) => Number.isFinite(n)) : parts)
          }}
          onBlur={() => {
            const d = { ...jsonDrafts }
            delete d[path]
            setJsonDrafts(d)
          }}
          placeholder="comma separated"
        />
      )
    }
    if (isPrimDict(v)) {
      return (
        <table className="kv">
          <tbody>
            {Object.entries(v).map(([k, x]) => (
              <tr key={k}>
                <th>{k}</th>
                <td>
                  <input
                    type={typeof x === 'number' ? 'number' : 'text'}
                    step="any"
                    value={x}
                    style={{ width: 150 }}
                    onChange={(e) => setField(section, key, { ...v, [k]: typeof x === 'number' ? (e.target.value === '' ? 0 : Number(e.target.value)) : e.target.value })}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )
    }
    const text = jsonDrafts[path] ?? JSON.stringify(v, null, 1)
    return (
      <textarea
        rows={Math.min(12, Math.max(2, text.split('\n').length))}
        value={text}
        style={{ fontFamily: 'monospace', fontSize: 12 }}
        onChange={(e) => {
          setJsonDrafts({ ...jsonDrafts, [path]: e.target.value })
          try {
            setField(section, key, JSON.parse(e.target.value))
          } catch {
            /* keep typing */
          }
        }}
      />
    )
  }

  const sections = Object.keys(cfg).filter((k) => !SKIP.has(k))
  return (
    <div>
      <div className="muted" style={{ marginBottom: 8 }}>
        Imported from {cfg.imported_from ?? 'built-in defaults'}
        {cfg.imported_at ? ` on ${fmtDate(cfg.imported_at)}` : ''}. These drive the price build-up; the workbook's DRIVERS, ROUTE,
        LABOR RATES, MOB-DEMOB, TOOLS and JOB sheets live here now. Percentages are shown as percent.
      </div>
      {sections.map((sec) => {
        const v = cfg[sec]
        const isObj = v && typeof v === 'object' && !Array.isArray(v)
        const changed = dirtySections.includes(sec)
        return (
          <div key={sec} className="set-card">
            <div className="inline" style={{ cursor: 'pointer', fontWeight: 600, width: '100%' }} onClick={() => setOpen(open === sec ? null : sec)}>
              <span>{open === sec ? '▾' : '▸'}</span> {SECTION_LABELS[sec] ?? titleCase(sec)}
              {changed && <span className="chip unsaved" style={{ marginLeft: 'auto' }}>edited</span>}
            </div>
            {open === sec && (
              <div style={{ marginTop: 8 }}>
                {isObj ? (
                  <table className="settings">
                    <tbody>
                      {Object.entries(v as Record<string, unknown>).map(([k, val]) => {
                        const meta = META[`${sec}.${k}`]
                        return (
                          <tr key={k}>
                            <th className="settings-key">
                              {meta?.label ?? titleCase(k)}
                              {meta?.help && <div className="hint">{meta.help}</div>}
                            </th>
                            <td>{renderValue(sec, k, val)}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div>
                    {typeof v === 'string' ? (
                      <input value={v} onChange={(e) => setCfg({ ...cfg, [sec]: e.target.value })} />
                    ) : (
                      <textarea
                        rows={10}
                        style={{ fontFamily: 'monospace', fontSize: 12 }}
                        value={jsonDrafts[sec] ?? JSON.stringify(v, null, 1)}
                        onChange={(e) => {
                          setJsonDrafts({ ...jsonDrafts, [sec]: e.target.value })
                          try {
                            setCfg({ ...cfg, [sec]: JSON.parse(e.target.value) })
                          } catch {
                            /* keep typing */
                          }
                        }}
                      />
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
      <div className="actions" style={{ position: 'sticky', bottom: 0 }}>
        <span className={`chip ${dirty ? 'unsaved' : 'ok'}`}>{dirty ? `${dirtySections.length} ${dirtySections.length === 1 ? 'section' : 'sections'} edited` : 'Saved'}</span>
        <button type="button" className="primary" onClick={save} disabled={!dirty || busy}>
          Save pricing settings
        </button>
        <button type="button" onClick={discard} disabled={!dirty}>
          Discard changes
        </button>
        <button type="button" onClick={reset} style={{ marginLeft: 'auto' }}>
          Reset to defaults
        </button>
        {msg && <span className="muted" style={{ flexBasis: '100%' }}>{msg}</span>}
        {error && (
          <div className="banner bad" style={{ flexBasis: '100%', margin: 0 }}>
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
