import { newId, type CandidatePanel, type PanelResult } from '../types'
import NumberInput from './NumberInput'

export default function PanelsEditor({
  panels,
  selectedId,
  results,
  onChange,
  onSelect,
}: {
  panels: CandidatePanel[]
  selectedId: string | null
  results: PanelResult[] | null
  onChange: (p: CandidatePanel[]) => void
  onSelect: (id: string) => void
}) {
  const update = (i: number, patch: Partial<CandidatePanel>) => onChange(panels.map((p, j) => (j === i ? { ...p, ...patch } : p)))
  const add = () => onChange([...panels, { id: newId(), name: '', watt_peak: 550, length_m: 2.278, width_m: 1.134 }])
  const remove = (i: number) => onChange(panels.filter((_, j) => j !== i))
  const resultFor = (id: string) => results?.find((r) => r.panel.id === id)
  const best = results?.find((r) => r.best)

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Use</th>
            <th>Model / name</th>
            <th className="num">Wp</th>
            <th className="num">Length (m)</th>
            <th className="num">Width (m)</th>
            <th className="num">Fits</th>
            <th className="num">kWp</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {panels.map((p, i) => {
            const r = resultFor(p.id)
            return (
              <tr key={p.id}>
                <td>
                  <input type="radio" name="selected-panel" checked={selectedId === p.id} onChange={() => onSelect(p.id)} style={{ width: 'auto' }} />
                </td>
                <td>
                  <input value={p.name} onChange={(e) => update(i, { name: e.target.value })} placeholder="e.g. Canadian 550W" />
                </td>
                <td>
                  <NumberInput value={p.watt_peak} onChange={(v) => update(i, { watt_peak: v ?? 0 })} min={1} />
                </td>
                <td>
                  <NumberInput value={p.length_m} onChange={(v) => update(i, { length_m: v ?? 0 })} min={0.1} step={0.001} />
                </td>
                <td>
                  <NumberInput value={p.width_m} onChange={(v) => update(i, { width_m: v ?? 0 })} min={0.1} step={0.001} />
                </td>
                <td className="num">{r ? r.total_count : '-'}</td>
                <td className="num">
                  {r ? r.system_kwp.toFixed(2) : '-'} {r?.best && <span className="badge good">most kWp</span>}
                </td>
                <td>
                  <button type="button" className="danger" onClick={() => remove(i)} disabled={panels.length <= 1}>
                    Remove
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {best && (
        <div className="banner info" style={{ marginTop: 8 }}>
          Most kWp: <b>{best.panel.name || 'panel'}</b>, {best.total_count} panels x {best.panel.watt_peak} W = <b>{best.system_kwp.toFixed(2)} kWp</b>
          {selectedId && selectedId !== best.panel.id && ' (a different panel is ticked under Use)'}
        </div>
      )}
      <div style={{ marginTop: 8 }}>
        <button type="button" onClick={add}>
          Add candidate panel
        </button>
        <span className="muted" style={{ marginLeft: 10 }}>
          Leave "Use" unticked to use the panel with the most kWp.
        </span>
      </div>
    </div>
  )
}
