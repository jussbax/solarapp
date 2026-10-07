import { useState } from 'react'
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { PaymentMilestone, PaymentPlan, ProgramBlock, ProgramJob } from '../types'
import { JOB_STAGES } from '../types'
import NumberInput from './NumberInput'

const php0 = (v: number | null | undefined) => (v == null ? '-' : `₱${Math.round(v).toLocaleString()}`)
const d = (s: string | null | undefined) => (s ? new Date(s + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '')
const EVENTS: { id: string; label: string }[] = [
  { id: 'signing', label: 'signing' }, { id: 'materials_on_site', label: 'delivery to site' }, { id: 'installation_done', label: 'end of installation' },
  { id: 'commissioning', label: 'commissioning' }, { id: 'cfei', label: 'CFEI' }, { id: 'meter_installed', label: 'meter installed' },
]
// colours validated for colour-blind separation and contrast on the light surface
const C_IN = '#0b9b8d'
const C_OUT = '#c84f2b'
const C_BAL = '#2f5fd8'

function Num({ label, value, onChange, hint, step, min, width = 150 }: { label: string; value: number | null; onChange: (v: number | null) => void; hint?: string; step?: number; min?: number; width?: number }) {
  return (
    <div className="narrow" style={{ width }}>
      <label>{label}</label>
      <NumberInput value={value} onChange={onChange} allowEmpty placeholder={hint} step={step} min={min} />
    </div>
  )
}

function PaymentPlanEditor({ plan, defaults, onChange }: { plan: PaymentPlan | null; defaults: PaymentPlan | undefined; onChange: (p: PaymentPlan | null) => void }) {
  const base: PaymentPlan = plan ?? defaults ?? { milestones: [], installments: 0, installment_share: 0, installment_interval_days: 30, installment_start_event: 'commissioning', installment_first_offset_days: 30 }
  const set = (p: Partial<PaymentPlan>) => onChange({ ...base, ...p })
  const setM = (i: number, p: Partial<PaymentMilestone>) => set({ milestones: base.milestones.map((m, j) => (j === i ? { ...m, ...p } : m)) })
  const total = base.milestones.reduce((a, m) => a + m.share, 0) + (base.installments > 0 ? base.installment_share : 0)
  return (
    <div className="set-card">
      <div className="inline" style={{ justifyContent: 'space-between', width: '100%' }}>
        <b>Payment terms</b>
        <span className="muted">
          {plan ? 'custom for this job' : 'company default'}{' '}
          {plan && (
            <button type="button" className="toggle link" onClick={() => onChange(null)}>
              use default
            </button>
          )}
        </span>
      </div>
      <table style={{ marginTop: 6 }}>
        <thead>
          <tr>
            <th>Milestone</th>
            <th className="num">Share %</th>
            <th>Due at</th>
            <th className="num">+ days</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {base.milestones.map((m, i) => (
            <tr key={i}>
              <td>
                <input value={m.label} onChange={(e) => setM(i, { label: e.target.value })} />
              </td>
              <td className="num" style={{ width: 90 }}>
                <NumberInput value={Math.round(m.share * 1000) / 10} onChange={(v) => setM(i, { share: (v ?? 0) / 100 })} min={0} max={100} />
              </td>
              <td>
                <select value={m.event} onChange={(e) => setM(i, { event: e.target.value })}>
                  {EVENTS.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      {ev.label}
                    </option>
                  ))}
                </select>
              </td>
              <td className="num" style={{ width: 80 }}>
                <NumberInput value={m.offset_days} onChange={(v) => setM(i, { offset_days: v ?? 0 })} step={1} />
              </td>
              <td>
                <button type="button" className="toggle link" onClick={() => set({ milestones: base.milestones.filter((_, j) => j !== i) })}>
                  remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="row" style={{ marginTop: 6 }}>
        <div className="narrow inline">
          <button type="button" onClick={() => set({ milestones: [...base.milestones, { key: `m${base.milestones.length + 1}`, label: 'Payment', share: 0, event: 'commissioning', offset_days: 0 }] })}>
            Add milestone
          </button>
        </div>
        <Num label="Instalments (count)" value={base.installments} onChange={(v) => set({ installments: v ?? 0 })} step={1} min={0} width={140} />
        <Num label="Instalment share %" value={Math.round(base.installment_share * 1000) / 10} onChange={(v) => set({ installment_share: (v ?? 0) / 100 })} min={0} width={140} />
        <Num label="Every (days)" value={base.installment_interval_days} onChange={(v) => set({ installment_interval_days: v ?? 30 })} step={1} min={1} width={110} />
        <Num label="First after (days)" value={base.installment_first_offset_days} onChange={(v) => set({ installment_first_offset_days: v ?? 30 })} step={1} min={0} width={120} />
        <div className="narrow" style={{ width: 170 }}>
          <label>Instalments start at</label>
          <select value={base.installment_start_event} onChange={(e) => set({ installment_start_event: e.target.value })}>
            {EVENTS.map((ev) => (
              <option key={ev.id} value={ev.id}>
                {ev.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className={`muted ${Math.abs(total - 1) > 0.001 ? 'badge bad' : ''}`} style={{ marginTop: 4 }}>
        Shares add up to {(total * 100).toFixed(0)}%{Math.abs(total - 1) > 0.001 ? ' (scaled to 100% when computing)' : ''}
      </div>
    </div>
  )
}

export function ProgramInputs({ job, program, onChange }: { job: ProgramJob; program: ProgramBlock | null; onChange: (j: ProgramJob) => void }) {
  const set = (p: Partial<ProgramJob>) => onChange({ ...job, ...p })
  return (
    <div>
      <div className="row">
        <div className="narrow" style={{ width: 170 }}>
          <label>Job stage</label>
          <select value={job.stage} onChange={(e) => set({ stage: e.target.value as ProgramJob['stage'] })}>
            {JOB_STAGES.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <div className="narrow" style={{ width: 160 }}>
          <label>Signing date</label>
          <input type="date" value={job.signing_date ?? ''} onChange={(e) => set({ signing_date: e.target.value || null })} />
        </div>
        <div className="narrow" style={{ width: 160 }}>
          <label>Installation start</label>
          <input type="date" value={job.install_date ?? ''} onChange={(e) => set({ install_date: e.target.value || null })} />
        </div>
        <div className="narrow" style={{ width: 120 }}>
          <label>Depart base</label>
          <input type="time" value={job.depart_time ?? ''} placeholder="06:00" onChange={(e) => set({ depart_time: e.target.value || null })} />
        </div>
        <div className="narrow" style={{ width: 120 }}>
          <label>Lunch at</label>
          <input type="time" value={job.lunch_start ?? ''} placeholder="12:00" onChange={(e) => set({ lunch_start: e.target.value || null })} />
        </div>
        <Num label="Lunch (min)" value={job.lunch_minutes} onChange={(v) => set({ lunch_minutes: v })} hint="60" step={5} min={0} width={100} />
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <Num label="Permit approval (days)" value={job.permit_approval_days} onChange={(v) => set({ permit_approval_days: v })} hint="7" step={1} min={0} width={170} />
        <Num label="Net metering application (days)" value={job.netmeter_application_days} onChange={(v) => set({ netmeter_application_days: v })} hint="30" step={1} min={0} width={210} />
        <Num label="DU inspection and meter (days)" value={job.netmeter_meter_days} onChange={(v) => set({ netmeter_meter_days: v })} hint="15" step={1} min={0} width={210} />
      </div>
      <div className="muted" style={{ margin: '6px 0' }}>
        Blank dates: signing today, installation the day after the permit is expected. Blank durations follow the program settings; the permit and utility durations are assumptions until you have data.
      </div>
      <PaymentPlanEditor plan={job.payment} defaults={program?.payment_plan} onChange={(payment) => set({ payment })} />
    </div>
  )
}

export function ProgramResults({ program, programUrl, stale }: { program: ProgramBlock; programUrl: string; stale: boolean }) {
  const [day, setDay] = useState(1)
  const [view, setView] = useState<'hourly' | 'tasks'>('hourly')
  if (!program.available) return <div className="banner warn">{program.reason}</div>
  const inst = program.install!
  const cf = program.cashflow!
  const dayRows = inst.hourly.find((h) => h.day === day)?.rows ?? []
  const chart = cf.weekly.map((w) => ({ week: d(w.week), In: Math.round(w.inflow), Out: Math.round(w.outflow), Balance: Math.round(w.balance) }))
  return (
    <div>
      {stale && <div className="banner warn">Inputs were edited after this calculation. Save and compute again to refresh the program.</div>}
      {program.warnings.map((w, i) => (
        <div key={w.code + i} className={`banner ${w.code === 'install_before_permit' || w.code === 'schedule_overrun' ? 'warn' : 'info'}`}>
          {w.message}
        </div>
      ))}
      <div className="kpis">
        <div className="kpi">
          <div className="label">Installation</div>
          <div className="value">{d(program.install_start)}</div>
          <div className="sub">
            {inst.days} day(s), {inst.crew.description}; {inst.crew.roof_pairs} roof pair(s), {inst.crew.ground_persons} on the ground
          </div>
        </div>
        <div className="kpi">
          <div className="label">Commissioning</div>
          <div className="value">{d(program.events?.find((e) => e.key === 'commissioning')?.date)}</div>
          <div className="sub">{program.net_metering ? `meter installed ${d(program.events?.find((e) => e.key === 'meter_installed')?.date)}` : 'off-grid, no utility steps'}</div>
        </div>
        <div className="kpi">
          <div className="label">Cash margin</div>
          <div className="value">{php0(cf.cash_margin)}</div>
          <div className="sub">
            in {php0(cf.total_in)}, out {php0(cf.total_out)}
          </div>
        </div>
        <div className="kpi">
          <div className="label">Lowest balance</div>
          <div className="value" style={{ color: cf.lowest_balance < 0 ? C_OUT : undefined }}>{php0(cf.lowest_balance)}</div>
          <div className="sub">on {d(cf.lowest_balance_date)}; cash the company carries</div>
        </div>
      </div>
      <div className="actions" style={{ position: 'static', border: 0, padding: '4px 0' }}>
        <a href={stale ? undefined : programUrl} onClick={(e) => stale && e.preventDefault()}>
          <button disabled={stale} title={stale ? 'Save and compute first' : ''}>
            Program of works PDF (internal)
          </button>
        </a>
        <span className="muted">The customer quotation PDF carries the milestone schedule and payment terms only.</span>
      </div>

      <h3>Schedule</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Until</th>
              <th>Activity</th>
              <th className="num">Amount</th>
              <th>Customer</th>
            </tr>
          </thead>
          <tbody>
            {(program.events ?? []).map((e, i) => (
              <tr key={e.key + i} style={e.kind === 'milestone' ? { fontWeight: 600 } : e.kind === 'payment_in' ? { color: C_IN } : undefined}>
                <td>{d(e.date)}</td>
                <td>{e.end && e.end !== e.date ? d(e.end) : ''}</td>
                <td>{e.label}</td>
                <td className="num">{e.amount != null ? php0(e.amount) : ''}</td>
                <td>{e.customer ? 'sees this' : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {program.assumptions && program.assumptions.length > 0 && (
        <div className="muted" style={{ marginTop: 4 }}>
          {program.assumptions.map((a, i) => (
            <div key={i}>Assumption: {a}</div>
          ))}
        </div>
      )}

      <h3>
        Installation days by the hour{' '}
        <span className="toggles" style={{ marginLeft: 8 }}>
          {inst.hourly.map((h) => (
            <button key={h.day} type="button" className={`toggle ${day === h.day ? 'on' : ''}`} onClick={() => setDay(h.day)}>
              Day {h.day}
            </button>
          ))}
          <button type="button" className={`toggle ${view === 'tasks' ? 'on' : ''}`} onClick={() => setView(view === 'tasks' ? 'hourly' : 'tasks')}>
            task list
          </button>
        </span>
      </h3>
      <div className="muted" style={{ marginBottom: 6 }}>
        Depart {String(inst.frame.depart)}, on site {String(inst.frame.arrive)}, work from {String(inst.frame.work_start)}, lunch {String(inst.frame.lunch_start)} to {String(inst.frame.lunch_end)}, back at base about{' '}
        {String(inst.frame.back_at_base)}. Man-hours: roof {inst.man_hours.roof.toFixed(1)}, ground {inst.man_hours.ground.toFixed(1)}, hand-off {inst.man_hours.handoff.toFixed(1)}. The roof crew joins the ground tasks once the roof is done; energizing waits for the roof strings.
      </div>
      <div className="table-wrap">
        {view === 'hourly' ? (
          <table>
            <thead>
              <tr>
                <th>Hour</th>
                <th>Roof crew ({inst.crew.roof_persons})</th>
                <th>Ground crew ({inst.crew.ground_persons})</th>
              </tr>
            </thead>
            <tbody>
              {dayRows.map((r) => (
                <tr key={r.time}>
                  <td style={{ whiteSpace: 'nowrap' }}>{r.time}</td>
                  <td>{r.roof}</td>
                  <td>{r.ground}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Day</th>
                <th>From</th>
                <th>To</th>
                <th>Crew</th>
                <th className="num">Persons</th>
                <th>Task</th>
              </tr>
            </thead>
            <tbody>
              {inst.segments.map((s, i) => (
                <tr key={i}>
                  <td>{s.day + 1}</td>
                  <td>{s.start_time}</td>
                  <td>{s.end_time}</td>
                  <td>{s.stream}</td>
                  <td className="num">{s.crew}</td>
                  <td>{s.task}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <h3>Cashflow</h3>
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <ComposedChart data={chart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e3e8e8" vertical={false} />
            <XAxis dataKey="week" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
            <Tooltip formatter={(v) => php0(Number(v))} />
            <Legend />
            <Bar dataKey="In" fill={C_IN} radius={[4, 4, 0, 0]} />
            <Bar dataKey="Out" fill={C_OUT} radius={[4, 4, 0, 0]} />
            <Line type="stepAfter" dataKey="Balance" stroke={C_BAL} strokeWidth={2} dot={{ r: 4 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Item</th>
              <th className="num">In</th>
              <th className="num">Out</th>
              <th className="num">Balance</th>
            </tr>
          </thead>
          <tbody>
            {cf.flows.map((f, i) => (
              <tr key={f.key + i}>
                <td style={{ whiteSpace: 'nowrap' }}>{d(f.date)}</td>
                <td>{f.label}</td>
                <td className="num" style={{ color: C_IN }}>{f.inflow ? php0(f.inflow) : ''}</td>
                <td className="num" style={{ color: C_OUT }}>{f.outflow ? php0(f.outflow) : ''}</td>
                <td className="num" style={{ fontWeight: 600, color: f.balance < 0 ? C_OUT : undefined }}>{php0(f.balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="muted" style={{ marginTop: 6 }}>
        Kept in the company as allocations rather than cash: handling, wastage and storage {php0(cf.noncash.handling_wastage_storage)}, truck ownership and maintenance{' '}
        {php0(cf.noncash.truck_ownership_maintenance)}, tools {php0(cf.noncash.tools)}. Commission is 5% of the direct cost, paid after the job. VAT is shown as a remittance after completion.
      </div>
    </div>
  )
}
