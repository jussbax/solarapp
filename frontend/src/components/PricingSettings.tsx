import { useEffect, useState } from 'react'
import { api } from '../api'
import type { PricingConfig } from '../types'

const SECTION_LABELS: Record<string, string> = {
  truck: 'Truck and freight run', handling: 'Handling at base', route: 'Route (stops, km and toll matrices)', categories: 'Categories: wastage and markup tiers',
  labor: 'Labour day rates', roof: 'Roof work', ground: 'Ground work', hauling: 'Hauling', mobdemob: 'Mob/demob', tools: 'Tools', job: 'Job level: fees, markups, VAT, rounding',
  job_defaults: 'Job defaults', wiring: 'Wiring rules and voltage drop', roles: 'BOQ item roles (codes used by the generator)',
}
const SKIP = new Set(['imported_from', 'imported_at'])

function titleCase(k: string) {
  return k.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
}

export default function PricingSettings() {
  const [cfg, setCfg] = useState<PricingConfig | null>(null)
  const [open, setOpen] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [jsonDrafts, setJsonDrafts] = useState<Record<string, string>>({})

  useEffect(() => {
    api.pricingConfig().then(setCfg).catch((e) => setError(e.message))
  }, [])
  if (!cfg) return <div className="muted">{error ?? 'Loading pricing settings...'}</div>

  const setField = (section: string, key: string, value: unknown) => setCfg({ ...cfg, [section]: { ...cfg[section], [key]: value } })
  const save = async () => {
    setError(null)
    try {
      for (const [path, text] of Object.entries(jsonDrafts)) {
        const [section, key] = path.split('.')
        try {
          JSON.parse(text)
        } catch {
          throw new Error(`${titleCase(section)} › ${titleCase(key)} is not valid JSON.`)
        }
      }
      const r = await api.savePricingConfig(cfg)
      setCfg(r)
      setJsonDrafts({})
      setMsg('Pricing settings saved. Recompute an assessment to apply them.')
    } catch (e) {
      setError((e as Error).message)
    }
  }
  const reset = async () => {
    if (!window.confirm('Reset all pricing settings to the built-in workbook defaults?')) return
    setCfg(await api.resetPricingConfig())
    setJsonDrafts({})
    setMsg('Reset to defaults.')
  }

  const renderValue = (section: string, key: string, v: unknown) => {
    const path = `${section}.${key}`
    if (typeof v === 'number') {
      return (
        <input
          type="number"
          step="any"
          value={v}
          style={{ width: 140 }}
          onChange={(e) => setField(section, key, e.target.value === '' ? 0 : Number(e.target.value))}
        />
      )
    }
    if (typeof v === 'boolean') return <input type="checkbox" checked={v} onChange={(e) => setField(section, key, e.target.checked)} style={{ width: 'auto' }} />
    if (typeof v === 'string') return <input value={v} onChange={(e) => setField(section, key, e.target.value)} />
    const text = jsonDrafts[path] ?? JSON.stringify(v, null, Array.isArray(v) && v.length > 0 && typeof v[0] !== 'object' ? 0 : 1)
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
        {cfg.imported_at ? ` on ${new Date(cfg.imported_at).toLocaleString()}` : ''}. These drive the price build-up; the workbook's DRIVERS, ROUTE, LABOR RATES, MOB-DEMOB,
        TOOLS and JOB sheets live here now.
      </div>
      {sections.map((sec) => {
        const v = cfg[sec]
        const isObj = v && typeof v === 'object' && !Array.isArray(v)
        return (
          <div key={sec} className="set-card">
            <div className="inline" style={{ cursor: 'pointer', fontWeight: 600 }} onClick={() => setOpen(open === sec ? null : sec)}>
              <span>{open === sec ? '▾' : '▸'}</span> {SECTION_LABELS[sec] ?? titleCase(sec)}
            </div>
            {open === sec && (
              <div style={{ marginTop: 8 }}>
                {isObj ? (
                  <table>
                    <tbody>
                      {Object.entries(v as Record<string, unknown>).map(([k, val]) => (
                        <tr key={k}>
                          <th style={{ width: 240, textAlign: 'left', verticalAlign: 'top' }}>{titleCase(k)}</th>
                          <td>{renderValue(sec, k, val)}</td>
                        </tr>
                      ))}
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
      <div style={{ marginTop: 8 }}>
        <button type="button" className="primary" onClick={save}>
          Save pricing settings
        </button>{' '}
        <button type="button" onClick={reset}>
          Reset to defaults
        </button>{' '}
        {msg && <span className="muted">{msg}</span>}
        {error && <span className="badge bad">{error}</span>}
      </div>
    </div>
  )
}
