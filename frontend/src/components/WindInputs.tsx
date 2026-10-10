import Field from './Field'
import NumberInput from './NumberInput'
import type { Exposure, WindInputs } from '../types'

/** The project's wind figures for the uplift check (round 13, item 3; brief 3.5), typed by the signing engineer with their
 * sources: a fold under the Roof faces card. The app ships none: the basic wind speed falls back to the province's row under
 * Settings › Mounting and wind, exposure B and Kzt 1.0 are labelled assumptions when blank, and the GCp per roof zone has no
 * default at all, so the check reads "not checked" until it is typed. */
const EXPOSURES: { id: Exposure; label: string }[] = [
  { id: 'B', label: 'B: towns and suburbs' },
  { id: 'C', label: 'C: open ground, the lakeshore, the coast' },
  { id: 'D', label: 'D: flat and unobstructed, facing open water' },
]

export function WindInputsFields({ value, onChange }: { value: WindInputs; onChange: (v: WindInputs) => void }) {
  const set = (key: keyof WindInputs, v: string | number | null) => onChange({ ...value, [key]: v } as WindInputs)
  const num = (label: string, key: 'v_kmh' | 'kzt' | 'gcp_zone1' | 'gcp_zone2' | 'gcp_zone3', unit: string, placeholder: string, help?: string) => (
    <Field label={label} unit={unit} help={help} id={`wind-${key}`}>
      {(id) => <NumberInput id={id} value={value[key]} onChange={(v) => set(key, v)} allowEmpty step={0.01} placeholder={placeholder} />}
    </Field>
  )
  const text = (label: string, key: 'zone' | 'v_source' | 'kzt_source' | 'gcp_source', placeholder: string, className?: string) => (
    <Field label={label} id={`wind-${key}`} className={className}>
      {(id) => <input id={id} value={value[key]} onChange={(e) => set(key, e.target.value)} placeholder={placeholder} />}
    </Field>
  )
  return (
    <div className="form-grid face-grid" data-testid="wind-inputs">
      {text('Wind zone', 'zone', "e.g. II (the province's row)")}
      {num('Basic wind speed V', 'v_kmh', 'km/h', "the province's row", '3-s gust at 10 m, Occupancy II')}
      {text('V: source', 'v_source', 'e.g. NSCP 2015 Fig. 207A.5-1A')}
      <Field label="Exposure" id="wind-exposure" help="Blank = B, an assumption">
        {(id) => (
          <select id={id} value={value.exposure} onChange={(e) => set('exposure', e.target.value)}>
            <option value="">assumption: B</option>
            {EXPOSURES.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
        )}
      </Field>
      {num('Kzt (topography)', 'kzt', '×', 'assumption: 1.0', 'A hill or ridge: the PEE types it')}
      {text('Kzt: source', 'kzt_source', 'e.g. NSCP 2015 207A.8')}
      {num('GCp, zone 1 (interior)', 'gcp_zone1', '', 'not typed', 'Negative for uplift')}
      {num('GCp, zone 2 (edge)', 'gcp_zone2', '', 'not typed')}
      {num('GCp, zone 3 (corner)', 'gcp_zone3', '', 'not typed', 'The worst typed zone is applied to every panel')}
      {text('GCp: source', 'gcp_source', 'e.g. NSCP 2015 Fig. 207E.4-2A, the roof pitch', 'wide')}
    </div>
  )
}
