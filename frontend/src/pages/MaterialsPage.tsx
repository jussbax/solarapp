import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import NumberInput from '../components/NumberInput'
import type { ImportReport, MaterialItem, MaterialSupplier, PricingStatus } from '../types'
import { fmtDateTime, php2 } from '../fmt'

const php = php2
type ItemDraft = Omit<MaterialItem, 'updated_at'>

function blankItem(): ItemDraft {
  return {
    code: '', category: 'Accessories', supplier: '', name: '', spec: '', unit: 'pc', sold_as: 'pc', list_price: 0, rating: null, rating_unit: '',
    weight_kg: 0, volume_m3: 0, weight_source: 'manual', storage: 0, price_list_date: '', remarks: '', panel_length_m: null, panel_width_m: null, active: true,
  }
}

function Field({ label, width = 160, children }: { label: string; width?: number; children: React.ReactNode }) {
  return (
    <div className="narrow" style={{ width }}>
      <label>{label}</label>
      {children}
    </div>
  )
}

function ItemForm({ it, set, codeEditable }: { it: ItemDraft; set: (p: Partial<ItemDraft>) => void; codeEditable: boolean }) {
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
        <Field label="List price (₱)" width={130}>
          <NumberInput value={it.list_price} onChange={(v) => set({ list_price: v ?? 0 })} min={0} />
        </Field>
        <Field label="Rating" width={100}>
          <NumberInput value={it.rating} onChange={(v) => set({ rating: v })} allowEmpty />
        </Field>
        <Field label="Rating unit" width={100}>
          <input value={it.rating_unit} onChange={(e) => set({ rating_unit: e.target.value })} placeholder="W, kW, kWh, A" />
        </Field>
      </div>
      <div className="row" style={{ marginTop: 6 }}>
        <Field label="Weight (kg)" width={110}>
          <NumberInput value={it.weight_kg} onChange={(v) => set({ weight_kg: v ?? 0 })} min={0} />
        </Field>
        <Field label="Volume (m³)" width={110}>
          <NumberInput value={it.volume_m3} onChange={(v) => set({ volume_m3: v ?? 0 })} min={0} step={0.0001} />
        </Field>
        <Field label="Storage (₱)" width={100}>
          <NumberInput value={it.storage} onChange={(v) => set({ storage: v ?? 0 })} min={0} />
        </Field>
        <Field label="Panel length (m)" width={130}>
          <NumberInput value={it.panel_length_m} onChange={(v) => set({ panel_length_m: v })} allowEmpty step={0.001} />
        </Field>
        <Field label="Panel width (m)" width={130}>
          <NumberInput value={it.panel_width_m} onChange={(v) => set({ panel_width_m: v })} allowEmpty step={0.001} />
        </Field>
        <Field label="Price list date" width={130}>
          <input value={it.price_list_date} onChange={(e) => set({ price_list_date: e.target.value })} />
        </Field>
        <Field label="Remarks" width={240}>
          <input value={it.remarks} onChange={(e) => set({ remarks: e.target.value })} />
        </Field>
      </div>
    </div>
  )
}

export default function MaterialsPage() {
  const [status, setStatus] = useState<PricingStatus | null>(null)
  const [cats, setCats] = useState<{ name: string; count: number }[]>([])
  const [suppliers, setSuppliers] = useState<MaterialSupplier[]>([])
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [supplier, setSupplier] = useState('')
  const [inactive, setInactive] = useState(false)
  const [items, setItems] = useState<MaterialItem[]>([])
  const [editing, setEditing] = useState<MaterialItem | null>(null)
  const [creating, setCreating] = useState<ItemDraft | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [keepConfig, setKeepConfig] = useState(true)
  const [report, setReport] = useState<ImportReport | null>(null)
  const [sort, setSort] = useState<{ key: 'code' | 'category' | 'name' | 'supplier' | 'list_price'; dir: 1 | -1 }>({ key: 'code', dir: 1 })
  const [limit, setLimit] = useState(50)
  const fileRef = useRef<HTMLInputElement>(null)

  const refreshMeta = useCallback(() => {
    api.pricingStatus().then(setStatus).catch(() => setStatus(null))
    api.materialCategories().then(setCats).catch(() => setCats([]))
    api.materialSuppliers().then(setSuppliers).catch(() => setSuppliers([]))
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
          edits here are used for pricing. Re-importing a workbook updates items by code and keeps panel dimensions typed here.
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <div style={{ flex: '2 1 260px' }}>
            <label>Search</label>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="code, name or spec" />
          </div>
          <div className="narrow" style={{ width: 200 }}>
            <label>Category</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All</option>
              {cats.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name} ({c.count})
                </option>
              ))}
            </select>
          </div>
          <div className="narrow" style={{ width: 180 }}>
            <label>Supplier</label>
            <select value={supplier} onChange={(e) => setSupplier(e.target.value)}>
              <option value="">All</option>
              {suppliers.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div className="narrow inline" style={{ paddingBottom: 8 }}>
            <input type="checkbox" checked={inactive} onChange={(e) => setInactive(e.target.checked)} style={{ width: 'auto' }} /> Show inactive
          </div>
          <div className="narrow inline" style={{ paddingBottom: 4 }}>
            <button type="button" className="primary" onClick={() => setCreating(blankItem())}>
              New item
            </button>
          </div>
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
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={10} className="muted">No items match. Try part of the code or name.</td>
                </tr>
              )}
              {shown.map((it) =>
                editing && editing.code === it.code ? (
                  <tr key={it.code}>
                    <td colSpan={10}>
                      <ItemForm it={editing} set={(p) => setEditing({ ...editing, ...p })} codeEditable={false} />
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
                          : <span className="badge bad">no size</span>
                        : ''}
                    </td>
                    <td style={{ whiteSpace: 'nowrap' }} className="cell-actions">
                      <button type="button" className="toggle link" onClick={() => setEditing(it)}>
                        Edit
                      </button>
                      <button type="button" className="toggle link" onClick={() => toggleActive(it)}>
                        {it.active ? 'Deactivate' : 'Activate'}
                      </button>
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
      </div>
    </>
  )
}
