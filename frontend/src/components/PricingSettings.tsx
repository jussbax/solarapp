import { useMemo, useState, type ReactNode } from 'react'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { PaymentPlan, PricingConfig } from '../types'
import { PaymentPlanEditor } from './ProgramSection'
import Field from './Field'
import NumberInput from './NumberInput'
import MapPicker from './MapPicker'
import { fmtDate } from '../fmt'
import { SETTINGS_ENTRIES, WEBSITE_SECTION, type SettingsEntry } from './shared'
import {
  DraftCtx, HEADED, HIDDEN, KEYED_SECTIONS, META, OTHER_GROUP, PCT_KEYS, SECTION_LABELS, SECTION_NOTES, SKIP, SUBBLOCKS, TASK_LABELS, TIME_KEYS, UNDO_SECONDS,
  decimalsFor, dirtyEntryIds, fieldId, findSettings, isCategoryList, isMatrix, isPrimDict, isPrimList, isTaskList, labelOf, numericKey, pctIn, settingsIndex, slug, sortedSizes, titleCase,
  useFindTarget, usePricingDraft, type CategoryRule, type Draft, type FindRow, type GroundTask,
} from './pricingMeta'

/* ---------- the shared draft: one in-memory copy of the pricing config for every pricing page ---------- */

/** Holds the pricing config while the person moves between the settings pages; Save writes the whole document. */
export function PricingDraftProvider({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const [cfg, setCfg] = useState<PricingConfig | null>(null)
  const [saved, setSaved] = useState<PricingConfig | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  // after Reset to defaults the settings as they were stay here for ten seconds, so a slip can be undone
  const [undo, setUndo] = useState<{ cfg: PricingConfig; saved: PricingConfig; left: number } | null>(null)

  useEffect(() => {
    if (!enabled) return
    api
      .pricingConfig()
      .then((c) => {
        setCfg(c)
        setSaved(c)
      })
      .catch((e) => setError(e.message))
  }, [enabled])

  useEffect(() => {
    if (!undo) return
    const t = window.setTimeout(() => setUndo((u) => (u && u.left > 1 ? { ...u, left: u.left - 1 } : null)), 1000)
    return () => window.clearTimeout(t)
  }, [undo])

  const dirtySections = useMemo(() => {
    if (!cfg || !saved) return []
    return Object.keys(cfg).filter((k) => !SKIP.has(k) && JSON.stringify(cfg[k]) !== JSON.stringify(saved[k]))
  }, [cfg, saved])
  const dirty = dirtySections.length > 0

  useEffect(() => {
    if (!dirty) return
    const onUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener('beforeunload', onUnload)
    return () => window.removeEventListener('beforeunload', onUnload)
  }, [dirty])

  const value: Draft = {
    cfg,
    saved,
    error,
    msg,
    busy,
    dirtySections,
    dirty,
    undo: undo ? { left: undo.left } : null,
    setField: (section, key, v) => setCfg((c) => (c ? { ...c, [section]: { ...c[section], [key]: v } } : c)),
    setSection: (section, v) => setCfg((c) => (c ? { ...c, [section]: v } : c)),
    save: async () => {
      if (!cfg) return false
      setError(null)
      setBusy(true)
      try {
        const r = await api.savePricingConfig(cfg)
        setCfg(r)
        setSaved(r)
        setUndo(null)
        setMsg('Saved. Calculate a project again to apply them.')
        return true
      } catch (e) {
        setError((e as Error).message)
        return false
      } finally {
        setBusy(false)
      }
    },
    discard: () => {
      if (saved) setCfg(saved)
    },
    reset: async () => {
      if (!cfg) return
      if (!window.confirm('Reset every pricing setting to the built-in workbook defaults? Your edits in every section are lost. You can undo for ten seconds afterwards.')) return
      setError(null)
      setBusy(true)
      const before = { cfg, saved: saved ?? cfg }
      try {
        const r = await api.resetPricingConfig()
        setCfg(r)
        setSaved(r)
        setMsg('Reset to defaults.')
        setUndo({ ...before, left: UNDO_SECONDS })
      } catch (e) {
        setError((e as Error).message)
      } finally {
        setBusy(false)
      }
    },
    undoReset: async () => {
      if (!undo) return
      setError(null)
      setBusy(true)
      try {
        const r = await api.savePricingConfig(undo.saved)
        setSaved(r)
        setCfg(undo.cfg) // unsaved edits from before the reset come back as unsaved edits
        setUndo(null)
        setMsg('Reset undone: your settings are back.')
      } catch (e) {
        setError((e as Error).message)
      } finally {
        setBusy(false)
      }
    },
  }
  return <DraftCtx.Provider value={value}>{children}</DraftCtx.Provider>
}

/* ---------- the editors: a table for every list, never a JSON box ---------- */

/** The categories as a small table (name, markup %, wastage %). */
function CategoriesEditor({ rows, onChange }: { rows: CategoryRule[]; onChange: (rows: CategoryRule[]) => void }) {
  const set = (i: number, p: Partial<CategoryRule>) => onChange(rows.map((r, j) => (j === i ? { ...r, ...p } : r)))
  return (
    <div id={fieldId('categories', 'value')} className="setting-block">
      <table className="categories" data-testid="categories-editor">
        <thead>
          <tr>
            <th>Category</th>
            <th className="num">Markup %</th>
            <th className="num">Wastage %</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="cell-main" data-label="Category">
                <input value={r.name} aria-label={`Category ${i + 1} name`} onChange={(e) => set(i, { name: e.target.value })} />
              </td>
              <td className="num" data-label="Markup %">
                <NumberInput value={pctIn(r.markup_tier)} decimals={1} min={0} ariaLabel={`${r.name || 'Category'} markup %`} style={{ width: 110 }} onChange={(v) => set(i, { markup_tier: (v ?? 0) / 100 })} />
              </td>
              <td className="num" data-label="Wastage %">
                <NumberInput value={pctIn(r.wastage ?? 0)} decimals={1} min={0} ariaLabel={`${r.name || 'Category'} wastage %`} style={{ width: 110 }} onChange={(v) => set(i, { wastage: (v ?? 0) / 100 })} />
              </td>
              <td className="cell-actions">
                <button type="button" className="toggle link" onClick={() => onChange(rows.filter((_, j) => j !== i))}>
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 6 }}>
        <button type="button" className="small" onClick={() => onChange([...rows, { name: '', markup_tier: 0.3, wastage: 0 }])}>
          Add category
        </button>
      </div>
    </div>
  )
}

/** The ground tasks: one row per task, the weights as numbers, the key under the name for the developer's sake. */
function GroundTasksEditor({ rows, savedKeys, onChange }: { rows: GroundTask[]; savedKeys: Set<string>; onChange: (rows: GroundTask[]) => void }) {
  const set = (i: number, p: Partial<GroundTask>) => onChange(rows.map((r, j) => (j === i ? { ...r, ...p } : r)))
  return (
    <div className="block">
      <table className="tasks" data-testid="ground-tasks">
        <thead>
          <tr>
            <th>Task</th>
            <th className="num">Mounting weight</th>
            <th className="num">Wiring weight</th>
            <th>Per</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="cell-main" data-label="Task">
                <input value={r.label} aria-label={`Task ${i + 1} name`} onChange={(e) => set(i, { label: e.target.value, key: savedKeys.has(r.key) ? r.key : slug(e.target.value) })} />
                <span className="key">{r.key}</span>
              </td>
              <td className="num" data-label="Mounting weight">
                <NumberInput value={r.mounting_weight} decimals={2} min={0} ariaLabel={`${r.label} mounting weight`} style={{ width: 100 }} onChange={(v) => set(i, { mounting_weight: v ?? 0 })} />
              </td>
              <td className="num" data-label="Wiring weight">
                <NumberInput value={r.wiring_weight} decimals={2} min={0} ariaLabel={`${r.label} wiring weight`} style={{ width: 100 }} onChange={(v) => set(i, { wiring_weight: v ?? 0 })} />
              </td>
              <td data-label="Per">
                <input value={r.unit} aria-label={`${r.label} unit`} style={{ width: 130 }} onChange={(e) => set(i, { unit: e.target.value })} />
              </td>
              <td className="cell-actions">
                <button type="button" className="toggle link" onClick={() => onChange(rows.filter((_, j) => j !== i))}>
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 6 }}>
        <button type="button" className="small" onClick={() => onChange([...rows, { key: slug(`task ${rows.length + 1}`), label: '', mounting_weight: 0, wiring_weight: 0, unit: 'per job' }])}>
          Add task
        </button>
      </div>
    </div>
  )
}

/** A list of sizes or words as chips with an add field: Enter adds, × removes. */
function ChipsEditor({ values, unit, numeric, label, onChange }: { values: (string | number)[]; unit?: string; numeric: boolean; label: string; onChange: (v: (string | number)[]) => void }) {
  const [text, setText] = useState('')
  const add = () => {
    const t = text.trim()
    if (!t) return
    const v: string | number = numeric ? Number(t) : t
    if (numeric && !Number.isFinite(v as number)) return
    if (values.includes(v)) {
      setText('')
      return
    }
    const next = [...values, v]
    onChange(numeric ? (next as number[]).sort((a, b) => a - b) : next)
    setText('')
  }
  return (
    <div className="block chips" data-testid="chips">
      {values.map((v, i) => (
        <span key={`${v}-${i}`} className="chip-item">
          {String(v)}
          {unit && numeric ? ` ${unit}` : ''}
          <button type="button" aria-label={`Remove ${v}`} title="Remove" onClick={() => onChange(values.filter((_, j) => j !== i))}>
            ×
          </button>
        </span>
      ))}
      <span className="chip-add">
        <input
          value={text}
          type={numeric ? 'number' : 'text'}
          inputMode={numeric ? 'numeric' : undefined}
          aria-label={`Add ${numeric ? 'size' : 'word'} to ${label}`}
          placeholder={numeric ? 'Add size' : 'Add word'}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              add()
            }
          }}
        />
        <button type="button" className="small" onClick={add}>
          Add
        </button>
      </span>
    </div>
  )
}

/** A size → value table ("3.5 mm²" → 20 A, or → an item code), sorted by size, with Add size and Remove. */
function SizeTableEditor({ value, unit, code, label, onChange }: { value: Record<string, string | number>; unit?: string; code: boolean; label: string; onChange: (v: Record<string, string | number>) => void }) {
  const [size, setSize] = useState('')
  const keys = sortedSizes(Object.keys(value))
  const sizes = keys.every(numericKey)
  const numeric = Object.values(value).every((x) => typeof x === 'number')
  const add = () => {
    const k = size.trim().replace(/\s*mm².*$/, '')
    if (!k || k in value) return
    onChange({ ...value, [k]: numeric ? 0 : '' })
    setSize('')
  }
  return (
    <div className="block">
      <table className="kv sizes">
        <thead>
          <tr>
            <th>{sizes ? 'Size' : 'Task'}</th>
            <th>{unit ?? (numeric ? 'Value' : 'Code')}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {keys.map((k) => {
            const x = value[k]
            const name = sizes ? `${k} mm²` : (TASK_LABELS[k] ?? titleCase(k))
            return (
              <tr key={k}>
                <th scope="row">{name}</th>
                <td>
                  {typeof x === 'number' ? (
                    <NumberInput value={x} decimals={0} min={0} ariaLabel={`${label} ${name}`} onChange={(v) => onChange({ ...value, [k]: v ?? 0 })} />
                  ) : (
                    <input value={x} aria-label={`${label} ${name}`} className={code ? 'code' : undefined} onChange={(e) => onChange({ ...value, [k]: e.target.value })} />
                  )}
                </td>
                <td className="cell-actions">
                  <button
                    type="button"
                    className="toggle link"
                    onClick={() => {
                      const next = { ...value }
                      delete next[k]
                      onChange(next)
                    }}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {sizes && (
        <span className="chip-add" style={{ marginTop: 6 }}>
          <input
            value={size}
            inputMode="decimal"
            aria-label={`Add size to ${label}`}
            placeholder="Add size, mm²"
            onChange={(e) => setSize(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                add()
              }
            }}
          />
          <button type="button" className="small" onClick={add}>
            Add
          </button>
        </span>
      )}
    </div>
  )
}

/** The minimum task durations and the late finish allowance as one "Minutes" table. */
function MinutesTable({ tasks, late, onTasks, onLate }: { tasks: Record<string, number>; late: number | undefined; onTasks: (v: Record<string, number>) => void; onLate: (v: number) => void }) {
  return (
    <div className="block">
      <table className="kv minutes">
        <thead>
          <tr>
            <th>Task</th>
            <th>Minutes</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(tasks).map(([k, x]) => (
            <tr key={k}>
              <th scope="row">{TASK_LABELS[k] ?? titleCase(k)}</th>
              <td>
                <NumberInput value={x} decimals={0} min={0} ariaLabel={`${TASK_LABELS[k] ?? titleCase(k)} minutes`} onChange={(v) => onTasks({ ...tasks, [k]: v ?? 0 })} />
              </td>
            </tr>
          ))}
          {late != null && (
            <tr>
              <th scope="row">Late finish allowance</th>
              <td>
                <NumberInput value={late} decimals={0} min={0} ariaLabel="Late finish allowance minutes" onChange={(v) => onLate(v ?? 0)} />
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

/** The route's stops as a one-column table with arrows; the km and toll tables follow every change. */
function StopsEditor({ stops, km, toll, onChange }: { stops: string[]; km: number[][]; toll: number[][]; onChange: (stops: string[], km: number[][], toll: number[][]) => void }) {
  const permute = (m: number[][], order: number[]) => order.map((i) => order.map((j) => m[i]?.[j] ?? 0))
  const move = (i: number, d: number) => {
    const j = i + d
    if (j < 0 || j >= stops.length) return
    const order = stops.map((_, k) => k)
    ;[order[i], order[j]] = [order[j], order[i]]
    onChange(order.map((k) => stops[k]), permute(km, order), permute(toll, order))
  }
  const remove = (i: number) => {
    const order = stops.map((_, k) => k).filter((k) => k !== i)
    onChange(order.map((k) => stops[k]), permute(km, order), permute(toll, order))
  }
  const add = () => {
    const at = Math.max(stops.length - 1, 0) // before the site, which stays last
    const grow = (m: number[][]) => {
      const rows = m.map((r) => [...r.slice(0, at), 0, ...r.slice(at)])
      rows.splice(at, 0, new Array(stops.length + 1).fill(0))
      return rows
    }
    onChange([...stops.slice(0, at), 'New stop', ...stops.slice(at)], grow(km), grow(toll))
  }
  return (
    <div className="block">
      <table className="kv stops" data-testid="stops-editor">
        <tbody>
          {stops.map((s, i) => (
            <tr key={i}>
              <th scope="row" className="num">
                {i + 1}
              </th>
              <td>
                <input value={s} aria-label={`Stop ${i + 1}`} onChange={(e) => onChange(stops.map((x, k) => (k === i ? e.target.value : x)), km, toll)} />
              </td>
              <td className="cell-actions">
                <button type="button" className="toggle" aria-label={`Move ${s} up`} title="Move up" disabled={i === 0} onClick={() => move(i, -1)}>
                  ▲
                </button>
                <button type="button" className="toggle" aria-label={`Move ${s} down`} title="Move down" disabled={i === stops.length - 1} onClick={() => move(i, 1)}>
                  ▼
                </button>
                <button type="button" className="toggle link" onClick={() => remove(i)}>
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 6 }}>
        <button type="button" className="small" onClick={add}>
          Add stop
        </button>
      </div>
    </div>
  )
}

function MatrixEditor({ value, stops, label, unit, onChange }: { value: number[][]; stops: string[]; label: string; unit?: string; onChange: (v: number[][]) => void }) {
  return (
    <div className="block table-wrap scroll-x">
      <div className="scroll-note muted">Scroll sideways to see every stop.</div>
      <table className="matrix">
        <thead>
          <tr>
            <th className="unit-cell">{unit}</th>
            {stops.map((st, j) => (
              <th key={j} className="num">
                {st}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {value.map((row, i) => (
            <tr key={i}>
              <th>{stops[i] ?? `#${i + 1}`}</th>
              {row.map((x, j) => (
                <td key={j} className="num">
                  <NumberInput
                    value={x}
                    decimals={0}
                    min={0}
                    ariaLabel={`${label}: ${stops[i] ?? i + 1} to ${stops[j] ?? j + 1}`}
                    onChange={(v) => {
                      const next = value.map((r) => [...r])
                      next[i][j] = v ?? 0
                      onChange(next)
                    }}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** A switch row above a grid: "Estimate page  On". */
function SwitchRow({ id, label, value, onChange }: { id: string; label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="switch-row" htmlFor={id}>
      <input id={id} type="checkbox" role="switch" checked={value} aria-checked={value} onChange={(e) => onChange(e.target.checked)} />
      <span className="switch-label">{label}</span>
      <span className={`switch-state ${value ? 'on' : ''}`}>{value ? 'On' : 'Off'}</span>
    </label>
  )
}

/* ---------- one section of the config as form cells and blocks ---------- */

/** One setting as a form cell: a Field for a single control, a block on its own line for a table or an editor. */
function SettingCell({ section, k, v }: { section: string; k: string; v: unknown }) {
  const { cfg, saved, setField } = usePricingDraft()
  const path = `${section}.${k}`
  const meta = META[path]
  const id = fieldId(section, k)
  const keyName = KEYED_SECTIONS.has(section) ? k : undefined
  const label = labelOf(section, k)
  const headed = HEADED.has(path) ? ' headed' : ''
  const common = { id, label, help: meta?.help, about: meta?.about, keyName }
  if (typeof v === 'number') {
    const pct = PCT_KEYS.has(k)
    const decimals = decimalsFor(meta, pct)
    return (
      <Field {...common} unit={meta?.unit ?? (pct ? '%' : undefined)}>
        {(fid) => (
          <NumberInput
            id={fid}
            value={pct ? pctIn(v) : v}
            decimals={decimals}
            disabled={meta?.readOnly}
            onChange={(n) => setField(section, k, pct ? (n ?? 0) / 100 : (n ?? 0))}
          />
        )}
      </Field>
    )
  }
  if (typeof v === 'boolean') {
    return (
      <Field {...common}>
        {(fid) => (
          <span className="inline" style={{ minHeight: 'var(--control-h)' }}>
            <input id={fid} type="checkbox" checked={v} onChange={(e) => setField(section, k, e.target.checked)} />
            <span className="muted">{v ? 'On' : 'Off'}</span>
          </span>
        )}
      </Field>
    )
  }
  if (typeof v === 'string') {
    if (TIME_KEYS.has(k)) return <Field {...common}>{(fid) => <input id={fid} type="time" value={v} onChange={(e) => setField(section, k, e.target.value)} />}</Field>
    const long = meta?.wide || v.length > 24 || /words|names/.test(label)
    return (
      <Field {...common} className={long ? 'wide' : undefined}>
        {(fid) => <input id={fid} value={v} onChange={(e) => setField(section, k, e.target.value)} className={KEYED_SECTIONS.has(section) ? 'code' : undefined} />}
      </Field>
    )
  }
  if (section === 'program' && k === 'payment') {
    return (
      <Field {...common} className={`full${headed}`}>
        {(fid) => (
          <div className="block" id={fid}>
            <PaymentPlanEditor plan={v as PaymentPlan} defaults={v as PaymentPlan} onChange={(p) => p && setField(section, k, p)} hideDefaultLink heading={false} />
          </div>
        )}
      </Field>
    )
  }
  if (section === 'program' && k === 'min_task_minutes' && isPrimDict(v)) {
    const late = cfg?.program?.late_finish_max_minutes
    return (
      <Field {...common} className={`wide own-line${headed}`} unit={undefined}>
        {(fid) => (
          <div id={fid} className="block">
            <MinutesTable tasks={v as Record<string, number>} late={typeof late === 'number' ? late : undefined} onTasks={(t) => setField(section, k, t)} onLate={(n) => setField(section, 'late_finish_max_minutes', n)} />
          </div>
        )}
      </Field>
    )
  }
  if (section === 'ground' && k === 'tasks' && isTaskList(v)) {
    const savedKeys = new Set<string>(((saved?.ground?.tasks as GroundTask[] | undefined) ?? []).map((t) => t.key))
    return (
      <Field {...common} className="full">
        {(fid) => (
          <div id={fid} className="block">
            <GroundTasksEditor rows={v} savedKeys={savedKeys} onChange={(rows) => setField(section, k, rows)} />
          </div>
        )}
      </Field>
    )
  }
  if (section === 'route' && k === 'stops' && isPrimList(v)) {
    const km = isMatrix(cfg?.route?.km) ? (cfg!.route.km as number[][]) : []
    const toll = isMatrix(cfg?.route?.toll) ? (cfg!.route.toll as number[][]) : []
    return (
      <Field {...common} className="wide own-line">
        {(fid) => (
          <div id={fid} className="block">
            <StopsEditor
              stops={v as string[]}
              km={km}
              toll={toll}
              onChange={(stops, km2, toll2) => {
                setField(section, k, stops)
                setField(section, 'km', km2)
                setField(section, 'toll', toll2)
              }}
            />
          </div>
        )}
      </Field>
    )
  }
  if (isMatrix(v)) {
    const stops: string[] = Array.isArray(cfg?.[section]?.stops) ? (cfg![section].stops as string[]) : v.map((_, i) => `#${i + 1}`)
    return (
      <Field {...common} className="full">
        {(fid) => (
          <div id={fid} className="block">
            <MatrixEditor value={v} stops={stops} label={label} unit={meta?.unit} onChange={(m) => setField(section, k, m)} />
          </div>
        )}
      </Field>
    )
  }
  if (isPrimList(v)) {
    const numeric = v.every((x) => typeof x === 'number')
    return (
      <Field {...common} className="full">
        {(fid) => (
          <div id={fid}>
            <ChipsEditor values={v} unit={meta?.unit} numeric={numeric} label={label} onChange={(list) => setField(section, k, list)} />
          </div>
        )}
      </Field>
    )
  }
  if (isPrimDict(v)) {
    return (
      <Field {...common} className="wide own-line">
        {(fid) => (
          <div id={fid}>
            <SizeTableEditor value={v} unit={meta?.unit} code={KEYED_SECTIONS.has(section)} label={label} onChange={(d) => setField(section, k, d)} />
          </div>
        )}
      </Field>
    )
  }
  // a shape the editor does not know: say so instead of printing a JSON box
  return (
    <Field {...common} className="full">
      {(fid) => (
        <div id={fid} className="muted" style={{ minHeight: 'var(--control-h)', display: 'flex', alignItems: 'center' }}>
          Set by the developer.
        </div>
      )}
    </Field>
  )
}

const isCell = (v: unknown) => typeof v === 'number' || typeof v === 'boolean' || typeof v === 'string'

/** A set of keys of one section: the single controls first, then the tables each on a line of its own. */
function KeysGrid({ section, keys }: { section: string; keys: string[] }) {
  const { cfg } = usePricingDraft()
  const v = cfg?.[section] as Record<string, unknown> | undefined
  if (!v) return null
  const shown = keys.filter((k) => k in v && !HIDDEN.has(`${section}.${k}`))
  const cells = shown.filter((k) => isCell(v[k]))
  const blocks = shown.filter((k) => !isCell(v[k]))
  if (shown.length === 0) return null
  return (
    <div className="form-grid">
      {cells.map((k) => (
        <SettingCell key={k} section={section} k={k} v={v[k]} />
      ))}
      {blocks.map((k) => (
        <SettingCell key={k} section={section} k={k} v={v[k]} />
      ))}
    </div>
  )
}

/** The company base: its name and its pin on the map (the route's coordinates). */
function CompanyBaseBlock() {
  const { cfg, setSection, setField } = usePricingDraft()
  const name = typeof cfg?.company_base === 'string' ? (cfg.company_base as string) : ''
  const lat = typeof cfg?.route?.base_lat === 'number' ? (cfg.route.base_lat as number) : null
  const lon = typeof cfg?.route?.base_lon === 'number' ? (cfg.route.base_lon as number) : null
  const meta = META['company_base.value']
  return (
    <div className="form-grid">
      <Field id={fieldId('company_base', 'value')} label={meta.label} help={meta.help} className="wide">
        {(fid) => <input id={fid} value={name} onChange={(e) => setSection('company_base', e.target.value)} />}
      </Field>
      <Field id={fieldId('route', 'base_lat')} label="Base on the map" help="The route's km start here" className="full">
        {(fid) => (
          <div id={fid} className="block">
            <MapPicker
              lat={lat}
              lon={lon}
              onChange={(a, o) => {
                setField('route', 'base_lat', a)
                setField('route', 'base_lon', o)
              }}
            />
          </div>
        )}
      </Field>
    </div>
  )
}

/** A whole section: its blocks and grids, or its own editor when the section is not a plain object. */
export function SectionBody({ sec }: { sec: string }) {
  const { cfg, setSection, setField } = usePricingDraft()
  if (!cfg) return null
  const v = cfg[sec]
  if (sec === 'company_base') return <CompanyBaseBlock />
  if (isCategoryList(v)) return <CategoriesEditor rows={v} onChange={(rows) => setSection(sec, rows)} />
  if (typeof v === 'string') {
    const meta = META[`${sec}.value`]
    return (
      <div className="form-grid">
        <Field label={meta?.label ?? SECTION_LABELS[sec] ?? titleCase(sec)} help={meta?.help} className="wide" id={fieldId(sec, 'value')}>
          {(fid) => <input id={fid} value={v} onChange={(e) => setSection(sec, e.target.value)} />}
        </Field>
      </div>
    )
  }
  if (!v || typeof v !== 'object' || Array.isArray(v)) {
    return <div className="muted">Set by the developer.</div>
  }
  const obj = v as Record<string, unknown>
  const keys = Object.keys(obj)
  const blocks = SUBBLOCKS[sec]
  if (blocks) {
    const named = new Set(blocks.flatMap((b) => b.keys))
    const rest = keys.filter((k) => !named.has(k) && !HIDDEN.has(`${sec}.${k}`))
    return (
      <>
        {blocks.map((b) => (
          <div key={b.title} className="setting-block" id={`${sec}-${slug(b.title)}`}>
            {!b.headed && <h3>{b.title}</h3>}
            <KeysGrid section={sec} keys={b.keys} />
          </div>
        ))}
        {rest.length > 0 && <KeysGrid section={sec} keys={rest} />}
      </>
    )
  }
  // the website estimate: the switch above the grid, the assumptions under it
  if (sec === WEBSITE_SECTION && typeof obj.enabled === 'boolean') {
    return (
      <>
        <SwitchRow id={fieldId(sec, 'enabled')} label={META['quick.enabled'].label} value={obj.enabled} onChange={(on) => setField(sec, 'enabled', on)} />
        <KeysGrid section={sec} keys={keys.filter((k) => k !== 'enabled')} />
      </>
    )
  }
  return <KeysGrid section={sec} keys={keys} />
}

/** The number of settings in a section, for the fold's summary. */
function countOf(cfg: PricingConfig, sec: string): number {
  const v = cfg[sec]
  if (v && typeof v === 'object' && !Array.isArray(v)) return Object.keys(v as object).filter((k) => !HIDDEN.has(`${sec}.${k}`)).length
  return 1
}

/** The sections of one pricing page, each an open block with its heading (the longest one folded), and the save bar. */
export function PricingPage({ entry }: { entry: SettingsEntry }) {
  const { cfg, error } = usePricingDraft()
  const rows = useMemo(() => settingsIndex(cfg).filter((r) => r.route === entry.route), [cfg, entry.route])
  useFindTarget(!!cfg, rows)
  if (!cfg) return <div className="muted">{error ?? 'Loading pricing settings...'}</div>
  const named = new Set(SETTINGS_ENTRIES.flatMap((e) => e.sections ?? []).concat([WEBSITE_SECTION]))
  const others = entry.id === 'system' ? Object.keys(cfg).filter((k) => !SKIP.has(k) && !named.has(k)) : []
  const sections = (entry.sections ?? []).filter((s) => s in cfg)
  const single = sections.length === 1 && others.length === 0 && !SUBBLOCKS[sections[0]]
  const block = (sec: string) => (
    <div key={sec} className="setting-block" id={`section-${sec}`} data-testid={`setting-${sec}`}>
      {!single && !SUBBLOCKS[sec] && <h3>{SECTION_LABELS[sec] ?? titleCase(sec)}</h3>}
      {SECTION_NOTES[sec] && <div className="lead">{SECTION_NOTES[sec]}</div>}
      <SectionBody sec={sec} />
    </div>
  )
  return (
    <>
      {sections.map((sec) =>
        sec === 'roles' ? (
          <details key={sec} className="setting-fold" id={`section-${sec}`} data-testid={`setting-${sec}`}>
            <summary>
              <span className="summary-title">{SECTION_LABELS[sec]}</span>
              <span className="chip">{countOf(cfg, sec)} settings</span>
            </summary>
            <div className="setting-body">
              {SECTION_NOTES[sec] && <div className="lead">{SECTION_NOTES[sec]}</div>}
              <SectionBody sec={sec} />
            </div>
          </details>
        ) : (
          block(sec)
        ),
      )}
      {others.length > 0 && (
        <div className="setting-block" id={OTHER_GROUP.id}>
          <h3>{OTHER_GROUP.label}</h3>
          <div className="lead">{OTHER_GROUP.lead}</div>
          {others.map((sec) => (
            <div key={sec} className="setting-block" id={`section-${sec}`} data-testid={`setting-${sec}`}>
              <h3>{SECTION_LABELS[sec] ?? titleCase(sec)}</h3>
              <SectionBody sec={sec} />
            </div>
          ))}
        </div>
      )}
      {entry.id === 'materials' && <ResetFoot />}
      <PricingBar />
    </>
  )
}

/** The sticky bar at the foot of a pricing page: the edited pages across the draft, Save, Discard. */
export function PricingBar() {
  const { dirty, dirtySections, busy, msg, error, save, discard } = usePricingDraft()
  const pages = [...dirtyEntryIds(dirtySections)].map((id) => SETTINGS_ENTRIES.find((e) => e.id === id)?.label ?? id)
  const n = dirtySections.length
  return (
    <div className="actions card-bar" data-testid="pricing-bar">
      <span className={`chip ${dirty ? 'unsaved' : 'ok'}`}>{dirty ? `${n} ${n === 1 ? 'section' : 'sections'} edited · ${pages.join(', ')}` : 'Saved'}</span>
      <button type="button" className="primary" onClick={save} disabled={!dirty || busy}>
        Save
      </button>
      <span className={`second-row ${!dirty ? 'hidden-phone' : ''}`}>
        <button type="button" onClick={discard} disabled={!dirty}>
          Discard changes
        </button>
      </span>
      {msg && !dirty && <span className="muted bar-note">{msg}</span>}
      {error && (
        <div className="banner bad" style={{ flexBasis: '100%', margin: 0 }}>
          {error}
        </div>
      )}
    </div>
  )
}

/** The foot of the Materials page: where the settings came from, and the way back to the workbook defaults. */
function ResetFoot() {
  const { cfg, busy, undo, reset, undoReset } = usePricingDraft()
  if (!cfg) return null
  return (
    <div className="muted reset-foot" data-testid="reset-foot">
      Imported from {cfg.imported_from ?? 'the built-in defaults'}
      {cfg.imported_at ? ` on ${fmtDate(cfg.imported_at)}` : ''}.{' '}
      {undo ? (
        <button type="button" className="toggle link" onClick={undoReset} disabled={busy} data-testid="undo-reset">
          Undo the reset ({undo.left} s)
        </button>
      ) : (
        <button type="button" className="toggle link" onClick={reset} disabled={busy} data-testid="reset-defaults">
          Reset every pricing setting to the workbook defaults
        </button>
      )}
    </div>
  )
}

/** The menu's search: a result list that opens the page and scrolls to the setting. */
export function FindSettings({ rows, needle, onNeedle, extraRows = [] }: { rows: FindRow[]; needle: string; onNeedle: (s: string) => void; extraRows?: FindRow[] }) {
  const navigate = useNavigate()
  const all = useMemo(() => [...extraRows, ...rows], [extraRows, rows])
  const hits = findSettings(all, needle)
  const q = needle.trim()
  return (
    <div className="setting-find">
      <input
        id="setting-find"
        type="search"
        value={needle}
        placeholder="Find a setting: VAT, team lead, toll"
        aria-label="Find a setting"
        onChange={(e) => onNeedle(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') onNeedle('')
        }}
      />
      {q && (
        <ul className="find-results" data-testid="find-results">
          {hits.length === 0 && <li className="muted">No setting matches</li>}
          {hits.slice(0, 40).map((r) => (
            <li key={r.id}>
              <button
                type="button"
                onClick={() => {
                  onNeedle('')
                  navigate(`${r.route}?find=${encodeURIComponent(r.find)}`)
                }}
              >
                <b>{r.label}</b>
                <span className="muted">{r.where}</span>
              </button>
            </li>
          ))}
          {hits.length > 40 && <li className="muted">{hits.length - 40} more; type another word</li>}
        </ul>
      )}
    </div>
  )
}
