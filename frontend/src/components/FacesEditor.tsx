import { newFace, newId, type FaceShape, type RoofFace, type ShadeObstacle, type WallEdge, type WallObstacle, type Warning } from '../types'
import { COMPASS, compassLabel } from './compass'
import NumberInput from './NumberInput'

const SHAPES: { id: FaceShape; label: string }[] = [
  { id: 'rect', label: 'Rectangle' }, { id: 'hip', label: 'Hip face' }, { id: 'tri', label: 'Triangle' },
]
const EDGES: { id: WallEdge; label: string }[] = [
  { id: 'eave', label: 'Eave side' }, { id: 'ridge', label: 'Ridge side' }, { id: 'left', label: 'Left end' }, { id: 'right', label: 'Right end' },
]

export default function FacesEditor({ faces, warnings, onChange }: { faces: RoofFace[]; warnings?: Warning[] | null; onChange: (f: RoofFace[]) => void }) {
  const update = (i: number, patch: Partial<RoofFace>) => onChange(faces.map((f, j) => (j === i ? { ...f, ...patch } : f)))
  const add = () => onChange([...faces, newFace(`Roof ${faces.length + 1}`)])
  const remove = (i: number) => onChange(faces.filter((_, j) => j !== i))
  const setWall = (i: number, k: number, patch: Partial<WallObstacle>) => update(i, { walls: faces[i].walls.map((w, m) => (m === k ? { ...w, ...patch } : w)) })
  const setTree = (i: number, k: number, patch: Partial<ShadeObstacle>) => update(i, { obstacles: faces[i].obstacles.map((t, m) => (m === k ? { ...t, ...patch } : t)) })

  return (
    <div>
      {faces.map((f, i) => (
        <div key={f.id} className="set-card">
          <div className="card-head">
            <b>{f.name || `Roof ${i + 1}`}</b>
            <button type="button" className="toggle link danger" onClick={() => remove(i)} disabled={faces.length <= 1}>
              Remove face
            </button>
          </div>
          <div className="face-grid">
            <div>
              <label>Name</label>
              <input value={f.name} onChange={(e) => update(i, { name: e.target.value })} />
            </div>
            <div>
              <label>Shape</label>
              <select value={f.shape} onChange={(e) => update(i, { shape: e.target.value as FaceShape })}>
                {SHAPES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Eave length (m)</label>
              <NumberInput value={f.length_m} onChange={(v) => update(i, { length_m: v ?? 0 })} min={0} step={0.1} />
            </div>
            {f.shape === 'hip' && (
              <div>
                <label>Ridge length (m)</label>
                <NumberInput value={f.ridge_m} onChange={(v) => update(i, { ridge_m: v })} allowEmpty min={0} step={0.1} placeholder="top edge" />
              </div>
            )}
            <div>
              <label>Slope length (m)</label>
              <NumberInput value={f.width_m} onChange={(v) => update(i, { width_m: v ?? 0 })} min={0} step={0.1} />
            </div>
            <div>
              <label>Tilt (°)</label>
              <NumberInput value={f.tilt_deg} onChange={(v) => update(i, { tilt_deg: v ?? 0 })} min={0} max={90} />
            </div>
            <div>
              <label>Facing</label>
              <select value={compassLabel(f.azimuth_deg)} onChange={(e) => update(i, { azimuth_deg: COMPASS.find((c) => c.label === e.target.value)!.deg })}>
                {COMPASS.map((c) => (
                  <option key={c.label} value={c.label}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Facing (°)</label>
              <NumberInput value={f.azimuth_deg} onChange={(v) => update(i, { azimuth_deg: (((v ?? 0) % 360) + 360) % 360 })} min={0} max={359.9} />
            </div>
          </div>
          {(warnings ?? [])
            .filter((w) => w.face_id === f.id)
            .map((w, k) => (
              <div key={w.code + k} className="banner warn face-warn" role="alert">
                {w.message}
              </div>
            ))}
          <details className="more">
            <summary>More: panels left out, count override</summary>
            <div className="face-grid" style={{ marginTop: 6 }}>
              <div>
                <label>Panels left out</label>
                <NumberInput value={f.panels_left_out} onChange={(v) => update(i, { panels_left_out: Math.max(0, Math.round(v ?? 0)) })} min={0} step={1} />
              </div>
              <div>
                <label>Panel count (override)</label>
                <NumberInput value={f.panel_count_override} onChange={(v) => update(i, { panel_count_override: v == null ? null : Math.max(0, Math.round(v)) })} allowEmpty min={0} step={1} placeholder="auto" />
              </div>
            </div>
          </details>
          <div className="muted" style={{ marginTop: 4 }}>
            {f.shape === 'rect' && 'Eave along the bottom edge, slope from eave to ridge.'}
            {f.shape === 'hip' && 'A hip face narrows toward the ridge: give the bottom edge, the top edge and the slope between them.'}
            {f.shape === 'tri' && 'A triangle comes to a point at the top: give the bottom edge and the slope to the peak.'}
            {' '}Panels left out: vents, tanks and areas you walked and would not use.
          </div>

          <div className="row" style={{ marginTop: 8, alignItems: 'center' }}>
            <div className="narrow">
              <b style={{ fontSize: 13 }}>Shade on this face</b>
            </div>
            <div className="narrow inline">
              <button type="button" className="small" onClick={() => update(i, { walls: [...f.walls, { id: newId(), edge: 'left', height_m: 1.5, gap_m: 0 }] })}>
                Add firewall or long wall
              </button>
              <button type="button" className="small" onClick={() => update(i, { obstacles: [...f.obstacles, { id: newId(), label: '', direction_deg: 270, elevation_deg: 20, width_deg: 40, share: 1 }] })}>
                Add tree or building
              </button>
            </div>
          </div>
          {f.walls.map((w, k) => (
            <div key={w.id} className="row" style={{ marginTop: 6 }}>
              <div className="narrow" style={{ width: 140 }}>
                <label>Wall on the</label>
                <select value={w.edge} onChange={(e) => setWall(i, k, { edge: e.target.value as WallEdge })}>
                  {EDGES.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="narrow" style={{ width: 150 }}>
                <label>Height above roof (m)</label>
                <NumberInput value={w.height_m} onChange={(v) => setWall(i, k, { height_m: v ?? 0 })} min={0} step={0.1} />
              </div>
              <div className="narrow" style={{ width: 140 }}>
                <label>Gap to roof edge (m)</label>
                <NumberInput value={w.gap_m} onChange={(v) => setWall(i, k, { gap_m: v ?? 0 })} min={0} step={0.1} />
              </div>
              <div className="narrow inline" style={{ paddingBottom: 4 }}>
                <button type="button" className="toggle link" onClick={() => update(i, { walls: f.walls.filter((_, m) => m !== k) })}>
                  remove
                </button>
              </div>
              <div className="hint">Left and right as you face the roof from the ground.</div>
            </div>
          ))}
          {f.obstacles.map((t, k) => (
            <div key={t.id} className="row" style={{ marginTop: 6 }}>
              <div className="narrow" style={{ width: 180 }}>
                <label>Obstacle</label>
                <input value={t.label} placeholder="Mango tree, neighbor's house" onChange={(e) => setTree(i, k, { label: e.target.value })} />
              </div>
              <div className="narrow" style={{ width: 110 }}>
                <label>Direction (°)</label>
                <NumberInput value={t.direction_deg} onChange={(v) => setTree(i, k, { direction_deg: (((v ?? 0) % 360) + 360) % 360 })} min={0} max={359.9} />
              </div>
              <div className="narrow" style={{ width: 130 }}>
                <label>Angle to top (°)</label>
                <NumberInput value={t.elevation_deg} onChange={(v) => setTree(i, k, { elevation_deg: v ?? 0 })} min={0} max={89} />
              </div>
              <div className="narrow" style={{ width: 120 }}>
                <label>Width (°)</label>
                <NumberInput value={t.width_deg} onChange={(v) => setTree(i, k, { width_deg: v ?? 40 })} min={1} max={180} step={5} />
              </div>
              <div className="narrow inline" style={{ paddingBottom: 4 }}>
                <button type="button" className="toggle link" onClick={() => update(i, { obstacles: f.obstacles.filter((_, m) => m !== k) })}>
                  remove
                </button>
              </div>
              <div className="hint">Angle read with a clinometer from panel height, a hand's width above the roof sheet.</div>
            </div>
          ))}
        </div>
      ))}
      <div style={{ marginTop: 8 }}>
        <button type="button" onClick={add}>
          Add roof face
        </button>
        <div className="hint" style={{ marginTop: 6 }}>
          Facing: 0 = north, 90 = east, 180 = south, 270 = west. Tilt 0 = flat. Walls cut a no-panel strip; walls and trees also shade the simulation hour by hour.
        </div>
      </div>
    </div>
  )
}
