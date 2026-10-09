import { useState } from 'react'
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { EconomicsBlock, EconomicsJob } from '../types'
import { AdjustFold, DefaultNum } from './ProgramSection'
import { kTick, usePricingDefaults } from './shared'
import { php0 } from '../fmt'
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
// colours validated for colour-blind separation and contrast on the light surface; as text the gold is --gold-text (4.9:1)
const C_SAVE = '#C9A227'
const C_COST = '#c84f2b'
const C_CUM = '#2f5fd8'
const GOLD_TEXT = 'var(--gold-text)'

const pctIn = (v: number | null | undefined) => (v == null ? null : Math.round(v * 10000) / 100)
const pctOut = (v: number | null) => (v == null ? null : v / 100)

export function EconomicsInputs({ job, eco, onChange }: { job: EconomicsJob; eco: EconomicsBlock | null; onChange: (j: EconomicsJob) => void }) {
  const set = (p: Partial<EconomicsJob>) => onChange({ ...job, ...p })
  const a = eco?.assumptions
  const cfg = usePricingDefaults()
  const ec = cfg?.economics ?? {}
  /** The default in force: the current setting, or what the last calculation used when the job left the field blank. */
  const def = (key: keyof EconomicsJob, setting: unknown, used: number | undefined): number | undefined => {
    if (typeof setting === 'number') return setting
    return job[key] == null ? used : undefined
  }
  const tariffDefault = job.tariff_php_per_kwh == null ? a?.tariff_php_per_kwh : undefined
  const changed = [job.export_rate_php_per_kwh, job.tariff_escalation, job.degradation, job.analysis_years, job.discount_rate, job.battery_life_years, job.inverter_life_years, job.om_per_year].filter((v) => v != null).length
  const upkeepPct = typeof ec.om_share_per_year === 'number' ? `${(ec.om_share_per_year * 100).toFixed(1)}% of the contract a year` : undefined
  return (
    <div>
      <div className="lead">All values are the company's savings settings unless tagged, the tariff from the latest bill; type over one to change it for this customer only.</div>
      <div className="form-grid">
        <DefaultNum
          label="Tariff"
          unit="₱ per kWh"
          value={job.tariff_php_per_kwh}
          fallback={tariffDefault}
          onChange={(v) => set({ tariff_php_per_kwh: v })}
          step={0.1}
          min={0}
          help={a && job.tariff_php_per_kwh == null ? `From ${a.tariff_source}` : 'The latest bill'}
          about="The latest bill's amount over its kWh: the effective rate the customer pays, including every charge on the bill. Without a bill amount the savings settings' tariff is used."
          unknownHelp="From the latest bill; shown after the first calculation"
        />
      </div>
      <AdjustFold changed={changed} testId="adjust-savings">
        <div className="form-grid">
          <DefaultNum label="Export credit" unit="₱ per kWh" value={job.export_rate_php_per_kwh} fallback={def('export_rate_php_per_kwh', ec.export_rate_php_per_kwh, a?.export_rate_php_per_kwh)} onChange={(v) => set({ export_rate_php_per_kwh: v })} step={0.1} min={0} help="The DU's generation rate" about="The electric company's blended generation rate under net metering, not the retail rate; check it for the customer's utility." />
          <DefaultNum label="Electricity price rise" unit="% a year" value={pctIn(job.tariff_escalation)} fallback={pctIn(def('tariff_escalation', ec.tariff_escalation, a?.tariff_escalation)) ?? undefined} onChange={(v) => set({ tariff_escalation: pctOut(v) })} step={0.5} decimals={1} />
          <DefaultNum label="Panel output loss" unit="% a year" value={pctIn(job.degradation)} fallback={pctIn(def('degradation', ec.degradation, a?.degradation)) ?? undefined} onChange={(v) => set({ degradation: pctOut(v) })} step={0.1} min={0} decimals={1} />
          <DefaultNum label="Analysis period" unit="years" value={job.analysis_years} fallback={def('analysis_years', ec.analysis_years, a?.analysis_years)} onChange={(v) => set({ analysis_years: v })} min={1} decimals={0} />
          <DefaultNum label="Discount rate" unit="%" value={pctIn(job.discount_rate)} fallback={pctIn(def('discount_rate', ec.discount_rate, a?.discount_rate)) ?? undefined} onChange={(v) => set({ discount_rate: pctOut(v) })} step={0.5} min={0} decimals={1} />
          <DefaultNum label="Battery life" unit="years" value={job.battery_life_years} fallback={def('battery_life_years', ec.battery_life_years, a?.battery_life_years)} onChange={(v) => set({ battery_life_years: v })} min={1} decimals={0} help="The warranty, unless set" />
          <DefaultNum label="Inverter life" unit="years" value={job.inverter_life_years} fallback={def('inverter_life_years', ec.inverter_life_years, a?.inverter_life_years)} onChange={(v) => set({ inverter_life_years: v })} min={1} decimals={0} help="Not the warranty" />
          <DefaultNum
            label="Upkeep"
            unit="₱ a year"
            value={job.om_per_year}
            fallback={job.om_per_year == null ? a?.om_per_year : undefined}
            onChange={(v) => set({ om_per_year: v })}
            step={100}
            min={0}
            decimals={0}
            help={upkeepPct}
            unknownHelp={upkeepPct ? `${upkeepPct}; shown after the first calculation` : undefined}
          />
        </div>
      </AdjustFold>
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
      <div className="kpis">
        <div className="kpi">
          <div className="label">Monthly bill</div>
          <div className="value">
            {php0(eco.bill_before_monthly)} → {php0(eco.bill_after_monthly)}
          </div>
          <div className="sub">
            without → with solar: saves {php0(eco.savings_monthly)} a month at ₱{a.tariff_php_per_kwh.toFixed(2)}/kWh ({a.tariff_source})
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
          <div className="label">Pays for itself in</div>
          <div className="value">{eco.payback_years != null ? `${eco.payback_years.toFixed(1)} years` : `more than ${a.analysis_years} years`}</div>
          <div className="sub">{eco.discounted_payback_years != null ? `${eco.discounted_payback_years.toFixed(1)} years discounted at ${(a.discount_rate * 100).toFixed(0)}%` : 'no discounted payback in the period'}</div>
        </div>
        <div className="kpi">
          <div className="label">Net over {a.analysis_years} years</div>
          <div className="value">{php0(eco.lifetime_net)}</div>
          <div className="sub">
            NPV {php0(eco.npv)}, IRR {eco.irr != null ? `${(eco.irr * 100).toFixed(1)}%` : '-'}
          </div>
        </div>
        <div className="kpi">
          <div className="label">Cost per kWh of solar</div>
          <div className="value">{eco.lcoe_php_per_kwh != null ? `₱${eco.lcoe_php_per_kwh.toFixed(2)}/kWh` : '-'}</div>
          <div className="sub">lifetime cost over lifetime production; {eco.co2_t_per_year?.toFixed(1)} t CO2 avoided a year</div>
        </div>
      </div>
      {eco.warnings.length > 0 && (
        <div className="installer-notes">
          <b>Notes for the installer</b>
          <ul>
            {eco.warnings.map((w, i) => (
              <li key={w.code + i}>{w.message}</li>
            ))}
          </ul>
        </div>
      )}

      <h3>Monthly bill, before and after solar (year 1)</h3>
      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer>
          <ComposedChart data={monthly} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e3e8e8" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={kTick} />
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
            <YAxis tick={{ fontSize: 11 }} tickFormatter={kTick} />
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
                  <td className="num" style={{ color: GOLD_TEXT, fontWeight: 600 }}>{php0(y.savings)}</td>
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
