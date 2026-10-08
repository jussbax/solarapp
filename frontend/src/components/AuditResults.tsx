import { useState } from 'react'
import { Area, Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { AuditBlock, SizingBlock } from '../types'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const n0 = (v: number) => Math.round(v).toLocaleString()
const n1 = (v: number) => v.toFixed(1)
const n2 = (v: number) => v.toFixed(2)
const pct = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(0)}%`
const KIND_LABEL: Record<string, string> = { off_grid: 'Off-grid (battery, no grid)', net_metering: 'Net metering (no battery)', combination: 'Net metering + battery (hybrid)' }

export default function AuditResults({ audit, sizing, panelName, panelWp }: { audit: AuditBlock; sizing: SizingBlock | null; panelName: string; panelWp: number }) {
  const avb = audit.audit_vs_bill
  const billMonth = avb?.bills[0] ? parseInt(avb.bills[0].billing_month.split('-')[1], 10) : new Date().getMonth() + 1
  const [month, setMonth] = useState(billMonth)
  const prof = sizing?.profiles[String(month)]
  const offGrid = sizing?.kind === 'off_grid'
  const deficitLabel = offGrid ? 'Unserved' : 'From grid'
  const surplusLabel = sizing && sizing.kind !== 'net_metering' && sizing.kind !== 'combination' ? 'Unused surplus' : 'Exported'
  const chart = Array.from({ length: 24 }, (_, h) => ({
    hour: `${h}`,
    Load: +(audit.load_profile_kw[month - 1][h]).toFixed(3),
    Solar: prof ? +prof.production[h].toFixed(3) : 0,
    'From battery': prof ? +prof.discharge[h].toFixed(3) : 0,
    [deficitLabel]: prof ? +prof.imported[h].toFixed(3) : 0,
    'To battery': prof ? +prof.charge[h].toFixed(3) : 0,
    [surplusLabel]: prof ? +(prof.export[h] + prof.curtailed[h]).toFixed(3) : 0,
  }))
  const warnings = [...audit.warnings, ...(sizing?.warnings ?? [])]

  return (
    <div>
      {warnings.map((w, i) => (
        <div key={w.code + i} className={`banner ${['roof_limited', 'reconcile_floor', 'reconcile_ceiling', 'audit_gap'].includes(w.code) ? 'warn' : 'info'}`}>
          {w.message}
        </div>
      ))}

      {sizing && (
        <div className="kpis">
          <div className="kpi">
            <div className="label">Recommended solar</div>
            <div className="value">{n2(sizing.kwp)} kWp</div>
            <div className="sub">
              {sizing.panels} x {panelWp} W {panelName}
              {sizing.roof_limited ? ` · roof limit (net-zero needs ${n1(sizing.target_kwp)} kWp)` : ` · roof allows up to ${n2(sizing.roof_max_kwp)} kWp`}
            </div>
          </div>
          <div className="kpi">
            <div className="label">Inverter</div>
            <div className="value">
              {sizing.inverter.units > 1 ? `${sizing.inverter.units} x ` : ''}
              {sizing.inverter.size_kw} kW
            </div>
            <div className="sub">needs {n1(sizing.inverter.required_kw)} kW, set by {sizing.inverter.binding}</div>
          </div>
          <div className="kpi">
            <div className="label">Battery</div>
            <div className="value">{sizing.battery.installed_kwh > 0 ? `${n1(sizing.battery.installed_kwh)} kWh` : 'none'}</div>
            <div className="sub">
              {sizing.battery.installed_kwh > 0
                ? `${n1(sizing.battery.usable_kwh)} kWh usable at ${Math.round(sizing.battery.depth_of_discharge * 100)}% depth of discharge, carries what solar cannot`
                : KIND_LABEL[sizing.kind]}
            </div>
          </div>
          <div className="kpi">
            <div className="label">Consumption covered</div>
            <div className="value">{n0(sizing.coverage_pct)}%</div>
            <div className="sub">
              {n0(sizing.annual_consumption_kwh)} kWh/yr used, {n0(sizing.annual_production_kwh)} kWh/yr produced
            </div>
          </div>
          <div className="kpi">
            <div className="label">{offGrid ? 'Unserved' : 'From the grid'}</div>
            <div className="value">{n0(offGrid ? sizing.annual_unserved_kwh : sizing.annual_import_kwh)} kWh</div>
            <div className="sub">
              {offGrid ? `per year not covered, ${n0(sizing.annual_curtailed_kwh)} kWh surplus unused` : `imported per year, ${n0(sizing.annual_export_kwh)} exported`}
            </div>
          </div>
        </div>
      )}

      <h3>Typical day</h3>
      <div className="month-picker">
        {MONTHS.map((m, i) => (
          <button key={m} type="button" className={`toggle ${month === i + 1 ? 'on' : ''}`} onClick={() => setMonth(i + 1)}>
            {m}
          </button>
        ))}
        <span className="muted" style={{ marginLeft: 8 }}>
          {n1(audit.daily_kwh_by_month[month - 1])} kWh per day
        </span>
      </div>
      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <ComposedChart data={chart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e3e8e8" />
            <XAxis dataKey="hour" />
            <YAxis unit=" kW" />
            <Tooltip />
            <Legend />
            <Area dataKey="Solar" fill="#C9A227" fillOpacity={0.35} stroke="#C9A227" type="monotone" />
            <Bar dataKey={deficitLabel} stackId="s" fill="#c84f2b" />
            <Bar dataKey="From battery" stackId="s" fill="#2f5fd8" />
            <Bar dataKey="To battery" stackId="t" fill="#a9c4f5" />
            <Bar dataKey={surplusLabel} stackId="t" fill="#cfd8d8" />
            <Line dataKey="Load" stroke="#111111" strokeWidth={2} dot={false} type="monotone" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {avb && (
        <>
          <h3>Audit vs bill</h3>
          <table>
            <thead>
              <tr>
                <th>Bill</th>
                <th className="num">Billed kWh</th>
                <th className="num">Audit as typed</th>
                <th className="num">Scaled to bill</th>
              </tr>
            </thead>
            <tbody>
              {avb.bills.map((b) => (
                <tr key={b.billing_month}>
                  <td>
                    {b.billing_month} ({b.days} days)
                  </td>
                  <td className="num">{n0(b.kwh)}</td>
                  <td className="num">
                    {n0(b.audit_kwh)} <span className={`badge ${Math.abs(avb.gap_pct) > 10 ? 'bad' : 'good'}`}>{pct((b.audit_kwh - b.kwh) / b.kwh * 100)}</span>
                  </td>
                  <td className="num">{n0(b.reconciled_kwh)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="muted" style={{ marginTop: 6 }}>
            {avb.reconciled
              ? `Uncertain appliances (aircon, refrigerators, dispensers, pumps, storage heaters) scaled by ${n2(avb.scale_uncertain)}, then everything existing by ${n2(avb.scale_all)}. A future appliance of a type the house already has inherits that scale; new types are used as typed.`
              : 'Reconciliation is off; the audit is used as typed.'}
          </div>
        </>
      )}

      <h3>Appliances</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Appliance</th>
              <th>Status</th>
              <th className="num">Qty</th>
              <th className="num">W</th>
              <th className="num">Duty</th>
              <th className="num">Hours per use day</th>
              <th className="num">Days/wk</th>
              <th className="num">kWh/day typed</th>
              <th className="num">kWh/day used</th>
              <th className="num">Share</th>
            </tr>
          </thead>
          <tbody>
            {audit.appliances.map((a) => (
              <tr key={a.id} className={a.status === 'retiring' ? 'muted' : ''}>
                <td>
                  {a.name} <span className="muted">{a.category_label}</span>
                  {a.warnings.map((w) => (
                    <div key={w.code} className="badge bad" style={{ display: 'block', marginTop: 2 }}>
                      {w.message}
                    </div>
                  ))}
                </td>
                <td>
                  {a.status === 'existing' ? '' : <span className="badge neutral">{a.status === 'future' ? 'future' : 'removed'}</span>}
                  {a.scale_inherited && <span className="muted" title="scaled like the existing appliances of this type"> ~</span>}
                </td>
                <td className="num">{a.quantity}</td>
                <td className="num">{a.input_power_w}</td>
                <td className="num" style={{ whiteSpace: 'nowrap' }}>
                  {n2(a.duty_factor)}
                  {a.uncertain ? '*' : ''}
                </td>
                <td className="num">{n1(a.hours_per_use_day)}</td>
                <td className="num">{a.days_per_week}</td>
                <td className="num">{n2(a.kwh_per_day_audit)}</td>
                <td className="num">{a.status === 'retiring' ? '-' : n2(a.kwh_per_day_reconciled)}</td>
                <td className="num">{a.status === 'retiring' ? '-' : `${a.share_pct.toFixed(0)}%`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="muted" style={{ marginTop: 6 }}>
        * uncertain type, scaled first during reconciliation. ~ future appliance scaled like the existing ones of its type.
      </div>
      <h3>Peak load</h3>
      <div className="muted">
        Hour table peak: <b>{n2(audit.peak_kw)} kW</b>
        {audit.peak_detail.label && ` at ${audit.peak_detail.label} on a ${audit.peak_detail.weekday} (${MONTHS[audit.peak_detail.month - 1]})`}, the sum of every appliance touching that hour at quantity x watts x duty.
        Highest hourly average of energy {n2(audit.peak_avg_kw)} kW
        {audit.largest_motor_kw > 0 && `; largest motor ${n1(audit.largest_motor_kw)} kW starting at ${audit.largest_motor_multiplier}x for the surge check`}.
      </div>
      {audit.peak_detail.contributors && audit.peak_detail.contributors.length > 0 && (
        <div className="muted" style={{ marginTop: 4 }}>
          In that hour: {audit.peak_detail.contributors.map((c) => `${c.name} ${Math.round(c.watts).toLocaleString()} W`).join(', ')}.
        </div>
      )}
      {audit.hour_table.length > 0 && (
        <details className="internal" style={{ marginTop: 6 }}>
          <summary>Hour table for that day</summary>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Hour</th>
                  <th>Appliances (duty-weighted W)</th>
                  <th className="num">Total W</th>
                </tr>
              </thead>
              <tbody>
                {audit.hour_table.map((row) => (
                  <tr key={row.hour} className={row.hour === audit.peak_detail.hour ? 'peak-row' : ''}>
                    <td style={{ whiteSpace: 'nowrap' }}>{row.label}</td>
                    <td>{row.appliances.map((a) => `${a.name} ${Math.round(a.watts)}`).join(' + ') || '-'}</td>
                    <td className="num">{Math.round(row.total_w).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      {sizing && (
        <>
          <h3>Month by month</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th></th>
                  {MONTHS.map((m) => (
                    <th key={m} className="num">
                      {m}
                    </th>
                  ))}
                  <th className="num">Year</th>
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ['Consumption kWh', 'consumption_kwh'],
                    ['Solar production kWh', 'production_kwh'],
                    ['Used directly kWh', 'direct_kwh'],
                    ['From battery kWh', 'battery_kwh'],
                    [offGrid ? 'Unused surplus kWh' : 'Exported kWh', offGrid ? 'curtailed_kwh' : 'export_kwh'],
                    [offGrid ? 'Unserved kWh' : 'From grid kWh', offGrid ? 'unserved_kwh' : 'import_kwh'],
                  ] as [string, keyof SizingBlock['monthly'][number]][]
                ).map(([label, key]) => (
                  <tr key={key}>
                    <td>{label}</td>
                    {sizing.monthly.map((m) => (
                      <td key={m.month} className="num">
                        {n0(m[key] as number)}
                      </td>
                    ))}
                    <td className="num">{n0(sizing.monthly.reduce((s, m) => s + (m[key] as number), 0))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="muted" style={{ marginTop: 6 }}>
            {KIND_LABEL[sizing.kind]}
            {sizing.offgrid && ` (worst month produces ${sizing.offgrid.pv_margin}x consumption; the battery carries the night, no autonomy allowance)`}. Yield {n0(sizing.annual_yield_kwh_per_kwp)} kWh per kWp per year from this roof's measured simulation. Self-consumption {n0(sizing.self_consumption_pct)}% of production.
            Inverter check: peak {n1(sizing.inverter.peak_load_kw)} kW, surge {n1(sizing.inverter.surge_requirement_kw)} kW at {sizing.inverter.surge_factor}x, PV {n1(sizing.inverter.pv_requirement_kw)} kW at {sizing.inverter.pv_ratio_max}x.
          </div>
        </>
      )}
    </div>
  )
}
