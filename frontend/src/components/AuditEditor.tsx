import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import {
  newAppliance, newBill, newWindow, windowHours,
  type ApplianceCategory, type ApplianceEntry, type BillEntry, type CatalogItem, type EnergyAudit, type SystemSettings, type UsageWindow,
} from '../types'
import NumberInput from './NumberInput'

const DAY_LABELS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
const MONTH_LABELS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']

function Toggle({ on, label, onClick, title }: { on: boolean; label: string; onClick: () => void; title: string }) {
  return (
    <button type="button" className={`toggle ${on ? 'on' : ''}`} onClick={onClick} title={title}>
      {label}
    </button>
  )
}

function WindowRow({ w, onChange, onRemove }: { w: UsageWindow; onChange: (w: UsageWindow) => void; onRemove: () => void }) {
  const flip = (list: number[], v: number) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v].sort((a, b) => a - b))
  const allDays = w.days.length === 7
  const allMonths = w.months.length === 12
  return (
    <div className="window-row">
      <input type="time" value={w.start} onChange={(e) => onChange({ ...w, start: e.target.value })} />
      <span className="muted">to</span>
      <input type="time" value={w.end} onChange={(e) => onChange({ ...w, end: e.target.value })} />
      <span className="muted hours">{windowHours(w).toFixed(2)} h</span>
      <span className="toggles">
        {DAY_LABELS.map((l, i) => (
          <Toggle key={i} on={w.days.includes(i)} label={l} title={['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i]} onClick={() => onChange({ ...w, days: flip(w.days, i) })} />
        ))}
        <button type="button" className="toggle link" onClick={() => onChange({ ...w, days: allDays ? [0, 1, 2, 3, 4] : [0, 1, 2, 3, 4, 5, 6] })}>
          {allDays ? 'weekdays' : 'all days'}
        </button>
      </span>
      <span className="toggles">
        {MONTH_LABELS.map((l, i) => (
          <Toggle key={i} on={w.months.includes(i + 1)} label={l} title={['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i]} onClick={() => onChange({ ...w, months: flip(w.months, i + 1) })} />
        ))}
        <button type="button" className="toggle link" onClick={() => onChange({ ...w, months: allMonths ? [3, 4, 5] : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] })}>
          {allMonths ? 'summer only' : 'all months'}
        </button>
      </span>
      <button type="button" className="danger small" onClick={onRemove}>
        x
      </button>
    </div>
  )
}

function NameWithSuggestions({ value, onChange, onPick }: { value: string; onChange: (v: string) => void; onPick: (c: CatalogItem) => void }) {
  const [items, setItems] = useState<CatalogItem[]>([])
  const [open, setOpen] = useState(false)
  const timer = useRef<number | null>(null)
  useEffect(() => {
    if (!open || value.trim().length < 2) {
      setItems([])
      return
    }
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => {
      api.searchAppliances(value).then(setItems).catch(() => setItems([]))
    }, 200)
  }, [value, open])
  return (
    <div className="suggest">
      <input value={value} placeholder="e.g. Split inverter AC 2.5HP" onChange={(e) => onChange(e.target.value)} onFocus={() => setOpen(true)} onBlur={() => window.setTimeout(() => setOpen(false), 150)} />
      {open && items.length > 0 && (
        <div className="suggest-list">
          {items.map((c) => (
            <div key={c.id} className="suggest-item" onMouseDown={() => onPick(c)}>
              <b>{c.name}</b> {c.brand} {c.model} <span className="muted">{c.input_power_w} W</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function AuditEditor({ audit, onChange }: { audit: EnergyAudit; onChange: (a: EnergyAudit) => void }) {
  const [cats, setCats] = useState<ApplianceCategory[]>([])
  const [openId, setOpenId] = useState<string | null>(null)
  useEffect(() => {
    api.categories().then(setCats).catch(() => setCats([]))
  }, [])
  const catOf = (id: string) => cats.find((c) => c.id === id)

  const setApps = (appliances: ApplianceEntry[]) => onChange({ ...audit, appliances })
  const updateApp = (i: number, patch: Partial<ApplianceEntry>) => setApps(audit.appliances.map((a, j) => (j === i ? { ...a, ...patch } : a)))
  const setBills = (bills: BillEntry[]) => onChange({ ...audit, bills })
  const updateBill = (i: number, patch: Partial<BillEntry>) => setBills(audit.bills.map((b, j) => (j === i ? { ...b, ...patch } : b)))
  const setSystem = (patch: Partial<SystemSettings>) => onChange({ ...audit, system: { ...audit.system, ...patch } })

  const addApp = () => {
    const a = newAppliance()
    setApps([...audit.appliances, a])
    setOpenId(a.id)
  }
  const duplicateApp = (i: number) => {
    const src = audit.appliances[i]
    const copy: ApplianceEntry = { ...src, id: Math.random().toString(36).slice(2, 10), windows: src.windows.map((w) => ({ ...w, days: [...w.days], months: [...w.months] })) }
    setApps([...audit.appliances.slice(0, i + 1), copy, ...audit.appliances.slice(i + 1)])
    setOpenId(copy.id)
  }

  return (
    <div>
      <h3>Appliances</h3>
      <div className="muted" style={{ marginBottom: 8 }}>
        Nameplate input watts per unit. Add the same appliance twice with different quantities when groups run at different hours, for example lights in different areas.
        Duty factor defaults from the category; leave it blank unless you measured the real draw.
      </div>
      <div className="table-wrap">
        <table className="appliances">
          <thead>
            <tr>
              <th>Appliance</th>
              <th>Category</th>
              <th className="num">W (nameplate)</th>
              <th className="num">Qty</th>
              <th className="num">Duty factor</th>
              <th>Status</th>
              <th className="num">When used</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {audit.appliances.map((a, i) => {
              const c = catOf(a.category)
              const open = openId === a.id
              const useDays = new Set(a.windows.flatMap((w) => w.days)).size
              const hoursPerUseDay = useDays ? a.windows.reduce((s, w) => s + windowHours(w) * w.days.length, 0) / useDays : 0
              return [
                <tr key={a.id}>
                  <td className="cell-main cell-sticky" style={{ minWidth: 180 }} data-label="Appliance">
                    <NameWithSuggestions
                      value={a.name}
                      onChange={(name) => updateApp(i, { name })}
                      onPick={(cat) => updateApp(i, { name: cat.name, brand: cat.brand, model: cat.model, category: cat.category, input_power_w: cat.input_power_w })}
                    />
                    <div className="inline sub-fields">
                      <input value={a.brand} placeholder="Brand" onChange={(e) => updateApp(i, { brand: e.target.value })} />
                      <input value={a.model} placeholder="Model" onChange={(e) => updateApp(i, { model: e.target.value })} />
                    </div>
                  </td>
                  <td data-label="Category">
                    <select value={a.category} onChange={(e) => updateApp(i, { category: e.target.value })} title={c?.note} style={{ minWidth: 140 }}>
                      {cats.map((x) => (
                        <option key={x.id} value={x.id}>
                          {x.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td data-label="W (nameplate)">
                    <NumberInput value={a.input_power_w} onChange={(v) => updateApp(i, { input_power_w: v ?? 0 })} min={0} style={{ width: 80 }} />
                  </td>
                  <td data-label="Qty">
                    <NumberInput value={a.quantity} onChange={(v) => updateApp(i, { quantity: Math.max(1, Math.round(v ?? 1)) })} min={1} step={1} style={{ width: 60 }} />
                  </td>
                  <td data-label="Duty factor">
                    <NumberInput value={a.duty_factor} onChange={(v) => updateApp(i, { duty_factor: v })} allowEmpty min={0.01} max={1} step={0.05} placeholder={c ? c.duty.toFixed(2) : ''} style={{ width: 70 }} />
                  </td>
                  <td data-label="Status">
                    <select value={a.status} onChange={(e) => updateApp(i, { status: e.target.value as ApplianceEntry['status'] })} style={{ minWidth: 90 }}>
                      <option value="existing">In use</option>
                      <option value="future">Planned</option>
                      <option value="retiring">Being removed</option>
                    </select>
                  </td>
                  <td className="num" data-label="When used">
                    <button type="button" className="small when-used" onClick={() => setOpenId(open ? null : a.id)}>
                      {a.windows.length} {a.windows.length === 1 ? 'window' : 'windows'} · {hoursPerUseDay.toFixed(1)} h × {useDays} d/wk {open ? '▴' : '▾'}
                    </button>
                  </td>
                  <td className="cell-actions">
                    <span className="inline">
                      <button type="button" className="small" onClick={() => duplicateApp(i)} title="Duplicate">
                        Copy
                      </button>
                      <button type="button" className="danger small" onClick={() => setApps(audit.appliances.filter((_, j) => j !== i))}>
                        Remove
                      </button>
                    </span>
                  </td>
                </tr>,
                open ? (
                  <tr key={a.id + '-w'} className="window-editor">
                    <td colSpan={8} className="cell-full">
                      {c && <div className="muted" style={{ marginBottom: 6 }}>{c.label}: {c.note}</div>}
                      {a.windows.map((w, k) => (
                        <WindowRow
                          key={k}
                          w={w}
                          onChange={(nw) => updateApp(i, { windows: a.windows.map((x, m) => (m === k ? nw : x)) })}
                          onRemove={() => updateApp(i, { windows: a.windows.filter((_, m) => m !== k) })}
                        />
                      ))}
                      <button type="button" className="small" onClick={() => updateApp(i, { windows: [...a.windows, newWindow()] })}>
                        Add usage window
                      </button>
                    </td>
                  </tr>
                ) : null,
              ]
            })}
          </tbody>
        </table>
      </div>
      {audit.appliances.length === 0 && <div className="muted" style={{ marginTop: 6 }}>No appliances yet. Add the big ones first: aircon, refrigerator, pump.</div>}
      <button type="button" onClick={addApp} style={{ marginTop: 8 }}>
        Add appliance
      </button>

      <h3>Electricity bill</h3>
      <div className="table-wrap">
        <table className="bills">
          <thead>
            <tr>
              <th>Billing month</th>
              <th className="num">kWh</th>
              <th className="num">Days in period</th>
              <th className="num">Amount (₱)</th>
              <th className="num">Generation charge (₱/kWh)</th>
              <th>Electric company</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {audit.bills.map((b, i) => (
              <tr key={b.id}>
                <td data-label="Billing month">
                  <input type="month" value={b.billing_month} onChange={(e) => updateBill(i, { billing_month: e.target.value })} />
                </td>
                <td data-label="kWh">
                  <NumberInput value={b.kwh} onChange={(v) => updateBill(i, { kwh: v ?? 0 })} min={0} />
                </td>
                <td data-label="Days in period">
                  <NumberInput value={b.days} onChange={(v) => updateBill(i, { days: v == null ? null : Math.round(v) })} allowEmpty min={20} max={40} step={1} placeholder="auto" />
                </td>
                <td data-label="Amount (₱)">
                  <NumberInput value={b.amount_php} onChange={(v) => updateBill(i, { amount_php: v })} allowEmpty min={0} placeholder="optional" />
                </td>
                <td data-label="Generation charge (₱/kWh)">
                  <NumberInput value={b.generation_rate_php_per_kwh ?? null} onChange={(v) => updateBill(i, { generation_rate_php_per_kwh: v })} allowEmpty min={0} step={0.01} decimals={2} placeholder="from the bill" />
                </td>
                <td data-label="Electric company">
                  <input value={b.utility} onChange={(e) => updateBill(i, { utility: e.target.value })} placeholder="Meralco, BATELEC II..." />
                </td>
                <td>
                  <button type="button" className="danger small" onClick={() => setBills(audit.bills.filter((_, j) => j !== i))}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {audit.bills.length === 0 && <div className="muted" style={{ marginTop: 6 }}>No bill yet. Add the latest bill: month, kWh and amount.</div>}
      <div className="hint" style={{ marginTop: 6 }}>
        Generation charge: the per-kWh generation rate in the bill's breakdown. Under net metering the electric company credits exported power at this rate, so
        the savings use it as the export credit; blank uses the figure in Settings › Customer savings.
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <div className="narrow">
          <button type="button" onClick={() => setBills([...audit.bills, newBill()])}>
            Add bill
          </button>
        </div>
        <label className="inline narrow" style={{ marginBottom: 0 }}>
          <input type="checkbox" checked={audit.reconcile} onChange={(e) => onChange({ ...audit, reconcile: e.target.checked })} style={{ width: 'auto' }} /> Scale the audit to match the bill
        </label>
      </div>

      <h3>System</h3>
      <div className="row">
        <div className="narrow" style={{ width: 220 }}>
          <label>System type</label>
          <select value={audit.system.kind} onChange={(e) => setSystem({ kind: e.target.value as SystemSettings['kind'] })}>
            <option value="net_metering">Net metering (no battery)</option>
            <option value="combination">Net metering + battery (hybrid)</option>
            <option value="off_grid">Battery first, no export (grid as backup)</option>
          </select>
        </div>
        {audit.system.kind === 'off_grid' && (
          <div className="narrow" style={{ width: 150 }}>
            <label>Design margin (× worst month)</label>
            <NumberInput value={audit.system.offgrid_pv_margin} onChange={(v) => setSystem({ offgrid_pv_margin: v ?? 1.25 })} min={1} max={2} step={0.05} />
          </div>
        )}

        <div className="narrow" style={{ width: 160 }}>
          <label>Inverter sizes available (kW)</label>
          <input
            defaultValue={audit.system.inverter_sizes_kw.join(', ')}
            onBlur={(e) => {
              const sizes = e.target.value.split(',').map((x) => parseFloat(x)).filter((x) => Number.isFinite(x) && x > 0)
              if (sizes.length) setSystem({ inverter_sizes_kw: sizes })
            }}
          />
        </div>
        <div className="narrow" style={{ width: 120 }}>
          <label>Surge allowance (× rated)</label>
          <NumberInput value={audit.system.inverter_surge_factor} onChange={(v) => setSystem({ inverter_surge_factor: v ?? 2 })} min={1} max={4} step={0.1} />
        </div>
        <div className="narrow" style={{ width: 120 }}>
          <label>Max PV-to-inverter ratio</label>
          <NumberInput value={audit.system.pv_ratio_max} onChange={(v) => setSystem({ pv_ratio_max: v ?? 1.3 })} min={1} max={2} step={0.05} />
        </div>
        <div className="narrow" style={{ width: 110 }}>
          <label>Battery usable share (DoD)</label>
          <NumberInput value={audit.system.battery_dod} onChange={(v) => setSystem({ battery_dod: v ?? 0.85 })} min={0.1} max={1} step={0.05} />
        </div>
        <div className="narrow" style={{ width: 100 }}>
          <label>Battery efficiency</label>
          <NumberInput value={audit.system.battery_efficiency} onChange={(v) => setSystem({ battery_efficiency: v ?? 0.92 })} min={0.5} max={1} step={0.01} />
        </div>
      </div>
    </div>
  )
}
