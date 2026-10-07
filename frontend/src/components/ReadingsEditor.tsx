import { newReadingSet, SKY_CONDITIONS, type ReadingSet, type ReadingSetResult, type RoofFace } from '../types'
import NumberInput from './NumberInput'

function fmt(n: number | null | undefined, d = 3) {
  return n == null || !Number.isFinite(n) ? '-' : n.toFixed(d)
}

export default function ReadingsEditor({
  sets,
  faces,
  results,
  selectedIndex,
  onChange,
}: {
  sets: ReadingSet[]
  faces: RoofFace[]
  results: ReadingSetResult[] | null
  selectedIndex: number | null | undefined
  onChange: (s: ReadingSet[]) => void
}) {
  const update = (i: number, patch: Partial<ReadingSet>) => onChange(sets.map((s, j) => (j === i ? { ...s, ...patch } : s)))
  const updateReading = (i: number, r: number, patch: Partial<ReadingSet['readings'][number]>) =>
    update(i, { readings: sets[i].readings.map((x, k) => (k === r ? { ...x, ...patch } : x)) })
  const add = () => onChange([...sets, newReadingSet(faces[0]?.id ?? null)])
  const remove = (i: number) => onChange(sets.filter((_, j) => j !== i))

  return (
    <div>
      {sets.length === 0 && <div className="muted" style={{ marginBottom: 8 }}>No readings yet. Add one set per roof face you measured.</div>}
      {sets.map((s, i) => {
        const r = results && results[i] && results.length === sets.length ? results[i] : null
        return (
          <div className="set-card" key={s.id}>
            <div className="row">
              <div>
                <label>Roof face</label>
                <select value={s.face_id ?? ''} onChange={(e) => update(i, { face_id: e.target.value || null })}>
                  <option value="">Whole site</option>
                  {faces.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label>Label</label>
                <input value={s.label} onChange={(e) => update(i, { label: e.target.value })} placeholder="optional" />
              </div>
              <div>
                <label>Date and time (local)</label>
                <input type="datetime-local" value={s.measured_at ?? ''} onChange={(e) => update(i, { measured_at: e.target.value || null })} />
              </div>
              <div>
                <label>Sky</label>
                <select value={s.sky_condition} onChange={(e) => update(i, { sky_condition: e.target.value })}>
                  {SKY_CONDITIONS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label>Ambient air temp (C, optional)</label>
                <NumberInput value={s.ambient_temp_c} onChange={(v) => update(i, { ambient_temp_c: v })} allowEmpty placeholder="estimate" />
              </div>
              <div className="narrow">
                <button type="button" className="danger" onClick={() => remove(i)}>
                  Remove set
                </button>
              </div>
            </div>
            <div className="table-wrap" style={{ marginTop: 8 }}>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th className="num">Irradiance (W/m2)</th>
                    <th className="num">MPPT power (W)</th>
                    <th className="num">Panel temp (C, probe)</th>
                    {r && <th className="num">k</th>}
                    {r && <th className="num">k site</th>}
                  </tr>
                </thead>
                <tbody>
                  {s.readings.map((rd, k) => (
                    <tr key={k}>
                      <td>{k + 1}</td>
                      <td>
                        <NumberInput value={rd.irradiance_wm2} onChange={(v) => updateReading(i, k, { irradiance_wm2: v ?? 0 })} min={0} />
                      </td>
                      <td>
                        <NumberInput value={rd.power_w} onChange={(v) => updateReading(i, k, { power_w: v ?? 0 })} min={0} />
                      </td>
                      <td>
                        <NumberInput value={rd.module_temp_c} onChange={(v) => updateReading(i, k, { module_temp_c: v ?? 0 })} />
                      </td>
                      {r && <td className="num">{fmt(r.k_raw_values[k])}</td>}
                      {r && <td className="num">{fmt(r.k_site_values[k])}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {r && (
              <div className="muted" style={{ marginTop: 6 }}>
                k = <b>{fmt(r.k_raw)}</b>, site factor k_site = <b>{fmt(r.k_site)}</b>, avg irradiance {fmt(r.avg_irradiance_wm2, 0)} W/m2, panel {fmt(r.avg_module_temp_c, 1)} C,
                ambient {r.ambient_temp_c != null ? `${fmt(r.ambient_temp_c, 1)} C (${r.ambient_source})` : 'n/a'}, rise{' '}
                {r.rise_per_kw != null ? `${fmt(r.rise_per_kw, 1)} C per kW/m2` : 'n/a'}.{' '}
                {selectedIndex === i && <span className="badge good">used for the site</span>} {r.low_confidence && <span className="badge bad">low confidence</span>}
                {r.warnings.length > 0 && (
                  <ul className="warnings">
                    {r.warnings.map((w) => (
                      <li key={w.code}>{w.message}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )
      })}
      <button type="button" onClick={add}>
        Add reading set
      </button>
      <div className="muted" style={{ marginTop: 6 }}>
        Three simultaneous readings per set: irradiance from the UT381PV, MPPT power from the UT673PV+, panel surface temperature from the probe. With several
        sets, the one with the highest site factor is used for the whole site.
      </div>
    </div>
  )
}
