import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import Field from './Field'
import NumberInput from './NumberInput'
import { PricingBar } from './PricingSettings'
import { META, fieldId, settingsIndex, useFindTarget, usePricingDraft } from './pricingMeta'
import type { SettingsEntry } from './shared'

/** Settings › Mounting and wind (round 13, item 3; docs/audits/round-13/engineer-brief.md 3.4 and 3.5): the pricing config's
 * `mounting` section as its own card. The fastener and the feet; the wind figures of the uplift check, each beside its source;
 * the wind zone and basic wind speed by province, listed from the shipped file (every province, every figure blank) with the
 * typed rows over it. The app ships no wind-code or fastener figure: a blank leaves the check "not checked", and the settings'
 * two defaults (two screws per foot, the rails at the quarter points) are assumptions the sheet labels. */

type Zone = { zone: string; v_kmh: number | null; source: string }
type ExposureRow = { alpha: number | null; zg_m: number | null }
type WindFile = { source: string; fields: string[]; provinces: Record<string, Zone> }

const EXPOSURES: { id: string; words: string }[] = [
  { id: 'B', words: 'towns and suburbs' },
  { id: 'C', words: 'open ground, the lakeshore, the coast' },
  { id: 'D', words: 'flat, unobstructed, facing open water' },
]

export default function MountingSettings({ entry }: { entry: SettingsEntry }) {
  const { cfg, error, setField } = usePricingDraft()
  const rows = useMemo(() => settingsIndex(cfg).filter((r) => r.route === entry.route), [cfg, entry.route])
  useFindTarget(!!cfg, rows)
  const [file, setFile] = useState<WindFile | null>(null)
  const [needle, setNeedle] = useState('')
  useEffect(() => {
    api
      .windZones()
      .then(setFile)
      .catch(() => setFile(null))
  }, [])
  if (!cfg) return <div className="muted">{error ?? 'Loading pricing settings...'}</div>
  const m = (cfg.mounting ?? {}) as Record<string, unknown>
  const set = (key: string, v: unknown) => setField('mounting', key, v)
  const meta = (key: string) => META[`mounting.${key}`]
  const numVal = (key: string) => (typeof m[key] === 'number' ? (m[key] as number) : null)
  const strVal = (key: string) => (typeof m[key] === 'string' ? (m[key] as string) : '')
  const num = (key: string, opts: { allowEmpty?: boolean; placeholder?: string; min?: number; max?: number } = {}) => {
    const d = meta(key)
    return (
      <Field id={fieldId('mounting', key)} label={d?.label ?? key} unit={d?.unit} help={d?.help} about={d?.about}>
        {(id) => (
          <NumberInput id={id} value={numVal(key)} decimals={d?.decimals ?? 2} allowEmpty={opts.allowEmpty} min={opts.min} max={opts.max} placeholder={opts.placeholder} onChange={(v) => set(key, opts.allowEmpty ? v : (v ?? 0))} />
        )}
      </Field>
    )
  }
  const text = (key: string, placeholder?: string) => {
    const d = meta(key)
    return (
      <Field id={fieldId('mounting', key)} label={d?.label ?? key} help={d?.help} about={d?.about} className={d?.wide ? 'wide' : undefined}>
        {(id) => <input id={id} value={strVal(key)} placeholder={placeholder} onChange={(e) => set(key, e.target.value)} />}
      </Field>
    )
  }

  // the exposure constants: B, C, D rows, each alpha and zg
  const exposures = (m.exposures ?? {}) as Record<string, ExposureRow>
  const setExposure = (id: string, patch: Partial<ExposureRow>) => {
    const row: ExposureRow = { alpha: exposures[id]?.alpha ?? null, zg_m: exposures[id]?.zg_m ?? null }
    set('exposures', { ...exposures, [id]: { ...row, ...patch } })
  }

  // the wind zones: the file's provinces (every figure blank) with the typed rows over them; a row with nothing typed is dropped
  const typed = (m.wind_zones ?? {}) as Record<string, Zone>
  const provinces = file ? Object.keys(file.provinces) : Object.keys(typed).sort((a, b) => a.localeCompare(b))
  const setZone = (province: string, patch: Partial<Zone>) => {
    const was = typed[province]
    const row: Zone = { ...{ zone: was?.zone ?? '', v_kmh: was?.v_kmh ?? null, source: was?.source ?? '' }, ...patch }
    const next = { ...typed }
    if (!row.zone.trim() && row.v_kmh == null && !row.source.trim()) delete next[province]
    else next[province] = row
    set('wind_zones', next)
  }
  const q = needle.trim().toLowerCase()
  const shown = provinces.filter((p) => !q || p.toLowerCase().includes(q))
  const nSet = provinces.filter((p) => typed[p]?.v_kmh != null).length
  const zonesMeta = meta('wind_zones')
  const expMeta = meta('exposures')

  return (
    <>
      <div className="setting-block" id="section-mounting" data-testid="setting-mounting">
        <h3>Fastener and feet</h3>
        <div className="lead">
          The screw the L-feet are fixed with and the span the rail maker allows between feet. The uplift check divides each foot's share between the screws and compares it with the maker's allowable withdrawal; blank figures leave it "not checked".
        </div>
        <div className="form-grid">
          {text('fastener_description', 'e.g. 5.5 × 75 mm self-drilling screw, bonded EPDM washer')}
          {num('fastener_pullout_kn', { allowEmpty: true, placeholder: 'not typed', min: 0 })}
          {text('fastener_pullout_source', "e.g. the screw maker's sheet, 1.5 mm steel purlin")}
          {num('screws_per_foot', { min: 1 })}
          {num('foot_spacing_max_m', { allowEmpty: true, placeholder: "the BOQ rule's", min: 0 })}
          {text('foot_spacing_max_source', "e.g. the rail maker's installation manual")}
          {num('rail_position_fraction', { min: 0.01, max: 0.49 })}
          {num('rail_kg_per_m', { allowEmpty: true, placeholder: 'left out', min: 0 })}
        </div>
      </div>
      <div className="setting-block" id="mounting-wind">
        <h3>Wind factors the signing engineer types</h3>
        <div className="lead">
          NSCP 2015 Section 207 (verify every figure): the app ships none of these. Each figure is printed on the mounting detail sheet beside its source. The GCp per roof zone is typed per project, under Roof faces › Wind for the uplift check.
        </div>
        <div className="form-grid">
          {num('kd', { allowEmpty: true, placeholder: 'not typed', min: 0, max: 1 })}
          {text('kd_source', 'e.g. NSCP 2015 Table 207A.6-1')}
          {text('exposure_source', 'e.g. NSCP 2015 Table 207A.9-1')}
        </div>
        <Field id={fieldId('mounting', 'exposures')} label={expMeta?.label ?? 'Exposure categories'} help={expMeta?.help} about={expMeta?.about} className="wide own-line">
          {(id) => (
            <div id={id} className="block">
              <table className="kv sizes" data-testid="exposures-table">
                <thead>
                  <tr>
                    <th>Exposure</th>
                    <th>alpha</th>
                    <th>zg (m)</th>
                  </tr>
                </thead>
                <tbody>
                  {EXPOSURES.map((e) => (
                    <tr key={e.id}>
                      <th scope="row">
                        {e.id} <span className="muted" style={{ fontWeight: 400 }}>{e.words}</span>
                      </th>
                      <td>
                        <NumberInput value={exposures[e.id]?.alpha ?? null} decimals={2} allowEmpty min={0} placeholder="not typed" ariaLabel={`Exposure ${e.id} alpha`} onChange={(v) => setExposure(e.id, { alpha: v })} />
                      </td>
                      <td>
                        <NumberInput value={exposures[e.id]?.zg_m ?? null} decimals={2} allowEmpty min={0} placeholder="not typed" ariaLabel={`Exposure ${e.id} zg`} onChange={(v) => setExposure(e.id, { zg_m: v })} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Field>
      </div>
      <div className="setting-block" id="mounting-zones">
        <h3>{zonesMeta?.label ?? 'Wind zone and basic wind speed by province'}</h3>
        <div className="lead">
          {file?.source ?? 'The province list ships with every figure blank; the signing engineer reads the zone and the speed from NSCP 2015 Figure 207A.5-1A and types them here with the source.'}{' '}
          <b>
            {nSet} of {provinces.length} provinces set.
          </b>
        </div>
        <div className="form-grid">
          <Field label="Find a province" className="wide">
            {(id) => <input id={id} value={needle} onChange={(e) => setNeedle(e.target.value)} placeholder="e.g. Laguna" />}
          </Field>
        </div>
        <Field id={fieldId('mounting', 'wind_zones')} label="Provinces" help={zonesMeta?.help} about={zonesMeta?.about} className="full">
          {(id) => (
            <div id={id} className="block">
              <table className="kv wide" data-testid="wind-zones-table">
                <thead>
                  <tr>
                    <th>Province</th>
                    <th>Zone</th>
                    <th>V (km/h)</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((p) => {
                    const row = typed[p]
                    return (
                      <tr key={p}>
                        <th scope="row">
                          {p} {row?.v_kmh == null && <span className="chip">not set</span>}
                        </th>
                        <td>
                          <input value={row?.zone ?? ''} style={{ maxWidth: 90 }} aria-label={`${p} zone`} placeholder="zone" onChange={(e) => setZone(p, { zone: e.target.value })} />
                        </td>
                        <td>
                          <NumberInput value={row?.v_kmh ?? null} decimals={0} allowEmpty min={0} placeholder="not set" ariaLabel={`${p} basic wind speed`} style={{ maxWidth: 110 }} onChange={(v) => setZone(p, { v_kmh: v })} />
                        </td>
                        <td>
                          <input value={row?.source ?? ''} aria-label={`${p} source`} placeholder="e.g. NSCP 2015 Fig. 207A.5-1A" onChange={(e) => setZone(p, { source: e.target.value })} />
                        </td>
                      </tr>
                    )
                  })}
                  {shown.length === 0 && (
                    <tr>
                      <td colSpan={4} className="muted">
                        No province matches.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Field>
      </div>
      <PricingBar />
    </>
  )
}
