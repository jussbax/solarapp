import { useState } from 'react'
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { EconomicsBlock, EconomicsJob } from '../types'
import NumberInput from './NumberInput'

const php0 = (v: number | null | undefined) => (v == null ? '-' : `₱${Math.round(v).toLocaleString()}`)
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
// colours validated for colour-blind separation and contrast on the light surface
const C_SAVE = '#0b9b8d'
const C_COST = '#c84f2b'
const C_CUM = '#2f5fd8'

function Num({ label, value, onChange, hint, step, min, width = 170 }: { label: string; value: number | null; onChange: (v: number | null) => void; hint?: string; step?: number; min?: number; width?: number }) {
  return (
    <div className="narrow" style={{ width }}>
      <label>{label}</label>
      <NumberInput value={value} onChange={onChange} allowEmpty placeholder={hint} step={step} min={min} />
    </div>
  )
}

const pctIn = (v: number | null) => (v == null ? null : Math.round(v * 10000) / 100)
const pctOut = (v: number | null) => (v == null ? null : v / 100)

export function EconomicsInputs({ job, eco, onChange }: { job: EconomicsJob; eco: EconomicsBlock | null; onChange: (j: EconomicsJob) => void }) {
  const set = (p: Partial<EconomicsJob>) => onChange({ ...job, ...p })
  const a = eco?.assumptions
  const hint = (v: number | undefined, f = (x: number) => String(x)) => (v == null ? '' : f(v))
  return (
    <div>
      <div className="row">
        <Num label="Tariff (₱/kWh)" value={job.tariff_php_per_kwh} onChange={(v) => set({ tariff_php_per_kwh: v })} hint={a ? `${a.tariff_php_per_kwh.toFixed(2)} from ${a.tariff_source}` : 'from the bill'} step={0.1} min={0} width={200} />
        <Num label="Export credit (₱/kWh)" value={job.export_rate_php_per_kwh} onChange={(v) => set({ export_rate_php_per_kwh: v })} hint={hint(a?.export_rate_php_per_kwh, (x) => x.toFixed(2))} step={0.1} min={0} />
        <Num label="Tariff rise per year (%)" value={pctIn(job.tariff_escalation)} onChange={(v) => set({ tariff_escalation: pctOut(v) })} hint={hint(a?.tariff_escalation, (x) => (x * 100).toFixed(1))} step={0.5} />
        <Num label="Panel degradation per year (%)" value={pctIn(job.degradation)} onChange={(v) => set({ degradation: pctOut(v) })} hint={hint(a?.degradation, (x) => (x * 100).toFixed(2))} step={0.1} min={0} width={200} />
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <Num label="Analysis years" value={job.analysis_years} onChange={(v) => set({ analysis_years: v })} hint={hint(a?.analysis_years)} step={1} min={1} width={130} />
        <Num label="Discount rate (%)" value={pctIn(job.discount_rate)} onChange={(v) => set({ discount_rate: pctOut(v) })} hint={hint(a?.discount_rate, (x) => (x * 100).toFixed(1))} step={0.5} min={0} width={140} />
        <Num label="Battery life (years)" value={job.battery_life_years} onChange={(v) => set({ battery_life_years: v })} hint={hint(a?.battery_life_years)} step={1} min={1} width={150} />
        <Num label="Inverter life (years)" value={job.inverter_life_years} onChange={(v) => set({ inverter_life_years: v })} hint={hint(a?.inverter_life_years)} step={1} min={1} width={150} />
        <Num label="Upkeep per year (₱)" value={job.om_per_year} onChange={(v) => set({ om_per_year: v })} hint={hint(a?.om_per_year, (x) => Math.round(x).toString())} step={100} min={0} width={160} />
      </div>
      <div className="muted" style={{ marginTop: 6 }}>
        Blank fields follow the settings. The tariff defaults to the latest bill's amount over kWh, the effective rate the customer pays. The export credit is the utility's blended generation rate under net metering, not the retail rate; check it for the customer's utility.
      </div>
    </div>
  )
}

export function EconomicsResults({ eco }: { eco: EconomicsBlock }) {
  const [showYears, setShowYears] = useState(false)
  if (!eco.available) return <div className="banner warn">{eco.reason}</div>
  const a = eco.assumptions!
  const years = eco.years ?? []
  const chart = [{ year: '0', Savings: 0, Costs: Math.round(eco.contract ?? 0), Cumulative: -Math.round(eco.contract ?? 0) }, ...years.map((y) => ({ year: String(y.year), Savings: Math.round(y.savings), Costs: Math.round(y.costs), Cumulative: Math.round(y.cumulative) }))]
  const monthly = (eco.monthly ?? []).map((m) => ({ month: MONTHS[m.month - 1], Before: Math.round(m.bill_before), After: Math.round(m.bill_after) }))
  return (
    <div>
      {eco.warnings.map((w, i) => (
        <div key={w.code + i} className="banner info">
          {w.message}
        </div>
      ))}
      <div className="kpis">
        <div className="kpi">
          <div className="label">Monthly bill, without → with solar</div>
          <div className="value">
            {php0(eco.bill_before_monthly)} → {php0(eco.bill_after_monthly)}
          </div>
          <div className="sub">
            saves {php0(eco.savings_monthly)} a month at ₱{a.tariff_php_per_kwh.toFixed(2)}/kWh ({a.tariff_source})
            {eco.includes_future_loads && `; today's bill is ${php0(eco.bill_today_monthly)}, the rest is the planned appliances`}
          </div>
        </div>
        <div className="kpi">
          <div className="label">First-year savings</div>
          <div className="value">{php0(eco.year1?.savings)}</div>
          <div className="sub">
            {Math.round(eco.year1?.solar_used_kwh ?? 0).toLocaleString()} kWh used from solar
            {eco.kind !== 'off_grid' && `, ${Math.round(eco.year1?.export_kwh ?? 0).toLocaleString()} kWh exported for ${php0(eco.year1?.export_credit)}`}
          </div>
        </div>
        <div className="kpi">
          <div className="label">Payback</div>
          <div className="value">{eco.payback_years != null ? `${eco.payback_years.toFixed(1)} yrs` : `> ${a.analysis_years} yrs`}</div>
          <div className="sub">{eco.discounted_payback_years != null ? `${eco.discounted_payback_years.toFixed(1)} yrs discounted at ${(a.discount_rate * 100).toFixed(0)}%` : 'no discounted payback in the period'}</div>
        </div>
        <div className="kpi">
          <div className="label">Net over {a.analysis_years} years</div>
          <div className="value">{php0(eco.lifetime_net)}</div>
          <div className="sub">
            NPV {php0(eco.npv)}, IRR {eco.irr != null ? `${(eco.irr * 100).toFixed(1)}%` : '-'}
          </div>
        </div>
        <div className="kpi">
          <div className="label">Cost of solar energy</div>
          <div className="value">{eco.lcoe_php_per_kwh != null ? `₱${eco.lcoe_php_per_kwh.toFixed(2)}/kWh` : '-'}</div>
          <div className="sub">lifetime cost over lifetime production; {eco.co2_t_per_year?.toFixed(1)} t CO2 avoided a year</div>
        </div>
      </div>

      <h3>Monthly bill, before and after solar (year 1)</h3>
      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer>
          <ComposedChart data={monthly} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e3e8e8" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
            <Tooltip formatter={(v) => php0(Number(v))} />
            <Legend />
            <Bar dataKey="Before" fill={C_COST} radius={[4, 4, 0, 0]} />
            <Bar dataKey="After" fill={C_SAVE} radius={[4, 4, 0, 0]} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <h3>Cumulative return over {a.analysis_years} years</h3>
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <ComposedChart data={chart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e3e8e8" vertical={false} />
            <XAxis dataKey="year" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
            <Tooltip formatter={(v) => php0(Number(v))} />
            <Legend />
            <ReferenceLine y={0} stroke="#888" />
            <Bar dataKey="Savings" fill={C_SAVE} radius={[4, 4, 0, 0]} />
            <Bar dataKey="Costs" fill={C_COST} radius={[4, 4, 0, 0]} />
            <Line type="monotone" dataKey="Cumulative" stroke={C_CUM} strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="muted">
        Assumptions: tariff ₱{a.tariff_php_per_kwh.toFixed(2)}/kWh rising {(a.tariff_escalation * 100).toFixed(1)}% a year; panels lose {(a.degradation * 100).toFixed(2)}% a year;
        {eco.kind !== 'off_grid' && ` export credited at ₱${a.export_rate_php_per_kwh.toFixed(2)}/kWh;`} upkeep {php0(a.om_per_year)} a year;
        {a.battery_replacement_cost > 0 && ` battery replaced every ${a.battery_life_years} years at ${php0(a.battery_replacement_cost)};`}
        {a.inverter_replacement_cost > 0 && ` inverter replaced every ${a.inverter_life_years} years at ${php0(a.inverter_replacement_cost)};`} discount rate {(a.discount_rate * 100).toFixed(0)}%.
      </div>
      <div style={{ marginTop: 8 }}>
        <button type="button" onClick={() => setShowYears((v) => !v)}>
          {showYears ? 'Hide' : 'Show'} year-by-year table
        </button>
      </div>
      {showYears && (
        <div className="table-wrap" style={{ marginTop: 6 }}>
          <table>
            <thead>
              <tr>
                <th>Year</th>
                <th className="num">Production kWh</th>
                <th className="num">Savings</th>
                <th className="num">Costs</th>
                <th className="num">Net</th>
                <th className="num">Cumulative</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {years.map((y) => (
                <tr key={y.year}>
                  <td>{y.year}</td>
                  <td className="num">{Math.round(y.production_kwh).toLocaleString()}</td>
                  <td className="num" style={{ color: C_SAVE }}>{php0(y.savings)}</td>
                  <td className="num" style={{ color: C_COST }}>{y.costs ? php0(y.costs) : ''}</td>
                  <td className="num">{php0(y.net)}</td>
                  <td className="num" style={{ fontWeight: 600, color: y.cumulative < 0 ? C_COST : undefined }}>{php0(y.cumulative)}</td>
                  <td className="muted">{y.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
