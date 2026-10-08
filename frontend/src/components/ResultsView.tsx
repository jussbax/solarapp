import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { AssessmentDoc, Results } from '../types'
import { compassLabel } from './compass'

const n0 = (v: number) => Math.round(v).toLocaleString()
const n1 = (v: number) => v.toFixed(1)
const n2 = (v: number) => v.toFixed(2)
const n3 = (v: number) => v.toFixed(3)
const pct = (v: number | null | undefined) => (v == null ? '-' : `${v > 0 ? '+' : ''}${v.toFixed(1)}%`)

export default function ResultsView({ doc, results, stale }: { doc: AssessmentDoc; results: Results; stale: boolean }) {
  const prod = results.production
  const ref = results.reference
  const selected = results.panels.find((p) => p.panel.id === results.selected_panel_id)!
  const dev = results.comparison.deviation_pct
  const chart = results.months.map((m, i) => ({ month: m, 'This roof': Math.round(prod.monthly_kwh[i]), 'PVGIS reference': Math.round(ref.monthly_kwh[i]) }))
  const k = results.k
  const best = results.best_panel

  return (
    <div>
      {stale && <div className="banner warn">Inputs were edited after this calculation. Save and compute again to refresh.</div>}
      {results.warnings.map((w) => (
        <div key={w.code} className={`banner ${w.code === 'synthetic_data' ? 'bad' : 'warn'}`}>
          {w.message}
        </div>
      ))}

      <div className="kpis">
        <div className="kpi">
          <div className="label">Panels</div>
          <div className="value">{prod.total_panels}</div>
          <div className="sub">
            {selected.panel.name || 'panel'} {selected.panel.watt_peak} W
            {selected.panel.id !== best.id && (
              <>
                <br />
                most kWp: {best.name || 'panel'} x {best.count} = {n2(best.system_kwp)} kWp
              </>
            )}
          </div>
        </div>
        <div className="kpi">
          <div className="label">System size</div>
          <div className="value">{n2(prod.system_kwp)} kWp</div>
        </div>
        <div className="kpi">
          <div className="label">Per year</div>
          <div className="value">{n0(prod.annual_kwh)} kWh</div>
          <div className="sub">{n0(prod.faces.reduce((a, f) => a + f.specific_yield_kwh_per_kwp * f.panel_count, 0) / Math.max(prod.total_panels, 1))} kWh per kWp</div>
        </div>
        <div className="kpi">
          <div className="label">Average month</div>
          <div className="value">{n0(prod.avg_monthly_kwh)} kWh</div>
          <div className="sub">
            low {n0(Math.min(...prod.monthly_kwh))}, high {n0(Math.max(...prod.monthly_kwh))}
          </div>
        </div>
        <div className="kpi">
          <div className="label">Measured vs PVGIS</div>
          <div className="value">
            <span className={`badge ${Math.abs(dev) < 10 ? 'good' : 'bad'}`} style={{ fontSize: 18 }}>
              {pct(dev)}
            </span>
          </div>
          <div className="sub">PVGIS-style roof: {n0(ref.annual_kwh)} kWh/yr</div>
        </div>
      </div>

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

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Month</th>
              {results.months.map((m) => (
                <th key={m} className="num">
                  {m}
                </th>
              ))}
              <th className="num">Year</th>
            </tr>
          </thead>
          <tbody>
            {prod.faces.map((f) => (
              <tr key={f.face_id}>
                <td>
                  {f.name} ({f.panel_count} panels, {f.tilt_deg}° {compassLabel(f.azimuth_deg)})
                </td>
                {f.monthly_kwh.map((v, i) => (
                  <td key={i} className="num">
                    {n0(v)}
                  </td>
                ))}
                <td className="num">{n0(f.annual_kwh)}</td>
              </tr>
            ))}
            <tr style={{ fontWeight: 600 }}>
              <td>Total kWh</td>
              {prod.monthly_kwh.map((v, i) => (
                <td key={i} className="num">
                  {n0(v)}
                </td>
              ))}
              <td className="num">{n0(prod.annual_kwh)}</td>
            </tr>
            <tr className="muted">
              <td>PVGIS reference kWh</td>
              {ref.monthly_kwh.map((v, i) => (
                <td key={i} className="num">
                  {n0(v)}
                </td>
              ))}
              <td className="num">{n0(ref.annual_kwh)}</td>
            </tr>
            <tr className="muted">
              <td>Difference</td>
              {results.comparison.monthly_deviation_pct.map((v, i) => (
                <td key={i} className="num">
                  {pct(v)}
                </td>
              ))}
              <td className="num">{pct(dev)}</td>
            </tr>
            {prod.faces.map((f) => (
              <tr key={f.face_id + '-psh'} className="muted">
                <td>{f.name}: in-plane sun hours per day</td>
                {f.psh_per_day.map((v, i) => (
                  <td key={i} className="num">
                    {n2(v)}
                  </td>
                ))}
                <td className="num">{n2(f.avg_psh_per_day)}</td>
              </tr>
            ))}
            <tr className="muted">
              <td>Days</td>
              {prod.days_in_month.map((v, i) => (
                <td key={i} className="num">
                  {v}
                </td>
              ))}
              <td className="num">{prod.days_in_month.reduce((a, b) => a + b, 0)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="muted" style={{ marginTop: 8 }}>
        Current formula for comparison ({results.legacy_method.formula}): <b>{n0(results.legacy_method.monthly_kwh)} kWh per month</b>,{' '}
        {n0(results.legacy_method.annual_kwh)} kWh per year.
      </div>

      <details className="internal" style={{ marginTop: 16 }}>
        <summary>Internal details (not on the customer PDF)</summary>
        <h3>Site factor</h3>
        <table>
          <tbody>
            <tr>
              <th>k (owner's formula, average of rows)</th>
              <td>{n3(k.k_raw)}</td>
            </tr>
            <tr>
              <th>k_site (heat and low-light removed)</th>
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
        <table>
          <thead>
            <tr>
              <th>Face</th>
              <th>Usable (m)</th>
              <th className="num">Portrait</th>
              <th className="num">Landscape</th>
              <th className="num">Used</th>
            </tr>
          </thead>
          <tbody>
            {doc.faces.map((f) => {
              const l = selected.faces[f.id]
              if (!l) return null
              const p = l.options.find((o) => o.orientation === 'portrait')!
              const q = l.options.find((o) => o.orientation === 'landscape')!
              return (
                <tr key={f.id}>
                  <td>{f.name}</td>
                  <td>
                    {n1(l.usable_length_m)} x {n1(l.usable_width_m)}
                  </td>
                  <td className="num">
                    {p.count} ({p.along_length} x {p.along_width})
                  </td>
                  <td className="num">
                    {q.count} ({q.along_length} x {q.along_width})
                  </td>
                  <td className="num">
                    {l.count} {l.override_applied && <span className="badge neutral">override</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        <h3>Weather data</h3>
        <div className="muted">
          PVGIS cell {results.dataset.id} ({results.dataset.radiation_db}), {results.dataset.distance_km} km from the pin, elevation {n0(results.dataset.elevation_m)} m.
          Horizontal sun hours per day from PVGIS: {prod.ghi_psh_per_day.map((v) => n2(v)).join(', ')} (annual average {n2(prod.annual_ghi_kwh_m2 / 365)}).
        </div>
        {results.nasa_reference && (
          <>
            <h3>NASA POWER reference (not used in results)</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Horizontal sun hours/day</th>
                    {results.months.map((m) => (
                      <th key={m} className="num">
                        {m}
                      </th>
                    ))}
                    <th className="num">Avg</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>PVGIS</td>
                    {results.nasa_reference.pvgis_ghi_psh.map((v, i) => (
                      <td key={i} className="num">
                        {n2(v)}
                      </td>
                    ))}
                    <td className="num">{n2(results.nasa_reference.pvgis_annual_psh)}</td>
                  </tr>
                  <tr>
                    <td>NASA POWER</td>
                    {results.nasa_reference.nasa_ghi_psh.map((v, i) => (
                      <td key={i} className="num">
                        {v == null ? '-' : n2(v)}
                      </td>
                    ))}
                    <td className="num">{results.nasa_reference.nasa_annual_psh == null ? '-' : n2(results.nasa_reference.nasa_annual_psh)}</td>
                  </tr>
                  <tr className="muted">
                    <td>NASA vs PVGIS</td>
                    {results.nasa_reference.monthly_diff_pct.map((v, i) => (
                      <td key={i} className="num">
                        {pct(v)}
                      </td>
                    ))}
                    <td className="num">{pct(results.nasa_reference.annual_diff_pct)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="muted">
              NASA point {results.nasa_reference.point.distance_km} km from the pin. A large gap means the two datasets disagree about this area's weather.
            </div>
          </>
        )}
        <div className="muted" style={{ marginTop: 8 }}>
          Computed {new Date(results.computed_at).toLocaleString()}.
        </div>
      </details>
    </div>
  )
}
