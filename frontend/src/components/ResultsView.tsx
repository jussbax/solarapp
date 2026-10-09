import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { AssessmentDoc, Results } from '../types'
import { compassLabel } from './compass'
import { fmtDateTime, n0, plural } from '../fmt'
import { PlanDrawing } from './PlanDrawing'
import MonthTable, { type MonthRow } from './MonthTable'
import { useNarrow } from './responsive'

const n1 = (v: number) => v.toFixed(1)
const n2 = (v: number) => v.toFixed(2)
const n3 = (v: number) => v.toFixed(3)
const pct = (v: number | null | undefined) => (v == null ? '-' : `${v > 0 ? '+' : ''}${v.toFixed(1)}%`)

/** Roof and production: the production figures (at the panels beside at the meter), one plan drawing per face that
 * holds panels with the sized system's panels highlighted, the month table, and the internal details. */
export default function ResultsView({ doc, results }: { doc: AssessmentDoc; results: Results }) {
  const narrow = useNarrow()
  const prod = results.production
  const ref = results.reference
  const selected = results.panels.find((p) => p.panel.id === results.selected_panel_id)
  const dev = results.comparison.deviation_pct
  const chart = results.months.map((m, i) => ({ month: m, 'This roof': Math.round(prod.monthly_kwh[i]), 'PVGIS reference': Math.round(ref.monthly_kwh[i]) }))
  const k = results.k
  const best = results.best_panel
  const geometry = (results.geometry ?? []).filter((g) => (g.panels ?? []).length > 0)
  const sized = geometry.some((g) => g.used != null)
  const lossPct = Math.round((1 - (prod.loss_factor ?? 1)) * 100)
  if (!selected) return <div className="banner warn">The selected panel is no longer in the list. Press Calculate again.</div>

  const monthRows: MonthRow[] = [
    ...prod.faces.map((f) => ({
      key: f.face_id,
      label: `${f.name} (${plural(f.panel_count, 'panel')}, ${f.tilt_deg}° ${compassLabel(f.azimuth_deg)})`,
      short: f.name,
      values: f.monthly_kwh.map(n0),
      total: n0(f.annual_kwh),
    })),
    { key: 'total', label: 'Total kWh at the panels', short: 'Total', values: prod.monthly_kwh.map(n0), total: n0(prod.annual_kwh), bold: true },
    ...(prod.monthly_kwh_ac ? [{ key: 'ac', label: 'At the meter kWh', short: 'Meter', values: prod.monthly_kwh_ac.map(n0), total: n0(prod.annual_kwh_ac ?? 0) }] : []),
    { key: 'ref', label: 'PVGIS reference kWh', short: 'PVGIS', values: ref.monthly_kwh.map(n0), total: n0(ref.annual_kwh), muted: true },
    { key: 'diff', label: 'Difference', short: 'Diff.', values: results.comparison.monthly_deviation_pct.map(pct), total: pct(dev), muted: true, phoneHide: true },
    ...prod.faces.map((f) => ({
      key: f.face_id + '-psh',
      label: `${f.name}: in-plane sun hours per day`,
      short: `${f.name} h/day`,
      values: f.psh_per_day.map(n2),
      total: n2(f.avg_psh_per_day),
      muted: true,
      phoneHide: true,
    })),
    { key: 'days', label: 'Days', short: 'Days', values: prod.days_in_month.map(String), total: String(prod.days_in_month.reduce((a, b) => a + b, 0)), muted: true, phoneHide: true },
  ]

  return (
    <div>
      {results.warnings.map((w, i) => (
        <div key={w.code + (w.face_id ?? '') + i} className={`banner ${w.code === 'synthetic_data' || w.hard ? 'bad' : 'warn'}`}>
          {w.message}
        </div>
      ))}

      <div className="kpis">
        <div className="kpi">
          <div className="label">Panels the roof holds</div>
          <div className="value">{prod.total_panels}</div>
          <div className="sub">
            {selected.panel.name || 'panel'} {selected.panel.watt_peak} W
            {selected.panel.id !== best.id && (
              <>
                <br />
                Most kWp: {best.name || 'panel'} x {best.count} = {n2(best.system_kwp)} kWp
              </>
            )}
          </div>
        </div>
        <div className="kpi">
          <div className="label">Full-roof size</div>
          <div className="value">{n2(prod.system_kwp)} kWp</div>
          <div className="sub">
            average month {n0(prod.avg_monthly_kwh)} kWh at the panels; low {n0(Math.min(...prod.monthly_kwh))}, high {n0(Math.max(...prod.monthly_kwh))}
          </div>
        </div>
        <div className="kpi">
          <div className="label">Measured vs PVGIS</div>
          <div className="value">
            <span className={`badge ${Math.abs(dev) < 10 ? 'good' : 'bad'}`} style={{ fontSize: 18 }}>
              {pct(dev)}
            </span>
          </div>
          <div className="sub">Same roof, standard model: {n0(ref.annual_kwh)} kWh/yr</div>
        </div>
      </div>
      {/* the two production figures side by side, on the phone too: what the panels make and what reaches the meter */}
      <div className="kpis kpi-pair" aria-label="Production per year">
        <div className="kpi">
          <div className="label">Per year, at the panels</div>
          <div className="value">{n0(prod.annual_kwh)} kWh</div>
          <div className="sub">
            {n0(prod.faces.reduce((a, f) => a + f.specific_yield_kwh_per_kwp * f.panel_count, 0) / Math.max(prod.total_panels, 1))} kWh per kWp, before any losses
          </div>
        </div>
        <div className="kpi">
          <div className="label">Per year, at the meter</div>
          <div className="value">{n0(prod.annual_kwh_ac ?? prod.annual_kwh)} kWh</div>
          <div className="sub">
            after inverter, wiring, soiling and other losses ({lossPct}% in all); {n0(prod.avg_monthly_kwh_ac ?? prod.avg_monthly_kwh)} kWh an average month. The figure on the customer documents.
          </div>
        </div>
      </div>

      {geometry.length > 0 && (
        <>
          <h3>Plan of each face</h3>
          <div className="muted" style={{ marginBottom: 6 }}>
            Panels numbered from the eave up.{' '}
            {sized
              ? 'Solid panels are the ones the sized system uses (best face first); dashed positions are the rest of what the roof can hold.'
              : 'Every position the roof can hold; the sized system is marked once the energy audit is calculated.'}
          </div>
          <div className="plans">
            {geometry.map((g) => (
              <div key={g.face_id} className="plan" data-testid="plan-drawing">
                <div className="plan-title">
                  <b>{g.name}</b>{' '}
                  <span className="muted">
                    {g.used != null ? `${g.used} of ${g.count} positions used` : `${plural(g.count, 'panel')} fit`}
                    {g.left_out > 0 && `, ${g.left_out} left out for vents`} · {n1(g.eave_m)} × {n1(g.slope_m)} m
                  </span>
                </div>
                <PlanDrawing face={g} selected={g.used} width={narrow ? 344 : 440} />
              </div>
            ))}
          </div>
        </>
      )}

      <h3>Monthly production, kWh at the panels</h3>
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={chart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e3e8e8" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="This roof" fill="#C9A227" radius={[4, 4, 0, 0]} />
            <Bar dataKey="PVGIS reference" fill="#2f5fd8" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <MonthTable months={results.months} rows={monthRows} />

      <div className="muted" style={{ marginTop: 8 }}>
        Current formula for comparison ({results.legacy_method.formula}): <b>{n0(results.legacy_method.monthly_kwh)} kWh per month</b>,{' '}
        {n0(results.legacy_method.annual_kwh)} kWh per year.
      </div>

      <details className="internal" style={{ marginTop: 16 }}>
        <summary>Internal details (not on customer documents)</summary>
        <h3>Site factor</h3>
        <table className="kv wide">
          <tbody>
            <tr>
              <th>Owner's k (average of rows)</th>
              <td>{n3(k.k_raw)}</td>
            </tr>
            <tr>
              <th>Site k (heat and low-light removed)</th>
              <td>{n3(k.k_site)}</td>
            </tr>
            <tr>
              <th>Thermal model</th>
              <td>{k.thermal}</td>
            </tr>
            {k.selected_set_index != null && (
              <tr>
                <th>Reading set used</th>
                <td>{k.sets[k.selected_set_index]?.label || `set ${k.selected_set_index + 1}`} (highest k_site)</td>
              </tr>
            )}
          </tbody>
        </table>
        <div className="muted" style={{ marginTop: 6 }}>
          {results.comparison.description}
        </div>

        <h3>Panel layout</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Face</th>
                <th>Shape and usable (m)</th>
                <th className="num">Portrait</th>
                <th className="num">Landscape</th>
                <th>Rows from the eave</th>
                <th className="num">Used</th>
                <th>Shade</th>
              </tr>
            </thead>
            <tbody>
              {doc.faces.map((f) => {
                const l = selected.faces[f.id]
                if (!l) return null
                const p = (l.options ?? []).find((o) => o.orientation === 'portrait')
                const q = (l.options ?? []).find((o) => o.orientation === 'landscape')
                const sh = results.shade?.[f.id]
                const cuts = l.cuts ? (['eave', 'ridge', 'left', 'right'] as const).filter((e) => l.cuts[e] > 0).map((e) => `${e} ${n1(l.cuts[e])} m`) : []
                return (
                  <tr key={f.id}>
                    <td>{f.name}</td>
                    <td>
                      {l.shape === 'hip' ? 'hip face' : l.shape === 'tri' ? 'triangle' : 'rectangle'}, {n1(l.usable_length_m ?? 0)} × {n1(l.usable_width_m ?? 0)}
                    </td>
                    <td className="num">{p?.count ?? '-'}</td>
                    <td className="num">{q?.count ?? '-'}</td>
                    <td>
                      {l.best?.rows ? l.best.rows.join(', ') || '0' : '-'} ({l.best?.orientation ?? '-'}){(l.left_out ?? 0) > 0 && `, ${l.left_out} left out`}
                    </td>
                    <td className="num">
                      {l.count} {l.override_applied && <span className="badge neutral">override</span>}
                    </td>
                    <td className="muted">
                      {cuts.length > 0 && `strip: ${cuts.join(', ')}. `}
                      {(sh?.obstacles ?? []).map((o) => `${o.label || 'obstruction'} ${compassLabel(o.direction_deg)} ${o.elevation_deg}°: ${o.cls === 'clear' ? 'no effect' : o.cls === 'small' ? 'small loss' : 'main-hours shade'}`).join('; ')}
                      {sh?.shade_loss_pct != null && sh.shade_loss_pct >= 0.5 && ` Shade takes ${sh.shade_loss_pct.toFixed(0)}% of the direct sun.`}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <h3>Weather data</h3>
        <div className="muted">
          PVGIS cell {results.dataset.id} ({results.dataset.radiation_db}), {results.dataset.distance_km} km from the pin, elevation {n0(results.dataset.elevation_m)} m.
          Horizontal sun hours per day from PVGIS: {prod.ghi_psh_per_day.map((v) => n2(v)).join(', ')} (annual average {n2(prod.annual_ghi_kwh_m2 / 365)}).
        </div>
        {results.nasa_reference && (
          <>
            <h3>NASA POWER reference (not used in results)</h3>
            <MonthTable
              months={results.months}
              firstHeader="Horizontal sun hours/day"
              rows={[
                { key: 'pvgis', label: 'PVGIS', values: results.nasa_reference.pvgis_ghi_psh.map(n2), total: n2(results.nasa_reference.pvgis_annual_psh) },
                {
                  key: 'nasa',
                  label: 'NASA POWER',
                  values: results.nasa_reference.nasa_ghi_psh.map((v) => (v == null ? '-' : n2(v))),
                  total: results.nasa_reference.nasa_annual_psh == null ? '-' : n2(results.nasa_reference.nasa_annual_psh),
                },
                { key: 'diff', label: 'NASA vs PVGIS', short: 'Diff.', values: results.nasa_reference.monthly_diff_pct.map(pct), total: pct(results.nasa_reference.annual_diff_pct), muted: true },
              ]}
            />
            <div className="muted">
              NASA point {results.nasa_reference.point.distance_km} km from the pin. A large gap means the two datasets disagree about this area's weather.
            </div>
          </>
        )}
        <div className="muted" style={{ marginTop: 8 }}>
          Computed {fmtDateTime(results.computed_at)}.
        </div>
      </details>
    </div>
  )
}
