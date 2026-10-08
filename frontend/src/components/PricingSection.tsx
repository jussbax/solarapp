import { Fragment, useState } from 'react'
import { api } from '../api'
import type { MaterialItem, PricingBlock, PricingJob } from '../types'
import MaterialPicker from './MaterialPicker'
import NumberInput from './NumberInput'

const php = (v: number | null | undefined) => (v == null ? '-' : `₱${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
const php0 = (v: number | null | undefined) => (v == null ? '-' : `₱${Math.round(v).toLocaleString()}`)
const pct = (v: number) => `${(v * 100).toFixed(1)}%`
const qty = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1))

function Num({ label, value, onChange, hint, step, min }: { label: string; value: number | null; onChange: (v: number | null) => void; hint?: string; step?: number; min?: number }) {
  return (
    <div className="narrow" style={{ width: 170 }}>
      <label>{label}</label>
      <NumberInput value={value} onChange={onChange} allowEmpty placeholder={hint} step={step} min={min} />
    </div>
  )
}

export function PricingInputs({ job, pricing, onChange }: { job: PricingJob; pricing: PricingBlock | null; onChange: (j: PricingJob) => void }) {
  const set = (p: Partial<PricingJob>) => onChange({ ...job, ...p })
  const ch = pricing?.choices
  const ji = pricing?.job_inputs ?? {}
  const d = (k: string, fallback: string) => (ji[k] != null ? String(ji[k]) : fallback)
  return (
    <div>
      <div className="muted" style={{ marginBottom: 8 }}>
        Blank fields use the pricing settings. Extra km comes from the map pin (straight line × road factor, less the route's reference site).
      </div>
      <div className="row">
        <div className="narrow" style={{ width: 300 }}>
          <label>Inverter</label>
          <select value={job.inverter_code ?? ''} onChange={(e) => set({ inverter_code: e.target.value || null })}>
            <option value="">Default inverter{ch?.inverter_code ? ` (${ch.inverter_units && ch.inverter_units > 1 ? `${ch.inverter_units} x ` : ''}${ch.inverter_code})` : ''}</option>
            {(ch?.inverter_options ?? []).map((o) => (
              <option key={o.code} value={o.code}>
                {o.code} {o.name} · {o.rating_kw} kW · {php0(o.landed)}
              </option>
            ))}
            {job.inverter_code && !(ch?.inverter_options ?? []).some((o) => o.code === job.inverter_code) && <option value={job.inverter_code}>{job.inverter_code}</option>}
          </select>
        </div>
        <div className="narrow" style={{ width: 300 }}>
          <label>Battery</label>
          <select value={job.battery_code ?? ''} onChange={(e) => set({ battery_code: e.target.value || null })}>
            <option value="">Cheapest combination that fits{ch?.battery_code ? ` (${ch.battery_units} x ${ch.battery_code})` : ''}</option>
            {(ch?.battery_options ?? []).map((o) => (
              <option key={o.code} value={o.code}>
                {o.units} x {o.code} {o.name} = {o.total_kwh.toFixed(1)} kWh · {php0(o.landed)}
              </option>
            ))}
            {job.battery_code && !(ch?.battery_options ?? []).some((o) => o.code === job.battery_code) && <option value={job.battery_code}>{job.battery_code}</option>}
          </select>
        </div>
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <Num label="Max panels per string" value={job.max_panels_per_string} onChange={(v) => set({ max_panels_per_string: v })} hint="10" min={1} step={1} />
        <Num label="Strings (override)" value={job.strings_override} onChange={(v) => set({ strings_override: v })} hint={ch ? `${ch.strings} computed` : 'computed'} min={1} step={1} />
        <Num label="Extra km (one way)" value={job.extra_km} onChange={(v) => set({ extra_km: v })} hint={pricing?.pin_distance ? `${pricing.pin_distance.extra_km} from pin` : '0'} min={0} />
        <Num label="Extra toll (₱)" value={job.extra_toll} onChange={(v) => set({ extra_toll: v })} hint={d('extra_toll', '0')} min={0} />
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <Num label="Roof productivity factor" value={job.roof_factor} onChange={(v) => set({ roof_factor: v })} hint={d('roof_factor', '0.75')} min={0.1} step={0.05} />
        <Num label="Days the roof is closed" value={job.roof_closed_days} onChange={(v) => set({ roof_closed_days: v })} hint={d('roof_closed_days', '1')} min={0} step={1} />
        <Num label="Max installation days" value={job.max_days} onChange={(v) => set({ max_days: v })} hint={d('max_days', '2')} min={1} step={1} />
        <Num label="Max roof pairs" value={job.max_pairs} onChange={(v) => set({ max_pairs: v })} hint={d('max_pairs', '2')} min={1} step={1} />
        <Num label="Owner days on site" value={job.owner_days} onChange={(v) => set({ owner_days: v })} hint={d('owner_days', '0')} min={0} />
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <Num label="PV run per string (m)" value={job.pv_run_m} onChange={(v) => set({ pv_run_m: v })} hint="25" min={1} />
        <Num label="AC run (m)" value={job.ac_run_m} onChange={(v) => set({ ac_run_m: v })} hint="15" min={1} />
        <Num label="Grounding run (m)" value={job.grounding_run_m} onChange={(v) => set({ grounding_run_m: v })} hint="20" min={0} />
        <Num label="Conduit (m)" value={job.conduit_m} onChange={(v) => set({ conduit_m: v })} hint="30" min={0} />
      </div>
    </div>
  )
}

export function PricingResults({
  pricing,
  job,
  onJobChange,
  quotationUrl,
  stale,
}: {
  pricing: PricingBlock
  job: PricingJob
  onJobChange: (j: PricingJob) => void
  quotationUrl: string
  stale: boolean
}) {
  const [adding, setAdding] = useState(false)
  const [showInternal, setShowInternal] = useState(false)
  if (!pricing.available) {
    return <div className="banner warn">{pricing.reason}</div>
  }
  if (!pricing.totals || !pricing.customer) {
    return <div className="banner warn">This pricing was saved by an older version of the app. Press Calculate to refresh it.</div>
  }
  const lines = pricing.lines ?? []
  const t = pricing.totals!
  const cust = pricing.customer!
  const sec = (k: string) => cust.sections.find((s) => s.key === k)
  const editFor = (code: string) => job.bom_edits.find((e) => e.code === code)
  const setQty = (code: string, v: number | null) => {
    const gen = pricing.generated_bom?.find((g) => g.code === code)
    const edits = job.bom_edits.filter((e) => e.code !== code)
    if (v == null || (gen && Math.abs(gen.qty - v) < 1e-9)) onJobChange({ ...job, bom_edits: edits })
    else onJobChange({ ...job, bom_edits: [...edits, { code, qty: v, note: '' }] })
  }
  const remove = (code: string) => {
    if (job.bom_extra.some((e) => e.code === code) && !pricing.generated_bom?.some((g) => g.code === code)) {
      onJobChange({ ...job, bom_extra: job.bom_extra.filter((e) => e.code !== code) })
    } else {
      setQty(code, 0)
    }
  }
  const addItem = (it: MaterialItem) => {
    const extra = job.bom_extra.filter((e) => e.code !== it.code)
    const prev = job.bom_extra.find((e) => e.code === it.code)
    onJobChange({ ...job, bom_extra: [...extra, { code: it.code, qty: (prev?.qty ?? 0) + 1, note: '' }] })
    setAdding(false)
  }
  const removedCodes = job.bom_edits.filter((e) => e.qty === 0).map((e) => e.code)
  const edited = job.bom_edits.length > 0 || job.bom_extra.length > 0
  const lb = pricing.labor ?? {}
  const fr = pricing.freight

  return (
    <div>
      {stale && <div className="banner warn">Inputs changed since the last calculation. Press Calculate to refresh the price.</div>}
      {(pricing.warnings ?? []).map((w, i) => (
        <div key={w.code + i} className={`banner ${['missing_item', 'no_inverter', 'no_battery', 'ats', 'ac_breaker'].includes(w.code) ? 'bad' : 'warn'}`}>
          {w.message}
        </div>
      ))}
      <div className="kpis">
        <div className="kpi">
          <div className="label">Contract price (VAT included)</div>
          <div className="value">{php0(t.contract_rounded)}</div>
          <div className="sub">{t.price_per_wp ? `₱${t.price_per_wp.toFixed(2)} per Wp` : ''} · {t.kwp.toFixed(2)} kWp</div>
        </div>
        <div className="kpi">
          <div className="label">Materials</div>
          <div className="value">{php0(sec('materials')?.amount)}</div>
          <div className="sub">{(sec('materials')?.items ?? []).filter((i) => i.main).map((i) => `${qty(i.qty)} x ${i.name}`).join(', ')}; mounting, wiring, protection, enclosures, grounding; freight included</div>
        </div>
        <div className="kpi">
          <div className="label">Labor</div>
          <div className="value">{php0(sec('labor')?.amount)}</div>
          <div className="sub">
            {String(lb.persons ?? '')} persons, {Number(lb.days ?? 0)} {Number(lb.days ?? 0) === 1 ? 'day' : 'days'}, {Number(lb.pairs ?? 0)} roof {Number(lb.pairs ?? 0) === 1 ? 'pair' : 'pairs'} · includes transport, PPE, PEE seal, permits and fees
          </div>
        </div>
        <div className="kpi">
          <div className="label">Tools</div>
          <div className="value">{php0(sec('equipment')?.amount)}</div>
          <div className="sub">tool charge for {Number(lb.days ?? 0)} installation {Number(lb.days ?? 0) === 1 ? 'day' : 'days'}</div>
        </div>
        <div className="kpi">
          <div className="label">VAT</div>
          <div className="value">{php0(sec('tax')?.amount)}</div>
          <div className="sub">12% of the three amounts above</div>
        </div>
      </div>
      <div className="actions" style={{ position: 'static', border: 0, padding: '4px 0' }}>
        <a href={stale ? undefined : quotationUrl} onClick={(e) => stale && e.preventDefault()}>
          <button disabled={stale} title={stale ? 'Calculate first' : ''}>
            Proposal PDF
          </button>
        </a>
        <button onClick={() => setShowInternal((v) => !v)}>{showInternal ? 'Hide' : 'Show'} internal build-up</button>
      </div>

      <details style={{ marginBottom: 10 }}>
        <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Customer proposal lines (what the proposal PDF shows)</summary>
        <div className="table-wrap" style={{ marginTop: 6 }}>
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th className="num">Qty</th>
                <th>Unit</th>
                <th className="num">Amount</th>
              </tr>
            </thead>
            <tbody>
              {cust.sections.map((s) => (
                <Fragment key={s.key}>
                  <tr style={{ fontWeight: 600, background: '#f7fafa' }}>
                    <td colSpan={3}>{s.label}</td>
                    <td className="num">{php(s.amount)}</td>
                  </tr>
                  {s.items.map((i) => (
                    <tr key={i.key}>
                      <td style={{ paddingLeft: 18 }}>{i.name}</td>
                      <td className="num">{qty(i.qty)}</td>
                      <td>{i.unit}</td>
                      <td className="num">{php(i.amount)}</td>
                    </tr>
                  ))}
                </Fragment>
              ))}
              <tr style={{ fontWeight: 700 }}>
                <td colSpan={3}>Total, VAT inclusive</td>
                <td className="num">{php(cust.total)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>

      <h3>
        Bill of materials{' '}
        {edited && (
          <button type="button" className="toggle link" onClick={() => onJobChange({ ...job, bom_edits: [], bom_extra: [] })}>
            Reset to generated
          </button>
        )}
      </h3>
      <div className="muted" style={{ marginBottom: 6 }}>
        Change a quantity or remove a line, then press Calculate to reprice. Generated quantities are kept as the baseline, so edits survive a recalculation.
        {pricing.choices && (
          <>
            {' '}
            Strings: {pricing.choices.strings} x {pricing.choices.panels_per_string} panels ({pricing.choices.string_voltage_v.toFixed(0)} V, {pricing.choices.string_current_a.toFixed(1)} A, {pricing.choices.pv_gauge} mm² at {pct(pricing.choices.pv_drop)} drop). AC {pricing.choices.ac_current_a.toFixed(0)} A on{' '}
            {pricing.choices.ac_gauge} mm² THHN at {pct(pricing.choices.ac_drop)} drop.
          </>
        )}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Item</th>
              <th>Supplier</th>
              <th className="num">Qty</th>
              <th>Unit</th>
              {showInternal && (
                <>
                  <th className="num">Landed/unit</th>
                  <th className="num">Landed</th>
                  <th className="num">Selling</th>
                </>
              )}
              <th>Note</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l) => {
              const e = editFor(l.code)
              return (
                <tr key={l.code} style={!l.found ? { background: '#fdecec' } : undefined}>
                  <td>{l.code}</td>
                  <td>
                    {l.name || <span className="badge bad">not in list</span>} <span className="muted">{l.category}</span>
                  </td>
                  <td>{l.supplier}</td>
                  <td className="num" style={{ width: 90 }}>
                    <NumberInput value={l.qty} onChange={(v) => setQty(l.code, v)} min={0} style={e ? { borderColor: '#d98e04' } : undefined} />
                  </td>
                  <td>{l.unit}</td>
                  {showInternal && (
                    <>
                      <td className="num">{php(l.landed_unit)}</td>
                      <td className="num">{php(l.landed)}</td>
                      <td className="num">
                        {php(l.selling)} <span className="muted">{pct(l.markup_tier)}</span>
                      </td>
                    </>
                  )}
                  <td className="muted">{l.note}</td>
                  <td>
                    <button type="button" className="toggle link" onClick={() => remove(l.code)}>
                      remove
                    </button>
                  </td>
                </tr>
              )
            })}
            {removedCodes.map((c) => (
              <tr key={'rm' + c} style={{ opacity: 0.6 }}>
                <td>{c}</td>
                <td colSpan={showInternal ? 8 : 5} className="muted">
                  removed{' '}
                  <button type="button" className="toggle link" onClick={() => setQty(c, null)}>
                    restore
                  </button>
                </td>
                <td></td>
              </tr>
            ))}
          </tbody>
          {showInternal && (
            <tfoot>
              <tr style={{ fontWeight: 600 }}>
                <td colSpan={6}>Materials</td>
                <td className="num">{php(t.materials_landed)}</td>
                <td className="num">{php(t.materials_selling)}</td>
                <td colSpan={2}></td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      <div style={{ marginTop: 8 }}>
        {adding ? (
          <div style={{ maxWidth: 520 }}>
            <MaterialPicker onPick={addItem} autoFocus placeholder="Search by code, name or spec" />
          </div>
        ) : (
          <button type="button" onClick={() => setAdding(true)}>
            Add item
          </button>
        )}
      </div>

      {showInternal && pricing.build_up && (
        <>
          <h3>Build-up (internal)</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Line</th>
                  <th className="num">Direct</th>
                  <th>Tier</th>
                  <th className="num">Markup</th>
                  <th className="num">Selling</th>
                </tr>
              </thead>
              <tbody>
                {pricing.build_up.map((b) => (
                  <tr key={b.key}>
                    <td>{b.label}</td>
                    <td className="num">{php(b.direct)}</td>
                    <td>{b.pass_through ? 'pass-through' : pct(b.tier)}</td>
                    <td className="num">{php(b.markup)}</td>
                    <td className="num">{php(b.selling)}</td>
                  </tr>
                ))}
                <tr style={{ fontWeight: 600 }}>
                  <td>Direct cost and selling</td>
                  <td className="num">{php(t.direct)}</td>
                  <td></td>
                  <td className="num">{php(t.markup)}</td>
                  <td className="num">{php(t.selling)}</td>
                </tr>
                <tr>
                  <td>Agent commission</td>
                  <td colSpan={3}></td>
                  <td className="num">{php(t.commission)}</td>
                </tr>
                <tr>
                  <td>VAT</td>
                  <td colSpan={3}></td>
                  <td className="num">{php(t.vat)}</td>
                </tr>
                <tr style={{ fontWeight: 600 }}>
                  <td>Contract (rounded up)</td>
                  <td colSpan={3} className="muted">
                    OCM {php0(t.ocm)}, profit {php0(t.op)}, markup {pct(t.markup_over_direct)} over direct
                  </td>
                  <td className="num">{php(t.contract_rounded)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          {fr && (
            <div className="muted" style={{ marginTop: 6 }}>
              Freight: {fr.trips} trip(s) via {(fr.stops_on_run ?? []).join(' → ')}, {fr.loop_km.toFixed(0)} km loop (extra {String(pricing.job_inputs?.extra_km ?? 0)} km each way), toll ₱{fr.toll.toLocaleString()}, run cost {php0(fr.run_cost)}; truck share{' '}
              {((fr.truck_share ?? 0) * 100).toFixed(1)}%. Labour: roof {Number(lb.roof_mh ?? 0).toFixed(1)} MH, ground {Number(lb.ground_mh ?? 0).toFixed(1)} MH, carry crew {String(lb.carry_crew ?? '')}; labour {php0(Number(lb.labor ?? 0))}, mob/demob{' '}
              {php0(Number(lb.mobdemob ?? 0))}, tools {php0(Number(lb.tools ?? 0))}.
            </div>
          )}
        </>
      )}
    </div>
  )
}

export function quotationLink(id: number) {
  return api.quotationUrl(id)
}
