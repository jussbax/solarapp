import { useState, type ReactNode } from 'react'
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { PaymentMilestone, PaymentPlan, PricingConfig, ProgramBlock, ProgramJob } from '../types'
import NumberInput from './NumberInput'
import Field from './Field'
import { Gantt } from './Gantt'
import { useElementWidth } from './responsive'
import { fillWeeks, kTick, roundTo, usePricingDefaults } from './shared'
import { fmtDate, fmtDateShort, php0 } from '../fmt'

const d = fmtDate
const EVENTS: { id: string; label: string; on: string }[] = [
  { id: 'signing', label: 'Signing', on: 'signing' }, { id: 'materials_on_site', label: 'Delivery to site', on: 'delivery' }, { id: 'installation_done', label: 'End of installation', on: 'the end of installation' },
  { id: 'commissioning', label: 'Switch-on', on: 'switch-on' }, { id: 'cfei', label: 'Final inspection certificate', on: 'the final inspection' }, { id: 'meter_installed', label: 'Meter installed', on: 'the meter' },
]
// colours validated for colour-blind separation and contrast on the light surface; as text the gold is --gold-text (4.9:1)
const C_IN = '#C9A227'
const C_OUT = '#c84f2b'
const C_BAL = '#2f5fd8'
const GOLD_TEXT = 'var(--gold-text)'

const same = (a: number | null | undefined, b: number | null | undefined) => a != null && b != null && Math.abs(a - b) < 1e-9

/** A project number whose value in force is always visible: the job's own value, or the company default shown
 * filled and untagged. Typing a value makes it an override (tagged, with the way back); typing the default itself,
 * or clearing the field, goes back to the default. `fallback` undefined means the default is not known yet. */
export function DefaultNum({
  label,
  value,
  fallback,
  onChange,
  unit,
  help,
  about,
  unknownHelp,
  step,
  min,
  max,
  decimals = 2,
}: {
  label: string
  value: number | null
  fallback: number | null | undefined
  onChange: (v: number | null) => void
  unit?: string
  help?: string
  /** The long explanation, behind the "?" beside the label. */
  about?: string
  /** Help while the default is not known yet (before the first calculation). */
  unknownHelp?: string
  step?: number
  min?: number
  max?: number
  /** Decimals shown for the quantity kind; the default is rounded the same way (a bill-derived tariff carries many more). */
  decimals?: number
}) {
  const isDefault = value == null
  const known = fallback != null
  const rounded: number | null = known ? roundTo(fallback, decimals) : null
  const shown: number | null = isDefault ? rounded : value
  return (
    <Field
      label={label}
      unit={unit}
      help={isDefault && !known ? (unknownHelp ?? 'Shown after the first calculation') : help}
      about={about}
      state={isDefault ? (known ? 'default' : undefined) : 'override'}
      onUseDefault={() => onChange(null)}
    >
      {(id) => (
        <NumberInput
          id={id}
          value={shown}
          decimals={decimals}
          onChange={(v) => onChange(same(v, rounded) || same(v, fallback) ? null : v)}
          allowEmpty
          placeholder={known ? undefined : 'from the settings'}
          step={step}
          min={min}
          max={max}
        />
      )}
    </Field>
  )
}

/** The inputs a job rarely changes, folded under one line; the fold opens itself while it holds an override. */
export function AdjustFold({ changed, children, testId = 'adjust' }: { changed: number; children: ReactNode; testId?: string }) {
  const [open, setOpen] = useState(changed > 0)
  return (
    <details className="more adjust" open={open} onToggle={(e) => setOpen(e.currentTarget.open)} data-testid={testId}>
      <summary>
        Adjust for this job
        {changed > 0 && <span className="muted"> · {changed} changed</span>}
      </summary>
      {children}
    </details>
  )
}

/** "50% on signing, 40% on delivery, 10% on switch-on; then 6 payments of 10% every 30 days". */
function describePlan(p: PaymentPlan): string {
  const parts = p.milestones.map((m) => `${roundTo(m.share * 100, 1)}% on ${EVENTS.find((e) => e.id === m.event)?.on ?? m.event}${m.offset_days ? ` + ${m.offset_days} days` : ''}`)
  const text = parts.join(', ')
  if (p.installments > 0) return `${text}; then ${p.installments} payments of ${roundTo((p.installment_share / p.installments) * 100, 1)}% every ${p.installment_interval_days} days`
  return text
}

/** The payment terms as one line ("Company terms: 50% on signing, ...") with Change; the editor opens only on Change. */
export function PaymentTermsLine({ plan, defaults, onChange }: { plan: PaymentPlan | null; defaults: PaymentPlan | undefined; onChange: (p: PaymentPlan | null) => void }) {
  const [editing, setEditing] = useState(false)
  const shown = plan ?? defaults
  if (editing) {
    return (
      <div className="terms-editor" data-testid="payment-terms">
        <PaymentPlanEditor plan={plan} defaults={defaults} onChange={onChange} />
        <div style={{ marginTop: 4 }}>
          <button type="button" className="toggle link" onClick={() => setEditing(false)}>
            Done
          </button>
        </div>
      </div>
    )
  }
  return (
    <div className="terms-line" data-testid="payment-terms">
      <b>Payment terms</b>
      <span>
        {plan ? 'This job: ' : 'Company terms: '}
        {shown ? describePlan(shown) : 'shown after the first calculation'}
      </span>
      <button type="button" className="toggle link" onClick={() => setEditing(true)}>
        Change
      </button>
      {plan && (
        <button type="button" className="toggle link" onClick={() => onChange(null)}>
          Use company terms
        </button>
      )}
    </div>
  )
}

export function PaymentPlanEditor({ plan, defaults, onChange, hideDefaultLink = false, heading = true }: { plan: PaymentPlan | null; defaults: PaymentPlan | undefined; onChange: (p: PaymentPlan | null) => void; hideDefaultLink?: boolean; heading?: boolean }) {
  const base: PaymentPlan = plan ?? defaults ?? { milestones: [], installments: 0, installment_share: 0, installment_interval_days: 30, installment_start_event: 'commissioning', installment_first_offset_days: 30 }
  const set = (p: Partial<PaymentPlan>) => onChange({ ...base, ...p })
  const setM = (i: number, p: Partial<PaymentMilestone>) => set({ milestones: base.milestones.map((m, j) => (j === i ? { ...m, ...p } : m)) })
  const total = base.milestones.reduce((a, m) => a + m.share, 0) + (base.installments > 0 ? base.installment_share : 0)
  const known = plan != null || defaults != null // before the first compute the company default is not loaded yet
  return (
    <div className="set-card">
      {heading && (
        <div className="card-head">
          <b>Payment terms</b>
          <span className="muted">
            {hideDefaultLink ? '' : plan ? (
              <>
                <span className="field-tag override" style={{ cursor: 'default' }}>Override</span>{' '}
                <button type="button" className="toggle link" onClick={() => onChange(null)}>
                  Use company terms
                </button>
              </>
            ) : known ? (
              'The company terms'
            ) : (
              'Company terms, shown after the first calculation'
            )}
          </span>
        </div>
      )}
      {/* under 640 px the rows stack as cards (data-label headings) so the Due at select is not 40 px wide */}
      <table className="payments">
        <thead>
          <tr>
            <th>Milestone</th>
            <th className="num">Share %</th>
            <th>Due at</th>
            <th className="num">Plus days</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {base.milestones.map((m, i) => (
            <tr key={i}>
              <td className="cell-main" data-label="Milestone">
                <input value={m.label} onChange={(e) => setM(i, { label: e.target.value })} aria-label={`Milestone ${i + 1} name`} />
              </td>
              <td className="num" style={{ width: 90 }} data-label="Share %">
                <NumberInput value={Math.round(m.share * 1000) / 10} decimals={1} onChange={(v) => setM(i, { share: (v ?? 0) / 100 })} min={0} max={100} ariaLabel={`Milestone ${i + 1} share %`} />
              </td>
              <td data-label="Due at">
                <select value={m.event} onChange={(e) => setM(i, { event: e.target.value })} aria-label={`Milestone ${i + 1} due at`}>
                  {EVENTS.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      {ev.label}
                    </option>
                  ))}
                </select>
              </td>
              <td className="num" style={{ width: 80 }} data-label="Plus days">
                <NumberInput value={m.offset_days} decimals={0} onChange={(v) => setM(i, { offset_days: v ?? 0 })} ariaLabel={`Milestone ${i + 1} plus days`} />
              </td>
              <td className="cell-actions">
                <button type="button" className="toggle link" onClick={() => set({ milestones: base.milestones.filter((_, j) => j !== i) })}>
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 8 }}>
        <button type="button" className="small" onClick={() => set({ milestones: [...base.milestones, { key: `m${base.milestones.length + 1}`, label: 'Payment', share: 0, event: 'commissioning', offset_days: 0 }] })}>
          Add milestone
        </button>
      </div>
      {/* the installments line on the same four columns as the lines above it */}
      <div className="form-grid" style={{ marginTop: 8 }}>
        <Field label="Installments" unit="payments" help="0 = none">
          {(id) => <NumberInput id={id} value={base.installments} decimals={0} onChange={(v) => set({ installments: v ?? 0 })} min={0} />}
        </Field>
        <Field label="Installment share" unit="%">
          {(id) => <NumberInput id={id} value={Math.round(base.installment_share * 1000) / 10} decimals={1} onChange={(v) => set({ installment_share: (v ?? 0) / 100 })} min={0} allowEmpty />}
        </Field>
        <Field label="Every" unit="days">
          {(id) => <NumberInput id={id} value={base.installment_interval_days} decimals={0} onChange={(v) => set({ installment_interval_days: v ?? 30 })} min={1} allowEmpty />}
        </Field>
        <Field label="First one after" unit="days">
          {(id) => <NumberInput id={id} value={base.installment_first_offset_days} decimals={0} onChange={(v) => set({ installment_first_offset_days: v ?? 30 })} min={0} allowEmpty />}
        </Field>
        <Field label="Counted from">
          {(id) => (
            <select id={id} value={base.installment_start_event} onChange={(e) => set({ installment_start_event: e.target.value })}>
              {EVENTS.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.label}
                </option>
              ))}
            </select>
          )}
        </Field>
      </div>
      {known && (
        <div className={`muted ${Math.abs(total - 1) > 0.001 ? 'badge bad' : ''}`}>
          Shares add up to {(total * 100).toFixed(0)}%{Math.abs(total - 1) > 0.001 ? ' (scaled to 100% when computing)' : ''}
        </div>
      )}
    </div>
  )
}

/** The site-day defaults from the program settings, so a blank time input says what it means. */
function useTimeDefaults(cfg: PricingConfig | null, program: ProgramBlock | null) {
  const frame = program?.install?.frame
  const depart = String(cfg?.program?.depart_time ?? '') || (frame ? String(frame.depart) : '')
  const lunch = String(cfg?.program?.lunch_start ?? '') || (frame ? String(frame.lunch_start) : '')
  return { depart, lunch }
}

function TimeField({ label, value, fallback, onChange }: { label: string; value: string | null; fallback: string; onChange: (v: string | null) => void }) {
  const isDefault = !value
  return (
    <Field label={label} state={isDefault ? (fallback ? 'default' : undefined) : 'override'} onUseDefault={() => onChange(null)} help={isDefault && !fallback ? 'Shown after the first calculation' : undefined}>
      {(id) => <input id={id} type="time" value={value ?? fallback} onChange={(e) => onChange(e.target.value && e.target.value !== fallback ? e.target.value : null)} />}
    </Field>
  )
}

const localToday = () => {
  const n = new Date()
  return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, '0')}-${String(n.getDate()).padStart(2, '0')}`
}

/** Schedule and cashflow inputs. The job stage is a pill in the page head, not an input here. */
export function ProgramInputs({ job, program, onChange }: { job: ProgramJob; program: ProgramBlock | null; onChange: (j: ProgramJob) => void }) {
  const set = (p: Partial<ProgramJob>) => onChange({ ...job, ...p })
  const cfg = usePricingDefaults()
  const defaults = useTimeDefaults(cfg, program)
  const pc = cfg?.program ?? {}
  const today = localToday()
  const installDefault = job.install_date == null && program?.available ? program.install_start ?? '' : ''
  const changed = [job.depart_time, job.lunch_start, job.lunch_minutes, job.permit_approval_days, job.netmeter_application_days, job.netmeter_meter_days].filter((v) => v != null).length
  return (
    <div>
      <div className="lead">All values are the company's program settings unless tagged; type over one to change it for this job only.</div>
      <div className="form-grid">
        <Field label="Signing date" state={job.signing_date ? 'override' : 'default'} onUseDefault={() => set({ signing_date: null })} help={job.signing_date ? undefined : 'Today'}>
          {(id) => <input id={id} type="date" value={job.signing_date ?? today} onChange={(e) => set({ signing_date: e.target.value && e.target.value !== today ? e.target.value : null })} />}
        </Field>
        <Field
          label="Installation start"
          state={job.install_date ? 'override' : installDefault ? 'default' : undefined}
          onUseDefault={() => set({ install_date: null })}
          help={job.install_date ? undefined : installDefault ? 'After the permit' : 'After the permit; shown after the first calculation'}
        >
          {(id) => <input id={id} type="date" value={job.install_date ?? installDefault} onChange={(e) => set({ install_date: e.target.value && e.target.value !== installDefault ? e.target.value : null })} />}
        </Field>
      </div>
      <AdjustFold changed={changed} testId="adjust-program">
        <div className="form-grid">
          <TimeField label="Leave base at" value={job.depart_time} fallback={defaults.depart} onChange={(depart_time) => set({ depart_time })} />
          <TimeField label="Lunch at" value={job.lunch_start} fallback={defaults.lunch} onChange={(lunch_start) => set({ lunch_start })} />
          <DefaultNum label="Lunch break" unit="minutes" value={job.lunch_minutes} fallback={pc.lunch_minutes} onChange={(v) => set({ lunch_minutes: v })} step={5} min={0} decimals={0} />
          <DefaultNum label="Electrical permit approval" unit="days" value={job.permit_approval_days} fallback={pc.permit_approval_days} onChange={(v) => set({ permit_approval_days: v })} min={0} decimals={0} help="Assumption" about="An assumption until you have data from the LGU." />
          <DefaultNum label="Net metering application" unit="days" value={job.netmeter_application_days} fallback={pc.netmeter_application_days} onChange={(v) => set({ netmeter_application_days: v })} min={0} decimals={0} help="Assumption" />
          <DefaultNum label="Inspection and net metering meter" unit="days" value={job.netmeter_meter_days} fallback={pc.netmeter_meter_days} onChange={(v) => set({ netmeter_meter_days: v })} min={0} decimals={0} help="After switch-on" />
        </div>
      </AdjustFold>
      <PaymentTermsLine plan={job.payment} defaults={program?.payment_plan ?? cfg?.program?.payment} onChange={(payment) => set({ payment })} />
    </div>
  )
}

/** Program of works: the Gantt chart first, then the schedule table, the hour-by-hour plan and the task list. */
export function ProgramResults({ program }: { program: ProgramBlock }) {
  const [day, setDay] = useState(1)
  const [view, setView] = useState<'hourly' | 'tasks'>('hourly')
  const [ganttRef, ganttWidth] = useElementWidth<HTMLDivElement>()
  if (!program.available) return <div className="banner warn">{program.reason}</div>
  const inst = program.install!
  const dayRows = inst.hourly.find((h) => h.day === day)?.rows ?? []
  return (
    <div>
      {program.warnings.map((w, i) => (
        <div key={w.code + i} className={`banner ${w.hard ? 'bad' : w.code === 'install_before_permit' || w.code === 'schedule_overrun' ? 'warn' : 'info'}`}>
          {w.message}
        </div>
      ))}
      <div className="kpis">
        <div className="kpi">
          <div className="label">Installation</div>
          <div className="value">{d(program.install_start)}</div>
          <div className="sub">
            {inst.days} {inst.days === 1 ? 'day' : 'days'}, {inst.crew.description}; {inst.crew.roof_pairs} roof {inst.crew.roof_pairs === 1 ? 'pair' : 'pairs'}, {inst.crew.ground_persons} on the ground
          </div>
        </div>
        <div className="kpi">
          <div className="label">Switch-on</div>
          <div className="value">{d(program.events?.find((e) => e.key === 'commissioning')?.date)}</div>
          <div className="sub">{program.net_metering ? `meter installed ${d(program.events?.find((e) => e.key === 'meter_installed')?.date)}` : 'off-grid, no utility steps'}</div>
        </div>
        <div className="kpi">
          <div className="label">Completion</div>
          <div className="value">{d(program.completion)}</div>
          <div className="sub">signing {d(program.signing_date)}; the proposal PDF carries the milestone schedule and payment terms only</div>
        </div>
      </div>

      <h3>Schedule</h3>
      <div ref={ganttRef} data-testid="gantt">
        <Gantt events={program.events ?? []} today={localToday()} width={ganttWidth || 900} />
      </div>
      <div className="table-wrap" style={{ marginTop: 10 }}>
        <table className="schedule">
          <thead>
            <tr>
              <th>Date</th>
              <th>Until</th>
              <th>Activity</th>
              <th className="num">Amount</th>
              <th>Customer sees</th>
            </tr>
          </thead>
          <tbody>
            {(program.events ?? []).map((e, i) => (
              <tr key={e.key + i} style={e.kind === 'milestone' ? { fontWeight: 600 } : e.kind === 'payment_in' ? { color: GOLD_TEXT, fontWeight: 600 } : undefined}>
                <td style={{ whiteSpace: 'nowrap' }}>{d(e.date)}</td>
                <td style={{ whiteSpace: 'nowrap' }}>{e.end && e.end !== e.date ? d(e.end) : ''}</td>
                <td>{e.label}</td>
                <td className="num">{e.amount != null ? php0(e.amount) : ''}</td>
                <td>{e.customer ? <span aria-label="The customer sees this">✓</span> : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {program.assumptions && program.assumptions.length > 0 && (
        <div className="muted" style={{ marginTop: 4 }}>
          {program.assumptions.map((a, i) => (
            <div key={i}>{a}</div>
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
            Task list
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
    </div>
  )
}

/** Cashflow: the weekly chart, the flow table and what stays in the company as allocations. */
export function CashflowResults({ program }: { program: ProgramBlock }) {
  if (!program.available) return <div className="banner warn">{program.reason}</div>
  const cf = program.cashflow!
  const chart = fillWeeks(cf.weekly).map((w) => ({ week: fmtDateShort(w.week), In: Math.round(w.inflow), Out: Math.round(w.outflow), Balance: Math.round(w.balance) }))
  return (
    <div>
      <div className="kpis">
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
          <div className="sub">on {d(cf.lowest_balance_date)}; most cash out at one time</div>
        </div>
      </div>
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <ComposedChart data={chart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e3e8e8" vertical={false} />
            <XAxis dataKey="week" tick={{ fontSize: 11 }} interval="preserveStartEnd" minTickGap={24} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={kTick} />
            <Tooltip formatter={(v) => php0(Number(v))} />
            <Legend />
            <Bar dataKey="In" fill={C_IN} radius={[4, 4, 0, 0]} />
            <Bar dataKey="Out" fill={C_OUT} radius={[4, 4, 0, 0]} />
            <Line type="stepAfter" dataKey="Balance" stroke={C_BAL} strokeWidth={2} dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="muted" style={{ margin: '0 0 8px' }}>
        One bar group per week from the first flow to the last; an empty week carries the balance.
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
                <td className="num" style={{ color: GOLD_TEXT, fontWeight: 600 }}>{f.inflow ? php0(f.inflow) : ''}</td>
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
