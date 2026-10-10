import { cloneElement, isValidElement, useCallback, useEffect, useId, useRef, useState, type ReactElement } from 'react'
import { api, type Me } from '../api'
import NumberInput from '../components/NumberInput'
import type { DatasheetItemInfo, DatasheetPage, DatasheetReport, DatasheetRow, ImportReport, MaterialItem, MaterialSupplier, PricingStatus } from '../types'
import { fmtDateTime, php2 } from '../fmt'

const php = php2
type ItemDraft = Omit<MaterialItem, 'updated_at'>

function blankItem(): ItemDraft {
  return {
    code: '', category: 'Accessories', supplier: '', name: '', spec: '', unit: 'pc', sold_as: 'pc', list_price: 0, rating: null, rating_unit: '',
    weight_kg: 0, volume_m3: 0, weight_source: 'manual', storage: 0, price_list_date: '', remarks: '', panel_length_m: null, panel_width_m: null, active: true,
    grid_interactive: null, certifications: '', max_pv_voltage_v: null, mppt_min_v: null, mppt_max_v: null, mppt_count: null, mppt_max_a: null, ac_input_a: null,
    battery_max_a: null, has_transfer_switch: null, continuous_a: null, voc_v: null, vmp_v: null, isc_a: null, imp_a: null, temp_coeff_voc_pct: null, temp_coeff_isc_pct: null,
    max_system_voltage_v: null, inverter_type: '', phase: null, battery_class: '', charge_v_max: null, charge_a_max: null, mppt_currents_a: '', battery_inputs: null,
    nominal_v: null, capacity_ah: null, discharge_a_recommended: null,
    overall_area_mm2: null, inner_diameter_mm: null, insulation_c: null, ampacity_a: null, fault_current_a: null, aic_ka: null,
  }
}

const isInverter = (cat: string) => cat === 'Inverter' || cat === 'All-in-one System'
const EQUIPMENT = ['Solar Panel', 'Inverter', 'Battery', 'All-in-one System']
const gridLabel = (v: boolean | null | undefined) => (v === true ? 'yes' : v === false ? 'no' : 'unknown')
const GRID_TITLE: Record<string, string> = {
  yes: 'Grid-interactive: may export (anti-islanding listed)',
  no: 'Not grid-interactive: an off-grid type, cannot export',
  unknown: 'Grid-interactive status unknown: set it under Edit; a net-metering job warns until it is known',
}
const TYPE_LABEL: Record<string, string> = { grid_tie: 'grid-tie', hybrid: 'hybrid', off_grid: 'off-grid', charge_controller: 'charge controller', ess_set: 'ESS set' }
/** Where an electrical figure came from (round 12, brief 2.5): the maker's datasheet, the owner's typing, or the workbook remark read by the importer. */
const SOURCE_TITLE: Record<string, string> = {
  datasheet: "From the maker's datasheet workbook",
  typed: 'Typed on this page (over the datasheet where there is one)',
  remarks: "Read from the item's name and the materials workbook's remark at import; verify against the datasheet",
  none: 'No electrical figures on file',
}
const fmtVal = (v: unknown) => (v == null || v === '' ? '-' : typeof v === 'boolean' ? (v ? 'yes' : 'no') : String(v))
const fmtDate = (d: string | null | undefined) => (d ? fmtDateTime(d).split(',')[0] : '')

/** A fixed-width cell in an item form row: the label is attached to the single control inside it, the unit beside it,
 *  an optional line under it (the datasheet's figure and the way back to it). */
function Field({ label, width = 160, unit, below, children }: { label: string; width?: number; unit?: React.ReactNode; below?: React.ReactNode; children: React.ReactNode }) {
  const id = useId()
  const control = isValidElement(children) ? cloneElement(children as ReactElement<{ id?: string }>, { id }) : children
  return (
    <div className={width ? 'narrow field' : 'field'} style={width ? { width } : { flex: '2 1 260px' }}>
      <label htmlFor={id}>{label}</label>
      <div className="control">
        {control}
        {unit && <span className="unit">{unit}</span>}
      </div>
      {below && <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>{below}</div>}
    </div>
  )
}

/** Datasheet figures per category (contract C4, round 12): panels for the string design, inverters for the string and
 *  circuit design and the net-metering rule, batteries for the current, voltage and charge checks against the inverter.
 *  Beside a field the owner types over, the datasheet's figure stays visible with "reset to datasheet". */
function ElectricalFields({ it, set, info }: { it: ItemDraft; set: (p: Partial<ItemDraft>) => void; info?: DatasheetItemInfo | null }) {
  const ds = info?.datasheet
  const below = (key: keyof ItemDraft): React.ReactNode => {
    if (!ds) return undefined
    const held = ds.held_fields?.[key as string]
    if (held != null && !ds.held_applied_at) return <>held: {fmtVal(held)} (not applied)</>
    const v = ds.fields?.[key as string]
    if (v === undefined) return undefined
    const cur = it[key]
    const same = (typeof v === 'number' && typeof cur === 'number' && Math.abs(v - cur) < 1e-9) || v === cur || (v === '' && cur == null)
    if (same) return <>datasheet</>
    return (
      <>
        datasheet {fmtVal(v)}{' '}
        <button type="button" className="toggle link" style={{ fontSize: 11, padding: 0, minHeight: 0 }} onClick={() => set({ [key]: v } as Partial<ItemDraft>)}>
          reset to datasheet
        </button>
      </>
    )
  }
  const num = (key: keyof ItemDraft, label: string, unit: string, decimals: number, width = 130) => (
    <Field label={label} width={width} unit={unit} below={below(key)}>
      <NumberInput value={(it[key] as number | null | undefined) ?? null} onChange={(v) => set({ [key]: v } as Partial<ItemDraft>)} allowEmpty decimals={decimals} />
    </Field>
  )
  const text = (key: keyof ItemDraft, label: string, width = 150, placeholder = '') => (
    <Field label={label} width={width} below={below(key)}>
      <input value={(it[key] as string | undefined) ?? ''} onChange={(e) => set({ [key]: e.target.value } as Partial<ItemDraft>)} placeholder={placeholder} />
    </Field>
  )
  const choice = (key: keyof ItemDraft, label: string, options: [string, string][], width = 170) => (
    <Field label={label} width={width} below={below(key)}>
      <select value={String(it[key] ?? '')} onChange={(e) => set({ [key]: e.target.value === '' ? (key === 'phase' || key === 'battery_inputs' ? null : '') : key === 'phase' || key === 'battery_inputs' ? Number(e.target.value) : e.target.value } as Partial<ItemDraft>)}>
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </Field>
  )
  if (it.category === 'Solar Panel') {
    return (
      <div className="row" style={{ marginTop: 6 }}>
        {num('voc_v', 'Voc', 'V', 2, 110)}
        {num('vmp_v', 'Vmp', 'V', 2, 110)}
        {num('isc_a', 'Isc', 'A', 2, 110)}
        {num('imp_a', 'Imp', 'A', 2, 110)}
        {num('max_system_voltage_v', 'Max system voltage', 'V', 0, 150)}
        {num('temp_coeff_voc_pct', 'Voc temperature coefficient', '%/°C', 2, 200)}
        {num('temp_coeff_isc_pct', 'Isc temperature coefficient', '%/°C', 2, 200)}
        <div className="muted" style={{ flexBasis: '100%', fontSize: 12 }}>
          From the datasheet at STC; the string design uses Voc at the cold design temperature and Vmp at the hot cell temperature. A panel without a coefficient takes the
          settings' default (an assumption) and every job says so.
        </div>
      </div>
    )
  }
  if (isInverter(it.category)) {
    return (
      <div className="row" style={{ marginTop: 6 }}>
        {choice('inverter_type', 'Type', [['', 'Unknown'], ['grid_tie', 'Grid-tie (no battery port)'], ['hybrid', 'Hybrid'], ['off_grid', 'Off-grid'], ['charge_controller', 'Charge controller'], ['ess_set', 'ESS set']], 200)}
        {choice('phase', 'Phase', [['', 'Unknown'], ['1', '1-phase'], ['3', '3-phase']], 120)}
        {num('max_pv_voltage_v', 'Max PV voltage', 'V', 0, 140)}
        {num('mppt_min_v', 'MPPT min', 'V', 0, 120)}
        {num('mppt_max_v', 'MPPT max', 'V', 0, 120)}
        {num('mppt_count', 'MPPT inputs', 'pcs', 0, 110)}
        {num('mppt_max_a', 'Max per MPPT', 'A', 0, 120)}
        {text('mppt_currents_a', 'MPPT currents per input', 150, '18/36/36')}
        {num('ac_input_a', 'AC input', 'A', 0, 110)}
        {choice('battery_class', 'Battery port', [['', 'Unknown'], ['LV', 'LV (12, 24 or 48 V)'], ['HV', 'HV'], ['none', 'None (no battery input)']], 190)}
        {num('charge_v_max', 'Max charge voltage', 'V', 1, 150)}
        {num('battery_max_a', 'Battery discharge', 'A', 0, 140)}
        {num('charge_a_max', 'Max charge current', 'A', 0, 150)}
        {choice('battery_inputs', 'Battery inputs', [['', 'One'], ['1', 'One'], ['2', 'Two']], 120)}
        {num('fault_current_a', 'Max output fault current', 'A', 1, 170)}
        <Field label="Grid-interactive" width={200}>
          <select
            value={it.grid_interactive === true ? 'yes' : it.grid_interactive === false ? 'no' : ''}
            onChange={(e) => set({ grid_interactive: e.target.value === 'yes' ? true : e.target.value === 'no' ? false : null })}
          >
            <option value="">Unknown</option>
            <option value="yes">Yes, may export (anti-islanding listed)</option>
            <option value="no">No, off-grid type</option>
          </select>
        </Field>
        <Field label="Certifications" width={260}>
          <input value={it.certifications ?? ''} onChange={(e) => set({ certifications: e.target.value })} placeholder="IEC 61727 / 62116, UL 1741" />
        </Field>
        <Field label="Transfer switch" width={200}>
          <select
            value={it.has_transfer_switch === true ? 'yes' : it.has_transfer_switch === false ? 'no' : ''}
            onChange={(e) => set({ has_transfer_switch: e.target.value === 'yes' ? true : e.target.value === 'no' ? false : null })}
          >
            <option value="">Unknown (an ATS is priced)</option>
            <option value="yes">Built in, no external ATS</option>
            <option value="no">None (an ATS is priced)</option>
          </select>
        </Field>
        <div className="muted" style={{ flexBasis: '100%', fontSize: 12 }}>
          Net-metering jobs only take an inverter marked grid-interactive; the certificate prints on the proposal and goes to the electric company. The battery
          circuit runs on the larger of the discharge and charge currents; the port's charge voltage is matched against the battery's class and ceiling. Read from
          the datasheet workbook or the materials remarks at import; verify against the datasheet.
        </div>
      </div>
    )
  }
  if (it.category === 'Battery') {
    return (
      <div className="row" style={{ marginTop: 6 }}>
        {choice('battery_class', 'Class', [['', 'Unknown'], ['LV', 'LV (12, 24 or 48 V)'], ['HV', 'HV']], 170)}
        {num('nominal_v', 'Nominal voltage', 'V', 1, 140)}
        {num('capacity_ah', 'Capacity', 'Ah', 0, 120)}
        {num('continuous_a', 'Max discharge (BMS)', 'A', 0, 160)}
        {num('discharge_a_recommended', 'Recommended discharge', 'A', 0, 170)}
        {num('charge_a_max', 'Max charge current', 'A', 0, 150)}
        {num('charge_v_max', 'Max charge voltage', 'V', 1, 150)}
        {num('fault_current_a', 'Short-circuit trip (BMS)', 'A', 0, 160)}
        <div className="muted" style={{ flexBasis: '100%', fontSize: 12 }}>
          The maximum discharge is the BMS limit the hard bank check reads against the inverter's battery current; the recommended rate is a soft check; the charge
          current says what to set on the inverter; the class and the ceiling are matched against the inverter's port; V × Ah is checked against the kWh rating.
          The BMS's short-circuit trip is the battery's fault contribution on the plans' short-circuit note (blank = "verify with the maker").
        </div>
      </div>
    )
  }
  // round 13 (docs/audits/round-13/engineer-brief.md, 2.3): the figures the plans' design analysis sheet reads from the wires, the raceways and the breakers;
  // a blank prints "not checked" with the reason on the sheet, never a silent default
  if (it.category === 'Wires and Terminations') {
    return (
      <div className="row" style={{ marginTop: 6 }}>
        {num('overall_area_mm2', 'Overall area (insulated)', 'mm²', 2, 170)}
        {num('insulation_c', 'Insulation rating', '°C', 0, 140)}
        {num('ampacity_a', "Maker's ampacity", 'A', 0, 140)}
        <div className="muted" style={{ flexBasis: '100%', fontSize: 12 }}>
          For the design analysis sheet: the insulated conductor's cross-section (the PEC table or the maker's sheet) gives the conduit fill; the insulation rating
          picks the ampacity column (blank reads as the settings' 90 °C, said as an assumption); the maker's ampacity replaces the wiring rules' table figure for a
          PV or battery cable (blank prints "verify the cable's rating").
        </div>
      </div>
    )
  }
  if (it.category === 'Enclosures and Raceways') {
    return (
      <div className="row" style={{ marginTop: 6 }}>
        {num('inner_diameter_mm', 'Inside diameter (conduit)', 'mm', 1, 180)}
        <div className="muted" style={{ flexBasis: '100%', fontSize: 12 }}>
          For a conduit: the inside diameter the design analysis sheet fills against the conductors' areas; blank prints "fill: not checked".
        </div>
      </div>
    )
  }
  if (it.category === 'Protective Devices') {
    return (
      <div className="row" style={{ marginTop: 6 }}>
        {num('aic_ka', 'Interrupting rating (AIC)', 'kA', 1, 170)}
        <div className="muted" style={{ flexBasis: '100%', fontSize: 12 }}>
          The breaker's interrupting rating; the design analysis sheet compares it with the DU's available fault current typed on the Site step (blank prints a
          blank line with "verify").
        </div>
      </div>
    )
  }
  return null
}

/** The Electrical column: the figures on file and a badge saying where they came from (datasheet, typed, remarks or none). */
function electricalSummary(it: MaterialItem, info?: DatasheetItemInfo | null): React.ReactNode {
  const source = info?.source ?? 'none'
  const ds = info?.datasheet
  const badge = EQUIPMENT.includes(it.category) ? (
    <span
      className={`badge ${source === 'datasheet' ? 'good' : source === 'typed' ? 'gold' : source === 'remarks' ? 'neutral' : 'bad'}`}
      title={source === 'datasheet' && ds ? `${SOURCE_TITLE.datasheet}: ${ds.file}, ${fmtDate(ds.date)}` : SOURCE_TITLE[source]}
      data-source={source}
    >
      {source}
    </span>
  ) : null
  const held = ds?.held ? (
    <div className="muted" style={{ fontSize: 11 }}>
      {ds.held_applied_at
        ? `held figures applied on ${fmtDate(ds.held_applied_at)} on the owner's word`
        : it.category === 'Battery'
          ? 'held: maximum above 1 C not applied (6.8)'
          : 'held: grid-tie unit, battery figures not applied (6.4)'}
    </div>
  ) : null
  const over = ds && ds.overridden.length > 0 ? <div className="muted" style={{ fontSize: 11 }}>typed over the datasheet: {ds.overridden.join(', ')}</div> : null
  if (isInverter(it.category)) {
    const grid = gridLabel(it.grid_interactive)
    const parts = [`Grid: ${grid}`]
    if (it.inverter_type) parts.push(TYPE_LABEL[it.inverter_type] ?? it.inverter_type)
    if (it.phase) parts.push(`${it.phase}-phase`)
    if (it.certifications) parts.push(it.certifications)
    if (it.battery_max_a) parts.push(`battery ${it.battery_max_a} A${it.charge_a_max ? ` / charge ${it.charge_a_max} A` : ''}`)
    if (it.charge_v_max) parts.push(`${it.charge_v_max} V${it.battery_class ? ` ${it.battery_class}` : ''} port`)
    if (it.mppt_count) parts.push(`${it.mppt_count} MPPT${it.mppt_currents_a ? ` (${it.mppt_currents_a} A)` : it.mppt_max_a ? ` × ${it.mppt_max_a} A` : ''}`)
    return (
      <>
        <span className={`badge ${it.grid_interactive === true ? 'good' : it.grid_interactive === false ? 'neutral' : 'bad'}`} title={GRID_TITLE[grid]}>
          {parts[0]}
        </span>{' '}
        {badge}
        {parts.length > 1 && <div className="muted" style={{ fontSize: 11 }}>{parts.slice(1).join(' · ')}</div>}
        {held}
        {over}
      </>
    )
  }
  if (it.category === 'Battery') {
    const parts = []
    if (it.nominal_v) parts.push(`${it.nominal_v} V`)
    if (it.capacity_ah) parts.push(`${it.capacity_ah} Ah`)
    if (it.continuous_a) parts.push(`${it.continuous_a} A max`)
    if (it.discharge_a_recommended) parts.push(`${it.discharge_a_recommended} A recommended`)
    if (it.charge_a_max) parts.push(`charge ${it.charge_a_max} A`)
    if (it.charge_v_max) parts.push(`ceiling ${it.charge_v_max} V`)
    return (
      <>
        {it.continuous_a ? `${it.continuous_a} A continuous` : <span className="muted">no continuous A</span>} {badge}
        {parts.length > 0 && <div className="muted" style={{ fontSize: 11 }}>{parts.join(' · ')}</div>}
        {held}
        {over}
      </>
    )
  }
  if (it.category === 'Solar Panel') {
    const parts = []
    if (it.voc_v) parts.push(`Voc ${it.voc_v} V`)
    if (it.vmp_v) parts.push(`Vmp ${it.vmp_v} V`)
    if (it.isc_a) parts.push(`Isc ${it.isc_a} A`)
    if (it.imp_a) parts.push(`Imp ${it.imp_a} A`)
    if (it.max_system_voltage_v) parts.push(`${it.max_system_voltage_v} V system`)
    return (
      <>
        {parts.length ? parts.slice(0, 2).join(' · ') : <span className="muted">no Voc/Isc</span>} {badge}
        {parts.length > 2 && <div className="muted" style={{ fontSize: 11 }}>{parts.slice(2).join(' · ')}</div>}
        {over}
      </>
    )
  }
  // round 13: the design analysis's figures on the wires, the raceways and the breakers
  if (it.category === 'Wires and Terminations' || it.category === 'Enclosures and Raceways' || it.category === 'Protective Devices') {
    const parts = []
    if (it.overall_area_mm2) parts.push(`${it.overall_area_mm2} mm² overall`)
    if (it.insulation_c) parts.push(`${it.insulation_c} °C`)
    if (it.ampacity_a) parts.push(`${it.ampacity_a} A`)
    if (it.inner_diameter_mm) parts.push(`inside Ø ${it.inner_diameter_mm} mm`)
    if (it.aic_ka) parts.push(`${it.aic_ka} kA AIC`)
    return parts.length ? <span className="muted" style={{ fontSize: 11 }}>{parts.join(' · ')}</span> : null
  }
  return it.category === 'All-in-one System' ? badge : ''
}

/** The key figures of a datasheet row without an item, in the category's own words. */
function rowFigures(r: DatasheetRow): string {
  const f = { ...r.held_fields, ...r.fields }
  const g = (k: string, unit: string) => (f[k] != null && f[k] !== '' ? `${f[k]} ${unit}`.trim() : null)
  const parts =
    r.category === 'Solar Panel'
      ? [g('rating', 'W'), g('voc_v', 'V Voc'), g('vmp_v', 'V Vmp'), g('isc_a', 'A Isc'), g('imp_a', 'A Imp'), g('max_system_voltage_v', 'V system')]
      : r.category === 'Battery'
        ? [g('nominal_v', 'V'), g('capacity_ah', 'Ah'), g('rating', 'kWh'), g('continuous_a', 'A max'), g('discharge_a_recommended', 'A recommended'), g('charge_a_max', 'A charge'), g('charge_v_max', 'V ceiling'), g('battery_class', '')]
        : [f.inverter_type ? TYPE_LABEL[String(f.inverter_type)] ?? String(f.inverter_type) : null, f.phase ? `${f.phase}-phase` : null, g('rating', 'kW'), g('charge_v_max', 'V'), g('battery_max_a', 'A discharge'), g('charge_a_max', 'A charge'), f.mppt_currents_a ? `MPPT ${f.mppt_currents_a} A` : null, g('battery_class', 'port')]
  return parts.filter(Boolean).join(' · ')
}

/** Per category (brief 2.5): the datasheet rows without a priced item, with "Link to item…" and "Add as item", and the items without a datasheet. */
function DatasheetBlocks({ ds, category, owner, suppliers, onChanged }: { ds: DatasheetPage; category: string; owner: boolean; suppliers: MaterialSupplier[]; onChanged: (msg: string) => void }) {
  const [link, setLink] = useState<Record<number, string>>({})
  const [codes, setCodes] = useState<Record<number, string>>({})
  const [sups, setSups] = useState<Record<number, string>>({})
  const [error, setError] = useState<string | null>(null)
  const cats = EQUIPMENT.filter((c) => !category || c === category)
  const heldAction = async (r: DatasheetRow) => {
    setError(null)
    try {
      if (r.held_applied_at) {
        const x = await api.withdrawHeld(r.id)
        onChanged(`Held figures withdrawn on ${r.model}${x.changes.length ? `: ${x.changes.join(', ')}` : ''}.`)
      } else {
        const x = await api.applyHeld(r.id)
        onChanged(`Held figures applied on ${r.model}${x.changes.length ? `: ${x.changes.join(', ')}` : ' (no priced item yet; they go on once it is linked)'}.`)
      }
    } catch (e) {
      setError((e as Error).message)
    }
  }
  const doLink = async (id: number) => {
    const code = link[id]
    if (!code) return
    setError(null)
    try {
      const r = await api.linkDatasheet(id, code)
      onChanged(`Linked to ${r.code}${r.changes.length ? `: ${r.changes.join(', ')}` : ''}.`)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  const doAdd = async (id: number) => {
    const code = (codes[id] || '').trim().toUpperCase()
    if (!code) return
    setError(null)
    try {
      const it = await api.addDatasheetItem(id, code, sups[id] || '')
      onChanged(`Added ${it.code} (inactive, list price 0${it.supplier ? '' : ', no supplier yet'}): type the price${it.supplier ? '' : ' and the supplier'} and activate it.`)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  return (
    <>
      {error && <div className="banner bad">{error}</div>}
      {cats.map((cat) => {
        const orphan = ds.rows.filter((r) => r.category === cat && !r.matched_code)
        const heldRows = ds.rows.filter((r) => r.category === cat && r.held)
        const items = Object.values(ds.items).filter((i) => i.category === cat)
        const without = items.filter((i) => !i.datasheet)
        if (!orphan.length && !without.length && !heldRows.length) return null
        return (
          <div key={cat} data-testid={`datasheet-blocks-${cat}`}>
            {heldRows.length > 0 && (
              <details className="more" data-testid="held-rows">
                <summary>
                  {cat}: held rows ({heldRows.length})
                </summary>
                <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                  Figures the brief holds back until you answer: the Solis grid-tie units' battery figures (6.4) and a battery maximum above 1 C (6.8). Apply a row on
                  your word; the figures then stay on the item through every later import.
                </div>
                <div className="table-wrap" style={{ marginTop: 6 }}>
                  <table className="materials">
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>Item</th>
                        <th>Held figures</th>
                        <th>State</th>
                        {owner && <th></th>}
                      </tr>
                    </thead>
                    <tbody>
                      {heldRows.map((r) => (
                        <tr key={r.id}>
                          <td data-label="Model" className="cell-main">
                            {r.brand} {r.model}
                            <div className="muted" style={{ fontSize: 11 }}>
                              {r.source_file}, {r.source_sheet} row {r.source_row}
                            </div>
                          </td>
                          <td data-label="Item">{r.matched_code ?? <span className="muted">no priced item</span>}</td>
                          <td data-label="Held figures" className="muted" style={{ fontSize: 12 }}>
                            {Object.entries(r.held_fields)
                              .map(([k, v]) => `${k} ${fmtVal(v)}`)
                              .join(' · ')}
                          </td>
                          <td data-label="State">
                            {r.held_applied_at ? <span className="badge good">applied {fmtDate(r.held_applied_at)}</span> : <span className="badge neutral">held</span>}
                          </td>
                          {owner && (
                            <td className="cell-actions" style={{ whiteSpace: 'nowrap' }}>
                              <button type="button" className="small" onClick={() => heldAction(r)}>
                                {r.held_applied_at ? 'Withdraw' : 'Apply held figures'}
                              </button>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            )}
            {orphan.length > 0 && (
              <details className="more" data-testid="datasheet-only">
                <summary>
                  {cat}: datasheet rows without a priced item ({orphan.length})
                </summary>
                <div className="table-wrap" style={{ marginTop: 6 }}>
                  <table className="materials">
                    <thead>
                      <tr>
                        <th>Brand</th>
                        <th>Model</th>
                        <th>Figures</th>
                        <th>Notes</th>
                        {owner && <th></th>}
                      </tr>
                    </thead>
                    <tbody>
                      {orphan.map((r) => (
                        <tr key={r.id}>
                          <td data-label="Brand">
                            {r.brand}
                            {r.brand_in_model && <div className="muted" style={{ fontSize: 11 }}>model text says {r.brand_in_model}</div>}
                          </td>
                          <td data-label="Model" className="cell-main">
                            {r.model}
                            <div className="muted" style={{ fontSize: 11 }}>
                              {r.source_file}, {r.source_sheet} row {r.source_row}
                              {r.held && ' · held'}
                            </div>
                          </td>
                          <td data-label="Figures" className="muted" style={{ fontSize: 12 }}>
                            {rowFigures(r)}
                          </td>
                          <td data-label="Notes" className="muted" style={{ fontSize: 11 }}>
                            {r.match_note}
                            {r.notices.length > 0 && (
                              <details>
                                <summary>{r.notices.length} notice{r.notices.length === 1 ? '' : 's'}</summary>
                                <ul style={{ margin: '4px 0 0 16px' }}>
                                  {r.notices.map((n, i) => (
                                    <li key={i}>{n}</li>
                                  ))}
                                </ul>
                              </details>
                            )}
                          </td>
                          {owner && (
                            <td className="cell-actions" style={{ whiteSpace: 'nowrap' }}>
                              <div className="row" style={{ gap: 4, alignItems: 'center' }}>
                                <select aria-label={`Link ${r.model} to item`} value={link[r.id] ?? ''} onChange={(e) => setLink({ ...link, [r.id]: e.target.value })} style={{ maxWidth: 220 }}>
                                  <option value="">Link to item…</option>
                                  {items.map((i) => (
                                    <option key={i.code} value={i.code}>
                                      {i.code} {i.name}
                                    </option>
                                  ))}
                                </select>
                                <button type="button" className="small" disabled={!link[r.id]} onClick={() => doLink(r.id)}>
                                  Link
                                </button>
                              </div>
                              <div className="row" style={{ gap: 4, alignItems: 'center', marginTop: 4 }}>
                                <input aria-label={`Code for ${r.model}`} placeholder="New code" value={codes[r.id] ?? ''} onChange={(e) => setCodes({ ...codes, [r.id]: e.target.value })} style={{ width: 120 }} />
                                <select aria-label={`Supplier for ${r.model}`} value={sups[r.id] ?? ''} onChange={(e) => setSups({ ...sups, [r.id]: e.target.value })} style={{ maxWidth: 150 }}>
                                  <option value="">Supplier…</option>
                                  {suppliers.map((sp) => (
                                    <option key={sp.name} value={sp.name}>
                                      {sp.name}
                                    </option>
                                  ))}
                                </select>
                                <button type="button" className="small" disabled={!(codes[r.id] || '').trim()} onClick={() => doAdd(r.id)}>
                                  Add as item
                                </button>
                              </div>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            )}
            {without.length > 0 && (
              <details className="more" data-testid="items-without-datasheet">
                <summary>
                  {cat}: items without a datasheet ({without.length})
                </summary>
                <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                  No row of the maker's sheets names these; their figures are the remarks' or typed. Send the maker's sheet, or link a row above.
                </div>
                <ul style={{ margin: '4px 0 0 18px', fontSize: 13 }}>
                  {without.map((i) => (
                    <li key={i.code}>
                      <span className="code">{i.code}</span> {i.name}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )
      })}
    </>
  )
}

function ItemForm({ it, set, codeEditable, info }: { it: ItemDraft; set: (p: Partial<ItemDraft>) => void; codeEditable: boolean; info?: DatasheetItemInfo | null }) {
  return (
    <div>
      <div className="row">
        <Field label="Code" width={140}>
          <input value={it.code} disabled={!codeEditable} onChange={(e) => set({ code: e.target.value.toUpperCase() })} placeholder="PLD-ACC-001" />
        </Field>
        <Field label="Category">
          <input list="material-categories" value={it.category} onChange={(e) => set({ category: e.target.value })} />
        </Field>
        <Field label="Supplier">
          <input list="material-suppliers" value={it.supplier} onChange={(e) => set({ supplier: e.target.value })} />
        </Field>
        <Field label="Name" width={320}>
          <input value={it.name} onChange={(e) => set({ name: e.target.value })} />
        </Field>
      </div>
      <div className="row" style={{ marginTop: 6 }}>
        <Field label="Spec" width={320}>
          <input value={it.spec} onChange={(e) => set({ spec: e.target.value })} />
        </Field>
        <Field label="Unit" width={80}>
          <input value={it.unit} onChange={(e) => set({ unit: e.target.value })} />
        </Field>
        <Field label="Sold as" width={100}>
          <input value={it.sold_as} onChange={(e) => set({ sold_as: e.target.value })} />
        </Field>
        <Field label="List price" width={140} unit="₱">
          <NumberInput value={it.list_price} onChange={(v) => set({ list_price: v ?? 0 })} min={0} decimals={2} />
        </Field>
        <Field label="Rating" width={210} unit={<input value={it.rating_unit} onChange={(e) => set({ rating_unit: e.target.value })} placeholder="W, kW, kWh, A" aria-label="Rating unit" style={{ width: 92 }} />}>
          <NumberInput value={it.rating} onChange={(v) => set({ rating: v })} allowEmpty decimals={2} />
        </Field>
      </div>
      <div className="row" style={{ marginTop: 6 }}>
        <Field label="Weight" width={120} unit="kg">
          <NumberInput value={it.weight_kg} onChange={(v) => set({ weight_kg: v ?? 0 })} min={0} decimals={2} />
        </Field>
        <Field label="Volume" width={120} unit="m³">
          <NumberInput value={it.volume_m3} onChange={(v) => set({ volume_m3: v ?? 0 })} min={0} decimals={it.volume_m3 > 0 && it.volume_m3 < 0.01 ? 3 : 2} />
        </Field>
        <Field label="Storage" width={110} unit="₱">
          <NumberInput value={it.storage} onChange={(v) => set({ storage: v ?? 0 })} min={0} decimals={0} />
        </Field>
        <Field label="Panel length" width={130} unit="m">
          <NumberInput value={it.panel_length_m} onChange={(v) => set({ panel_length_m: v })} allowEmpty decimals={3} />
        </Field>
        <Field label="Panel width" width={130} unit="m">
          <NumberInput value={it.panel_width_m} onChange={(v) => set({ panel_width_m: v })} allowEmpty decimals={3} />
        </Field>
        <Field label="Price list date" width={130}>
          <input value={it.price_list_date} onChange={(e) => set({ price_list_date: e.target.value })} />
        </Field>
        <Field label="Remarks" width={240}>
          <input value={it.remarks} onChange={(e) => set({ remarks: e.target.value })} />
        </Field>
      </div>
      {info?.datasheet && (
        <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
          Datasheet: {info.datasheet.file}, {fmtDate(info.datasheet.date)} ({info.datasheet.sheet} row {info.datasheet.row}, matched {info.datasheet.tier}). A figure typed over the datasheet's is
          kept on the next import; "reset to datasheet" puts the sheet's figure back.
          {info.datasheet.notices.length > 0 && (
            <ul style={{ margin: '4px 0 0 18px' }}>
              {info.datasheet.notices.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <ElectricalFields it={it} set={set} info={info} />
    </div>
  )
}

export default function MaterialsPage({ user }: { user: Me }) {
  const owner = user.role === 'owner'
  const [status, setStatus] = useState<PricingStatus | null>(null)
  const [cats, setCats] = useState<{ name: string; count: number }[]>([])
  const [suppliers, setSuppliers] = useState<MaterialSupplier[]>([])
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [supplier, setSupplier] = useState('')
  const [inactive, setInactive] = useState(false)
  const [items, setItems] = useState<MaterialItem[]>([])
  const [ds, setDs] = useState<DatasheetPage | null>(null)
  const [editing, setEditing] = useState<MaterialItem | null>(null)
  const [creating, setCreating] = useState<ItemDraft | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [keepConfig, setKeepConfig] = useState(true)
  const [applyHeld, setApplyHeld] = useState(false)
  const [report, setReport] = useState<ImportReport | null>(null)
  const [dsReport, setDsReport] = useState<DatasheetReport | null>(null)
  const [sort, setSort] = useState<{ key: 'code' | 'category' | 'name' | 'supplier' | 'list_price'; dir: 1 | -1 }>({ key: 'code', dir: 1 })
  const [limit, setLimit] = useState(50)
  const fileRef = useRef<HTMLInputElement>(null)
  const dsFileRef = useRef<HTMLInputElement>(null)

  const refreshMeta = useCallback(() => {
    api.pricingStatus().then(setStatus).catch(() => setStatus(null))
    api.materialCategories().then(setCats).catch(() => setCats([]))
    api.materialSuppliers().then(setSuppliers).catch(() => setSuppliers([]))
    api.datasheets().then(setDs).catch(() => setDs(null))
  }, [])
  const search = useCallback(() => {
    api
      .materials({ q, category: category || undefined, supplier: supplier || undefined, include_inactive: inactive, limit: 400 })
      .then((r) => {
        setItems(r)
        setLimit(50)
      })
      .catch((e) => setError(e.message))
  }, [q, category, supplier, inactive])
  const sorted = [...items].sort((a, b) => {
    const x = a[sort.key] ?? ''
    const y = b[sort.key] ?? ''
    return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * sort.dir
  })
  const shown = sorted.slice(0, limit)
  const sortBy = (key: typeof sort.key) => setSort((s) => (s.key === key ? { key, dir: s.dir === 1 ? -1 : 1 } : { key, dir: 1 }))
  const arrow = (key: typeof sort.key) => (sort.key === key ? (sort.dir === 1 ? ' ▲' : ' ▼') : '')
  const info = (code: string) => ds?.items[code] ?? null

  useEffect(() => {
    refreshMeta()
  }, [refreshMeta])
  useEffect(() => {
    const t = window.setTimeout(search, 150)
    return () => window.clearTimeout(t)
  }, [search])

  const saveEdit = async () => {
    if (!editing) return
    setError(null)
    try {
      const { code, updated_at, ...patch } = editing
      void updated_at
      await api.updateMaterial(code, patch)
      setEditing(null)
      setMsg(`Saved ${code}.`)
      refreshMeta()
      search()
    } catch (e) {
      setError((e as Error).message)
    }
  }
  const saveNew = async () => {
    if (!creating) return
    setError(null)
    try {
      await api.createMaterial(creating)
      setMsg(`Added ${creating.code}.`)
      setCreating(null)
      refreshMeta()
      search()
    } catch (e) {
      setError((e as Error).message)
    }
  }
  const toggleActive = async (it: MaterialItem) => {
    await api.updateMaterial(it.code, { active: !it.active })
    search()
  }
  const doImport = async (file: File) => {
    setError(null)
    setReport(null)
    try {
      const r = await api.importMaterials(file, keepConfig)
      setReport(r)
      refreshMeta()
      search()
    } catch (e) {
      setError((e as Error).message)
    }
  }
  const doSeed = async () => {
    setError(null)
    try {
      setReport(await api.importSeed(keepConfig))
      refreshMeta()
      search()
    } catch (e) {
      setError((e as Error).message)
    }
  }
  const doDatasheets = async (files: FileList, dryRun: boolean) => {
    setError(null)
    setDsReport(null)
    const merged: DatasheetReport = { lines: [], counts: {}, changed_codes: [], projects_using_changed: [], summary: '', dry_run: dryRun, files: [] }
    try {
      for (const f of Array.from(files)) {
        const r = await api.importDatasheet(f, applyHeld, dryRun)
        merged.lines.push(...r.lines)
        merged.changed_codes.push(...r.changed_codes)
        merged.files.push(...r.files)
        for (const [k, v] of Object.entries(r.counts)) merged.counts[k] = (merged.counts[k] ?? 0) + v
        merged.projects_using_changed = Array.from(new Set([...merged.projects_using_changed, ...r.projects_using_changed]))
      }
      const c = merged.counts
      merged.summary = `rows read ${c.rows ?? 0}, matched ${c.matched ?? 0}, specs-only ${c.specs_only ?? 0}, skipped ${c.skipped ?? 0}, held ${c.held ?? 0}, items changed ${c.items_changed ?? 0}, items untouched ${c.items_untouched ?? 0}, priced projects that use a changed item ${merged.projects_using_changed.length}${dryRun ? ' (dry run: nothing written)' : ''}`
      setDsReport(merged)
      refreshMeta()
      search()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <>
      <datalist id="material-categories">
        {cats.map((c) => (
          <option key={c.name} value={c.name} />
        ))}
      </datalist>
      <datalist id="material-suppliers">
        {suppliers.map((s) => (
          <option key={s.name} value={s.name} />
        ))}
      </datalist>
      <div className="card">
        <h2>Materials list</h2>
        <div className="muted">
          {status ? `${status.item_count} items from ${status.supplier_count} suppliers` : '-'}
          {status?.imported_from && ` · last import ${status.imported_from}${status.imported_at ? ` on ${fmtDateTime(status.imported_at)}` : ''}`}. The app is the master:
          edits here are used for pricing. Re-importing a workbook updates items by code and keeps panel dimensions typed here; the datasheet figures go back on after it.
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <Field label="Search" width={0}>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="code, name or spec" />
          </Field>
          <Field label="Category" width={200}>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All</option>
              {cats.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name} ({c.count})
                </option>
              ))}
            </select>
          </Field>
          <Field label="Supplier" width={180}>
            <select value={supplier} onChange={(e) => setSupplier(e.target.value)}>
              <option value="">All</option>
              {suppliers.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
          <label className="check narrow">
            <input type="checkbox" checked={inactive} onChange={(e) => setInactive(e.target.checked)} /> <span>Show inactive</span>
          </label>
          {owner && (
            <div className="narrow">
              <button type="button" className="primary" onClick={() => setCreating(blankItem())}>
                New item
              </button>
            </div>
          )}
        </div>
        {error && (
          <div className="banner bad" style={{ marginTop: 8 }}>
            {error}
          </div>
        )}
        {msg && (
          <div className="muted" style={{ marginTop: 6 }}>
            {msg}
          </div>
        )}
        {creating && (
          <div className="set-card" style={{ marginTop: 10 }}>
            <h3 style={{ marginTop: 0 }}>New item</h3>
            <ItemForm it={creating} set={(p) => setCreating({ ...creating, ...p })} codeEditable />
            <div style={{ marginTop: 8 }}>
              <button type="button" className="primary" onClick={saveNew} disabled={!creating.code || !creating.name || !creating.supplier}>
                Add
              </button>{' '}
              <button type="button" onClick={() => setCreating(null)}>
                Cancel
              </button>
            </div>
          </div>
        )}
        <div className="muted" style={{ marginTop: 10 }}>
          {items.length === 0 ? '' : `${items.length} ${items.length === 1 ? 'item' : 'items'}${items.length >= 400 ? ' (first 400; narrow the search)' : ''}`}
        </div>
        <div className="table-wrap table-sticky" style={{ marginTop: 6 }}>
          <table className="materials">
            <thead>
              <tr>
                <th className="sortable" onClick={() => sortBy('code')}>Code{arrow('code')}</th>
                <th className="sortable" onClick={() => sortBy('category')}>Category{arrow('category')}</th>
                <th className="sortable" onClick={() => sortBy('name')}>Item{arrow('name')}</th>
                <th className="sortable" onClick={() => sortBy('supplier')}>Supplier{arrow('supplier')}</th>
                <th className="num">Rating</th>
                <th className="num sortable" onClick={() => sortBy('list_price')}>List price{arrow('list_price')}</th>
                <th>Unit</th>
                <th className="num">Weight (kg)</th>
                <th>Panel size</th>
                <th>Electrical</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={11} className="muted">No items match. Try part of the code or name.</td>
                </tr>
              )}
              {shown.map((it) =>
                editing && editing.code === it.code ? (
                  <tr key={it.code}>
                    <td colSpan={11}>
                      <ItemForm it={editing} set={(p) => setEditing({ ...editing, ...p })} codeEditable={false} info={info(it.code)} />
                      <div style={{ marginTop: 8 }}>
                        <button type="button" className="primary" onClick={saveEdit}>
                          Save
                        </button>{' '}
                        <button type="button" onClick={() => setEditing(null)}>
                          Cancel
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={it.code} style={it.active ? undefined : { opacity: 0.5 }}>
                    <td className="code" data-label="Code">{it.code}</td>
                    <td data-label="Category">{it.category}</td>
                    <td data-label="Item" className="cell-main">
                      {it.name}
                      {it.spec && (
                        <div className="muted" style={{ fontSize: 11 }}>
                          {it.spec}
                        </div>
                      )}
                    </td>
                    <td data-label="Supplier">{it.supplier}</td>
                    <td className="num" data-label="Rating">{it.rating != null ? `${it.rating} ${it.rating_unit}` : ''}</td>
                    <td className="num" data-label="List price">{php(it.list_price)}</td>
                    <td data-label="Unit">{it.unit}</td>
                    <td className="num" data-label="Weight (kg)">{it.weight_kg ? it.weight_kg.toFixed(2) : ''}</td>
                    <td data-label="Panel size">
                      {it.category === 'Solar Panel'
                        ? it.panel_length_m && it.panel_width_m
                          ? `${it.panel_length_m} × ${it.panel_width_m} m`
                          : <span className="badge bad">No size</span>
                        : ''}
                    </td>
                    <td data-label="Electrical">{electricalSummary(it, info(it.code))}</td>
                    <td style={{ whiteSpace: 'nowrap' }} className="cell-actions">
                      {owner && (
                        <>
                          <button type="button" className="toggle link" onClick={() => setEditing(it)}>
                            Edit
                          </button>
                          <button type="button" className="toggle link" onClick={() => toggleActive(it)}>
                            {it.active ? 'Deactivate' : 'Activate'}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
        {sorted.length > limit && (
          <div style={{ marginTop: 8 }}>
            <button type="button" onClick={() => setLimit((l) => l + 50)}>
              Show 50 more ({sorted.length - limit} left)
            </button>
          </div>
        )}
      </div>

      {ds && ds.rows.length > 0 && (
        <div className="card" data-testid="datasheets-card">
          <h2>Datasheets</h2>
          <div className="muted">
            {ds.rows.length} rows from the maker's workbooks, {ds.rows.filter((r) => r.matched_code).length} matched to an item
            {status?.datasheets_imported_from ? ` · last import ${status.datasheets_imported_from}${status.datasheets_imported_at ? ` on ${fmtDateTime(status.datasheets_imported_at)}` : ''}` : ''}. A row without a
            priced item is "datasheet only" until it is linked or added; an item without a row keeps its remarks' figures. Held rows (the Solis grid-tie
            units' battery figures, a battery maximum above 1 C) wait on the owner's answer.
          </div>
          <div style={{ marginTop: 6 }}>
            <DatasheetBlocks
              ds={ds}
              category={category}
              owner={owner}
              suppliers={suppliers}
              onChanged={(m) => {
                setMsg(m)
                refreshMeta()
                search()
              }}
            />
          </div>
        </div>
      )}

      {!owner && (
        <div className="card">
          <h2>Changing the list</h2>
          <div className="muted">Prices, new items and the workbook import are the owner's to change. Tell the owner what you found cheaper or out of stock.</div>
        </div>
      )}
      {owner && (
      <div className="card">
        <h2>Import workbook</h2>
        <div className="muted">
          Upload the materials workbook (.xlsx, same layout as PLD_Materials_DB). Items are matched by code: existing rows are updated, new codes are added, items missing from the
          workbook are left as they are.
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <div className="narrow">
            <input ref={fileRef} type="file" accept=".xlsx" style={{ width: 'auto' }} />
          </div>
          <label className="check">
            <input type="checkbox" checked={keepConfig} onChange={(e) => setKeepConfig(e.target.checked)} />
            <span>Keep the app's pricing settings (untick to reload the workbook's drivers, rates and routes too)</span>
          </label>
          <div className="narrow inline">
            <button
              type="button"
              className="primary"
              onClick={() => {
                const f = fileRef.current?.files?.[0]
                if (f) doImport(f)
              }}
            >
              Import
            </button>
            {status?.seed_available && (
              <button type="button" onClick={doSeed}>
                Reload the built-in workbook
              </button>
            )}
          </div>
        </div>
        {report && (
          <div className="banner info" style={{ marginTop: 8 }}>
            Added {report.added} items, updated {report.updated}, {report.suppliers} suppliers.
            {report.warnings.length > 0 && (
              <ul style={{ margin: '6px 0 0 18px' }}>
                {report.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        <h2 style={{ marginTop: 16 }}>Import datasheet workbooks</h2>
        <div className="muted">
          The maker's datasheet workbooks (panels, inverters, batteries; the kind is read from the sheets). Every row is kept as a specs row and matched to an item
          by its model; the figures go on the item above the remarks and below what you typed here. Nothing on a sheet is corrected: an irregular cell is flagged in
          the report, and the figures the brief holds back (the Solis grid-tie rows' battery figures, a battery maximum above 1 C) are applied only when you say so.
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <div className="narrow">
            <input ref={dsFileRef} type="file" accept=".xlsx" multiple style={{ width: 'auto' }} aria-label="Datasheet workbooks" />
          </div>
          <label className="check">
            <input type="checkbox" checked={applyHeld} onChange={(e) => setApplyHeld(e.target.checked)} />
            <span>Apply the held figures too (only on the owner's word: brief 6.4 and 6.8)</span>
          </label>
          <div className="narrow inline">
            <button
              type="button"
              className="primary"
              onClick={() => {
                const f = dsFileRef.current?.files
                if (f && f.length) doDatasheets(f, false)
              }}
            >
              Import datasheets
            </button>
            <button
              type="button"
              onClick={() => {
                const f = dsFileRef.current?.files
                if (f && f.length) doDatasheets(f, true)
              }}
            >
              Dry run
            </button>
          </div>
        </div>
        {dsReport && (
          <div className="banner info" style={{ marginTop: 8 }} data-testid="datasheet-report">
            {dsReport.summary}
            {dsReport.projects_using_changed.length > 0 && <div>Projects to re-price on their next Calculate: {dsReport.projects_using_changed.join(', ')}.</div>}
            <details className="more">
              <summary>{dsReport.lines.length} rows</summary>
              <ul style={{ margin: '6px 0 0 18px', fontSize: 12, maxHeight: 320, overflow: 'auto' }}>
                {dsReport.lines.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </details>
          </div>
        )}
      </div>
      )}
    </>
  )
}
