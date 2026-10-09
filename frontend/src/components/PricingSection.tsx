import { Fragment, useState } from 'react'
import { api } from '../api'
import type { MaterialItem, PricingBlock, PricingJob } from '../types'
import MaterialPicker from './MaterialPicker'
import NumberInput from './NumberInput'
import Field from './Field'
import { DefaultNum } from './ProgramSection'
import { usePricingDefaults } from './shared'
import { php0, php2 } from '../fmt'

const php = php2
const pct = (v: number) => `${(v * 100).toFixed(1)}%`
const qty = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1))
/** Warnings that stop the job even without the `hard` flag: no item to price. */
const RED_CODES = new Set(['missing_item', 'no_inverter', 'no_battery', 'ats', 'ac_breaker'])

export function PricingInputs({ job, pricing, onChange }: { job: PricingJob; pricing: PricingBlock | null; onChange: (j: PricingJob) => void }) {
  const set = (p: Partial<PricingJob>) => onChange({ ...job, ...p })
  const ch = pricing?.choices
  const ji = pricing?.job_inputs ?? {}
  const cfg = usePricingDefaults()
  const jd = cfg?.job_defaults ?? {}
  const wr = cfg?.wiring ?? {}
  /** The default in force: the current setting, or what the last calculation used when the job left the field blank. */
  const def = (key: keyof PricingJob, setting: unknown): number | undefined => {
    if (typeof setting === 'number') return setting
    const used = ji[key as string]
    return job[key] == null && typeof used === 'number' ? used : undefined
  }
  const pinKm = pricing?.pin_distance?.extra_km
  return (
    <div>
      <div className="lead">
        A value tagged <span className="field-tag">default</span> comes from the pricing settings and is the one in force; type over it to change it for this job only.
      </div>
      <div className="form-grid">
        <Field label="Inverter" className="wide" state={job.inverter_code ? 'override' : ch?.inverter_code ? 'default' : undefined} onUseDefault={() => set({ inverter_code: null })}>
          {(id) => (
            <select id={id} value={job.inverter_code ?? ''} onChange={(e) => set({ inverter_code: e.target.value || null })}>
              <option value="">Default inverter{ch?.inverter_code ? ` (${ch.inverter_units && ch.inverter_units > 1 ? `${ch.inverter_units} x ` : ''}${ch.inverter_code})` : ''}</option>
              {(ch?.inverter_options ?? []).map((o) => (
                <option key={o.code} value={o.code}>
                  {o.code} {o.name} · {o.rating_kw} kW · {php0(o.landed)}
                </option>
              ))}
              {job.inverter_code && !(ch?.inverter_options ?? []).some((o) => o.code === job.inverter_code) && <option value={job.inverter_code}>{job.inverter_code}</option>}
            </select>
          )}
        </Field>
        <Field label="Battery" className="wide" state={job.battery_code ? 'override' : ch?.battery_code ? 'default' : undefined} onUseDefault={() => set({ battery_code: null })}>
          {(id) => (
            <select id={id} value={job.battery_code ?? ''} onChange={(e) => set({ battery_code: e.target.value || null })}>
              <option value="">Cheapest combination that fits{ch?.battery_code ? ` (${ch.battery_units} x ${ch.battery_code})` : ''}</option>
              {(ch?.battery_options ?? []).map((o) => (
                <option key={o.code} value={o.code}>
                  {o.units} x {o.code} {o.name} = {o.total_kwh.toFixed(1)} kWh · {php0(o.landed)}
                </option>
              ))}
              {job.battery_code && !(ch?.battery_options ?? []).some((o) => o.code === job.battery_code) && <option value={job.battery_code}>{job.battery_code}</option>}
            </select>
          )}
        </Field>
        <DefaultNum label="Max panels per string" unit="panels" value={job.max_panels_per_string} fallback={typeof cfg?.roles?.max_panels_per_string === 'number' ? cfg.roles.max_panels_per_string : undefined} onChange={(v) => set({ max_panels_per_string: v })} min={1} step={1} />
        <DefaultNum
          label="Strings"
          value={job.strings_override}
          fallback={ch?.strings}
          onChange={(v) => set({ strings_override: v })}
          min={1}
          step={1}
          help="Computed from the panels per string; type a count to force it."
          unknownHelp="Computed from the panels per string; shown after the first calculation."
        />
        <DefaultNum
          label="Extra km, one way"
          unit="km"
          value={job.extra_km}
          fallback={pinKm ?? def('extra_km', jd.extra_km)}
          onChange={(v) => set({ extra_km: v })}
          min={0}
          help={pinKm != null ? 'From the map pin: straight line × road factor, less the route’s reference site.' : 'From the map pin once calculated.'}
        />
        <DefaultNum label="Extra toll" unit="₱" value={job.extra_toll} fallback={def('extra_toll', jd.extra_toll)} onChange={(v) => set({ extra_toll: v })} min={0} />
        <DefaultNum label="Roof productivity factor" unit="×" value={job.roof_factor} fallback={def('roof_factor', jd.roof_factor)} onChange={(v) => set({ roof_factor: v })} min={0.1} step={0.05} />
        <DefaultNum label="Days the roof is closed" unit="days" value={job.roof_closed_days} fallback={def('roof_closed_days', jd.roof_closed_days)} onChange={(v) => set({ roof_closed_days: v })} min={0} step={1} />
        <DefaultNum label="Max installation days" unit="days" value={job.max_days} fallback={def('max_days', jd.max_days)} onChange={(v) => set({ max_days: v })} min={1} step={1} />
        <DefaultNum label="Max roof pairs" unit="pairs" value={job.max_pairs} fallback={def('max_pairs', jd.max_pairs)} onChange={(v) => set({ max_pairs: v })} min={1} step={1} />
        <DefaultNum label="Owner days on site" unit="days" value={job.owner_days} fallback={def('owner_days', jd.owner_days)} onChange={(v) => set({ owner_days: v })} min={0} />
        <DefaultNum label="PV run per string" unit="m" value={job.pv_run_m} fallback={typeof wr.pv_run_m === 'number' ? wr.pv_run_m : undefined} onChange={(v) => set({ pv_run_m: v })} min={1} />
        <DefaultNum label="AC run" unit="m" value={job.ac_run_m} fallback={typeof wr.ac_run_m === 'number' ? wr.ac_run_m : undefined} onChange={(v) => set({ ac_run_m: v })} min={1} />
        <DefaultNum label="Grounding run" unit="m" value={job.grounding_run_m} fallback={typeof wr.grounding_run_m === 'number' ? wr.grounding_run_m : undefined} onChange={(v) => set({ grounding_run_m: v })} min={0} />
        <DefaultNum label="Conduit" unit="m" value={job.conduit_m} fallback={typeof wr.conduit_m === 'number' ? wr.conduit_m : undefined} onChange={(v) => set({ conduit_m: v })} min={0} />
      </div>
    </div>
  )
}

/** Quantities: the price and its sections, the customer BOQ lines, the editable bill of materials with its two exports,
 * and the internal build-up. The proposal PDF lives in the Documents card. */
export function PricingResults({
  pricing,
  job,
  onJobChange,
  exportUrls,
  docReason,
  openDocument,
}: {
  pricing: PricingBlock
  job: PricingJob
  onJobChange: (j: PricingJob) => void
  /** The BOM export routes; the server applies the one stale rule to them as to every document. */
  exportUrls: { csv: string; xlsx: string }
  /** Why no document (the exports included) can be produced right now, or null when they can. */
  docReason: string | null
  openDocument: (url: string) => void
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
      {(pricing.warnings ?? []).map((w, i) => (
        <div key={w.code + i} className={`banner ${w.hard || RED_CODES.has(w.code) ? 'bad' : 'warn'}`} data-hard={w.hard ? '1' : undefined}>
          {w.message}
        </div>
      ))}
      <div className="kpis">
        <div className="kpi">
          <div className="label">Contract price</div>
          <div className="value">{php0(t.contract_rounded)}</div>
          <div className="sub">VAT included · {t.price_per_wp ? `₱${t.price_per_wp.toFixed(2)} per Wp · ` : ''}{t.kwp.toFixed(2)} kWp</div>
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
        Bill of materials (BOM){' '}
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
            {pricing.choices.ac_gauge} mm² THHN at {pct(pricing.choices.ac_drop)} drop. The System design card has the full picture.
          </>
        )}
      </div>
      <div className="actions inline bom-actions">
        <button type="button" disabled={!!docReason} onClick={() => openDocument(exportUrls.csv)} data-testid="export-csv">
          Export CSV
        </button>
        <button type="button" disabled={!!docReason} onClick={() => openDocument(exportUrls.xlsx)} data-testid="export-xlsx">
          Export XLSX
        </button>
        <button type="button" onClick={() => setShowInternal((v) => !v)}>{showInternal ? 'Hide' : 'Show'} internal build-up</button>
        <span className="muted doc-reason">{docReason ?? 'The exports carry the list below with your edits, for supplier orders.'}</span>
      </div>
      <div className="table-wrap">
        <table className="bom">
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
                  <td className="cell-code code">{l.code}</td>
                  <td className="cell-main">
                    {l.name || <span className="badge bad">not in list</span>} <span className="muted">{l.category}</span>
                  </td>
                  <td className="cell-supplier" data-label="Supplier">{l.supplier}</td>
                  <td className="num cell-qty" style={{ width: 90 }}>
                    <NumberInput value={l.qty} onChange={(v) => setQty(l.code, v)} min={0} style={e ? { borderColor: '#d98e04' } : undefined} />
                    <span className="unit-inline muted">{l.unit}</span>
                  </td>
                  <td className="cell-unit">{l.unit}</td>
                  {showInternal && (
                    <>
                      <td className="num cell-internal" data-label="Landed/unit">{php(l.landed_unit)}</td>
                      <td className="num cell-internal" data-label="Landed">{php(l.landed)}</td>
                      <td className="num cell-internal" data-label="Selling">
                        {php(l.selling)} <span className="muted">{pct(l.markup_tier)}</span>
                      </td>
                    </>
                  )}
                  <td className="muted cell-note">{l.note}</td>
                  <td className="cell-remove">
                    <button type="button" className="toggle link remove-icon" onClick={() => remove(l.code)} aria-label={`Remove ${l.code}`} title="Remove this line">
                      <span className="remove-x" aria-hidden="true">×</span>
                      <span className="remove-word">remove</span>
                    </button>
                  </td>
                </tr>
              )
            })}
            {removedCodes.map((c) => (
              <tr key={'rm' + c} className="row-removed" style={{ opacity: 0.6 }}>
                <td className="cell-code code">{c}</td>
                <td colSpan={showInternal ? 8 : 5} className="muted cell-main">
                  removed{' '}
                  <button type="button" className="toggle link" onClick={() => setQty(c, null)}>
                    restore
                  </button>
                </td>
                <td className="cell-remove"></td>
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
              Freight: {fr.trips} trip(s) via {(fr.stops_on_run ?? []).join(' → ')}, {fr.loop_km.toFixed(0)} km loop (extra {String(pricing.job_inputs?.extra_km ?? 0)} km each way), toll {php0(fr.toll)}, run cost {php0(fr.run_cost)}; truck share{' '}
              {((fr.truck_share ?? 0) * 100).toFixed(1)}%. Labor: roof {Number(lb.roof_mh ?? 0).toFixed(1)} MH, ground {Number(lb.ground_mh ?? 0).toFixed(1)} MH, carry crew {String(lb.carry_crew ?? '')}; labor {php0(Number(lb.labor ?? 0))}, mob/demob{' '}
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
