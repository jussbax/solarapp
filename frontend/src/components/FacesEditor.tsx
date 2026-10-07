import { newId, type RoofFace } from '../types'
import { COMPASS, compassLabel } from './compass'
import NumberInput from './NumberInput'

export default function FacesEditor({ faces, onChange }: { faces: RoofFace[]; onChange: (f: RoofFace[]) => void }) {
  const update = (i: number, patch: Partial<RoofFace>) => onChange(faces.map((f, j) => (j === i ? { ...f, ...patch } : f)))
  const add = () =>
    onChange([...faces, { id: newId(), name: `Roof ${faces.length + 1}`, length_m: 10, width_m: 6, tilt_deg: 15, azimuth_deg: 180, panel_count_override: null }])
  const remove = (i: number) => onChange(faces.filter((_, j) => j !== i))

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th className="num">Length (m)</th>
            <th className="num">Width (m)</th>
            <th className="num">Tilt (deg)</th>
            <th>Facing</th>
            <th className="num">Azimuth (deg)</th>
            <th className="num">Panel count override</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {faces.map((f, i) => (
            <tr key={f.id}>
              <td>
                <input value={f.name} onChange={(e) => update(i, { name: e.target.value })} />
              </td>
              <td>
                <NumberInput value={f.length_m} onChange={(v) => update(i, { length_m: v ?? 0 })} min={0} />
              </td>
              <td>
                <NumberInput value={f.width_m} onChange={(v) => update(i, { width_m: v ?? 0 })} min={0} />
              </td>
              <td>
                <NumberInput value={f.tilt_deg} onChange={(v) => update(i, { tilt_deg: v ?? 0 })} min={0} max={90} />
              </td>
              <td>
                <select value={compassLabel(f.azimuth_deg)} onChange={(e) => update(i, { azimuth_deg: COMPASS.find((c) => c.label === e.target.value)!.deg })}>
                  {COMPASS.map((c) => (
                    <option key={c.label} value={c.label}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <NumberInput value={f.azimuth_deg} onChange={(v) => update(i, { azimuth_deg: ((v ?? 0) % 360 + 360) % 360 })} min={0} max={359.9} />
              </td>
              <td>
                <NumberInput value={f.panel_count_override} onChange={(v) => update(i, { panel_count_override: v == null ? null : Math.max(0, Math.round(v)) })} allowEmpty min={0} step={1} placeholder="auto" />
              </td>
              <td>
                <button type="button" className="danger" onClick={() => remove(i)} disabled={faces.length <= 1}>
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 8 }}>
        <button type="button" onClick={add}>
          Add roof face
        </button>
        <span className="muted" style={{ marginLeft: 10 }}>
          Azimuth: 0 = north, 90 = east, 180 = south, 270 = west. Tilt 0 = flat.
        </span>
      </div>
    </div>
  )
}
