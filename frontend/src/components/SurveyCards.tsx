import { useRef, useState } from 'react'
import Field from './Field'
import NumberInput from './NumberInput'
import { fmtDateShort } from '../fmt'
import type { ConditionFlag, GeoPoint, Interconnection, PanelboardCircuit, PurlinMaterial, RoofConstruction, RoofType, ServiceEntrance, SitePlan, VicinityMap } from '../types'

/** The survey record the plan set reads (round 13, docs/audits/round-13/engineer-brief.md, 1.3, 3.2, 4.2): the service entrance,
 * the roof construction and the site plan's points and outlines. Every field is optional and blank until surveyed; a blank
 * prints as a blank line with its reason on the sheets that read it, never a guess. Plain typed fields: the map's draw tools
 * for the outlines and the points are a later step. */

const ROOF_TYPES: { id: RoofType; label: string }[] = [
  { id: 'rib_metal', label: 'Rib-type (trapezoidal) metal sheet' },
  { id: 'corrugated_metal', label: 'Corrugated metal sheet' },
  { id: 'tile_clay', label: 'Clay tile' },
  { id: 'tile_concrete', label: 'Concrete tile' },
  { id: 'concrete_deck', label: 'Concrete deck (flat)' },
  { id: 'other', label: 'Other' },
]
const PURLINS: { id: PurlinMaterial; label: string }[] = [
  { id: 'steel_c', label: 'Steel C-purlin' },
  { id: 'steel_tubular', label: 'Steel tubular' },
  { id: 'wood', label: 'Wood' },
  { id: 'none', label: 'None' },
]
const FLAGS: { id: ConditionFlag; label: string }[] = [
  { id: 'sound', label: 'Sound' },
  { id: 'rusted', label: 'Rusted' },
  { id: 'thin', label: 'Thin' },
  { id: 'old', label: 'Old' },
]
const POI: { id: Interconnection; label: string }[] = [
  { id: 'load_side_breaker', label: 'Backfeed breaker in the existing panelboard (load side)' },
  { id: 'supply_side_tap', label: 'Supply-side tap' },
  { id: 'line_side_of_main', label: 'Line side of the main' },
]

/** The roof construction fields (3.2) for the project's default or for one face; on a face a blank reads "same as the project". */
export function RoofConstructionFields({ value, onChange, perFace, idPrefix }: { value: RoofConstruction; onChange: (v: RoofConstruction) => void; perFace?: boolean; idPrefix: string }) {
  const blank = perFace ? 'same as the project' : 'not surveyed'
  const set = (key: keyof RoofConstruction, v: string | number | null) => onChange({ ...value, [key]: v } as RoofConstruction)
  const sel = (label: string, key: 'roof_type' | 'purlin_material' | 'condition_flag', opts: { id: string; label: string }[], help?: string) => (
    <Field label={label} id={`${idPrefix}-${key}`} help={help}>
      {(id) => (
        <select id={id} value={value[key]} onChange={(e) => set(key, e.target.value)}>
          <option value="">{blank}</option>
          {opts.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  )
  const num = (label: string, key: 'purlin_thickness_mm' | 'purlin_spacing_m' | 'rafter_spacing_m' | 'mean_roof_height_m' | 'fastener_pullout_kn', unit: string, help?: string, blankWord?: string) => (
    <Field label={label} unit={unit} help={help} id={`${idPrefix}-${key}`}>
      {(id) => <NumberInput id={id} value={value[key] ?? null} onChange={(v) => set(key, v)} allowEmpty min={0} step={0.01} placeholder={perFace ? 'project' : (blankWord ?? 'not surveyed')} />}
    </Field>
  )
  const text = (label: string, key: 'sheet_profile' | 'purlin_section' | 'condition' | 'fastener_pullout_source', placeholder: string, className?: string) => (
    <Field label={label} id={`${idPrefix}-${key}`} className={className}>
      {(id) => <input id={id} value={value[key] ?? ''} onChange={(e) => set(key, e.target.value)} placeholder={perFace ? blank : placeholder} />}
    </Field>
  )
  return (
    <div className="form-grid face-grid" data-testid={`${idPrefix}-construction`}>
      {sel('Roof type', 'roof_type', ROOF_TYPES, 'Decides which mounting detail is drawn')}
      {text('Sheet profile', 'sheet_profile', 'e.g. rib 30 mm, pitch 250 mm')}
      {sel('Purlin material', 'purlin_material', PURLINS)}
      {text('Purlin section', 'purlin_section', 'e.g. C 100 × 50 × 1.5')}
      {num('Purlin thickness', 'purlin_thickness_mm', 'mm')}
      {num('Purlin spacing', 'purlin_spacing_m', 'm', 'The feet sit on purlins')}
      {num('Rafter spacing', 'rafter_spacing_m', 'm', 'Tile roofs')}
      {num('Mean roof height', 'mean_roof_height_m', 'm', 'Ground to mid-slope')}
      {sel('Condition', 'condition_flag', FLAGS, 'Other than sound: the sheet says to verify')}
      {text('Condition note', 'condition', 'e.g. rust at the eave, two sheets replaced', 'wide')}
      {/* round 13, item 3 (3.4): the fastener's allowable withdrawal for this roof, over the settings' figure, with its source */}
      {num('Fastener withdrawal, allowable', 'fastener_pullout_kn', 'kN', "Blank = the settings' figure", 'settings')}
      {text('Withdrawal figure: source', 'fastener_pullout_source', "e.g. the screw maker's sheet, 1.5 mm steel purlin")}
    </div>
  )
}

/** A [latitude, longitude] as two numbers: saved when both are typed, cleared when both are blank; one alone is kept on the screen only. */
function PointInput({ label, value, onChange, idPrefix }: { label: string; value: GeoPoint | null; onChange: (p: GeoPoint | null) => void; idPrefix: string }) {
  const [draft, setDraft] = useState<[number | null, number | null]>(value ?? [null, null])
  const put = (k: 0 | 1, v: number | null) => {
    const next: [number | null, number | null] = k === 0 ? [v, draft[1]] : [draft[0], v]
    setDraft(next)
    if (next[0] != null && next[1] != null) onChange([next[0], next[1]])
    else if (next[0] == null && next[1] == null && value) onChange(null)
  }
  const partial = (draft[0] == null) !== (draft[1] == null)
  return (
    <>
      <Field label={`${label}: latitude`} id={`${idPrefix}-lat`}>
        {(id) => <NumberInput id={id} value={draft[0]} onChange={(v) => put(0, v)} allowEmpty min={-90} max={90} step="any" placeholder="e.g. 14.23350" />}
      </Field>
      <Field label={`${label}: longitude`} id={`${idPrefix}-lon`} help={partial ? 'Both figures are needed' : undefined}>
        {(id) => <NumberInput id={id} value={draft[1]} onChange={(v) => put(1, v)} allowEmpty min={-180} max={180} step="any" placeholder="e.g. 121.36450" />}
      </Field>
    </>
  )
}

/** An outline as typed corners, one "latitude, longitude" per line; saved when every line reads and there are three corners or more (or none). */
function PolygonInput({ label, value, onChange, id, help }: { label: string; value: GeoPoint[]; onChange: (pts: GeoPoint[]) => void; id: string; help: string }) {
  const [text, setText] = useState(value.map((p) => `${p[0]}, ${p[1]}`).join('\n'))
  const [err, setErr] = useState<string | null>(null)
  const apply = () => {
    const pts: GeoPoint[] = []
    for (const line of text.split('\n').map((l) => l.trim()).filter(Boolean)) {
      const parts = line.split(/[,\s]+/).filter(Boolean)
      const la = parseFloat(parts[0])
      const lo = parseFloat(parts[1])
      if (parts.length < 2 || !Number.isFinite(la) || !Number.isFinite(lo) || Math.abs(la) > 90 || Math.abs(lo) > 180) {
        setErr(`"${line}" is not "latitude, longitude".`)
        return
      }
      pts.push([la, lo])
    }
    if (pts.length > 0 && pts.length < 3) {
      setErr('An outline needs at least three corners.')
      return
    }
    setErr(null)
    if (JSON.stringify(pts) !== JSON.stringify(value)) onChange(pts)
  }
  return (
    <Field label={label} id={id} help={err ?? help} className="wide">
      {(fid) => <textarea id={fid} rows={4} value={text} onChange={(e) => setText(e.target.value)} onBlur={apply} placeholder={'14.23350, 121.36450\n14.23360, 121.36470\n…'} aria-invalid={err ? true : undefined} />}
    </Field>
  )
}

function emptyCircuit(): PanelboardCircuit {
  return { no: '', description: '', breaker_a: null, poles: null, wire_mm2: null, conduit_mm: null }
}

/** The service entrance as surveyed (1.3), with the DU's fault level (2.3) and the panelboard's existing circuits (5.3). */
export function ServiceEntranceCard({ value, onChange }: { value: ServiceEntrance; onChange: (v: ServiceEntrance) => void }) {
  const set = (p: Partial<ServiceEntrance>) => onChange({ ...value, ...p })
  const setCircuit = (k: number, p: Partial<PanelboardCircuit>) => set({ circuits: value.circuits.map((c, i) => (i === k ? { ...c, ...p } : c)) })
  return (
    <div className="card" id="card-service" data-testid="card-service">
      <h2>Service entrance</h2>
      <div className="muted" style={{ marginBottom: 8 }}>
        As surveyed at the meter and the existing panelboard. Every field is optional: a blank prints as a blank line on the plans with "not surveyed", never a guess. The single-line diagram and the 120 % busbar rule that read these are later steps.
      </div>
      <div className="form-grid">
        <Field label="Electric company (DU)" id="service-du_name">
          {(id) => <input id={id} value={value.du_name} onChange={(e) => set({ du_name: e.target.value })} placeholder="e.g. Meralco, BATELEC II, FLECO" />}
        </Field>
        <Field label="Account number" id="service-account_no" help="Customer data: on the plans and the DU pack only">
          {(id) => <input id={id} value={value.account_no} onChange={(e) => set({ account_no: e.target.value })} />}
        </Field>
        <Field label="Meter number" id="service-meter_no">
          {(id) => <input id={id} value={value.meter_no} onChange={(e) => set({ meter_no: e.target.value })} />}
        </Field>
        <Field label="Phase" id="service-phase">
          {(id) => (
            <select id={id} value={value.phase == null ? '' : String(value.phase)} onChange={(e) => set({ phase: e.target.value === '' ? null : (Number(e.target.value) as 1 | 3) })}>
              <option value="">not surveyed</option>
              <option value="1">Single-phase (1Ø)</option>
              <option value="3">Three-phase (3Ø)</option>
            </select>
          )}
        </Field>
        <Field label="Service voltage" unit="V" id="service-voltage_v" help="Blank: the wiring rules' 230 V prints as an assumption">
          {(id) => <NumberInput id={id} value={value.voltage_v} onChange={(voltage_v) => set({ voltage_v })} allowEmpty min={0} step={1} placeholder="not surveyed" />}
        </Field>
        <Field label="Main breaker" unit="A" id="service-main_breaker_a">
          {(id) => <NumberInput id={id} value={value.main_breaker_a} onChange={(main_breaker_a) => set({ main_breaker_a })} allowEmpty min={0} step={1} placeholder="not surveyed" />}
        </Field>
        <Field label="Busbar rating" unit="A" id="service-busbar_a" help="Blank: the 120 % rule is not checked">
          {(id) => <NumberInput id={id} value={value.busbar_a} onChange={(busbar_a) => set({ busbar_a })} allowEmpty min={0} step={1} placeholder="not surveyed" />}
        </Field>
        <Field label="Available fault current" unit="kA" id="service-fault_level_ka" help="At the service, from the DU; verify">
          {(id) => <NumberInput id={id} value={value.fault_level_ka} onChange={(fault_level_ka) => set({ fault_level_ka })} allowEmpty min={0} step={0.1} placeholder="from the DU" />}
        </Field>
        <Field label="Existing panelboard" id="service-panelboard" className="wide">
          {(id) => <input id={id} value={value.panelboard} onChange={(e) => set({ panelboard: e.target.value })} placeholder="e.g. main panel, ground floor, 12-way" />}
        </Field>
        <Field label="Point of interconnection" id="service-interconnection" className="wide">
          {(id) => (
            <select id={id} value={value.interconnection} onChange={(e) => set({ interconnection: e.target.value as Interconnection })}>
              <option value="">not chosen</option>
              {POI.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field label="Interconnection note" id="service-interconnection_note" className="full">
          {(id) => <input id={id} value={value.interconnection_note} onChange={(e) => set({ interconnection_note: e.target.value })} placeholder="where the breaker sits, the distance to the meter" />}
        </Field>
      </div>
      <details className="more" data-testid="service-circuits">
        <summary>Existing circuits of the panelboard ({value.circuits.length})</summary>
        <div className="muted" style={{ margin: '4px 0 6px' }}>
          Optional: the circuits as the panelboard's directory lists them. The schedule of loads (a later sheet) prints them verbatim above the audit's loads.
        </div>
        {value.circuits.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table className="circuits-table">
              <thead>
                <tr>
                  <th>No.</th>
                  <th>Description</th>
                  <th>Breaker A</th>
                  <th>Poles</th>
                  <th>Wire mm²</th>
                  <th>Conduit mm</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {value.circuits.map((c, k) => (
                  <tr key={k}>
                    <td>
                      <input value={c.no} onChange={(e) => setCircuit(k, { no: e.target.value })} aria-label={`Circuit ${k + 1} number`} style={{ width: 56 }} />
                    </td>
                    <td>
                      <input value={c.description} onChange={(e) => setCircuit(k, { description: e.target.value })} aria-label={`Circuit ${k + 1} description`} style={{ minWidth: 160 }} />
                    </td>
                    <td>
                      <NumberInput value={c.breaker_a} onChange={(breaker_a) => setCircuit(k, { breaker_a })} allowEmpty min={0} step={1} ariaLabel={`Circuit ${k + 1} breaker`} style={{ width: 72 }} />
                    </td>
                    <td>
                      <NumberInput value={c.poles} onChange={(v) => setCircuit(k, { poles: v == null ? null : Math.round(v) })} allowEmpty min={1} max={4} step={1} ariaLabel={`Circuit ${k + 1} poles`} style={{ width: 56 }} />
                    </td>
                    <td>
                      <NumberInput value={c.wire_mm2} onChange={(wire_mm2) => setCircuit(k, { wire_mm2 })} allowEmpty min={0} step={0.5} ariaLabel={`Circuit ${k + 1} wire`} style={{ width: 72 }} />
                    </td>
                    <td>
                      <NumberInput value={c.conduit_mm} onChange={(conduit_mm) => setCircuit(k, { conduit_mm })} allowEmpty min={0} step={1} ariaLabel={`Circuit ${k + 1} conduit`} style={{ width: 72 }} />
                    </td>
                    <td>
                      <button type="button" className="toggle link" onClick={() => set({ circuits: value.circuits.filter((_, i) => i !== k) })}>
                        remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <button type="button" className="small" onClick={() => set({ circuits: [...value.circuits, emptyCircuit()] })}>
          Add circuit
        </button>
      </details>
    </div>
  )
}

const POINTS: { key: 'inverter' | 'battery' | 'poi' | 'meter'; label: string; placeholder: string }[] = [
  { key: 'inverter', label: 'Inverter', placeholder: 'e.g. ground floor utility room, south wall' },
  { key: 'battery', label: 'Battery', placeholder: 'e.g. beside the inverter' },
  { key: 'poi', label: 'Point of interconnection', placeholder: 'e.g. backfeed breaker in the main panel' },
  { key: 'meter', label: 'Meter', placeholder: 'e.g. on the gate post' },
]

/** The vicinity map's controls on the Site plan card (round 13, item 4): the page owns the calls; the card shows the state and asks. */
export interface VicinityControls {
  state: VicinityMap | null
  /** The preview of whichever map prints (null when nothing is on record). */
  previewUrl: string | null
  busy: boolean
  /** Why the actions are off (an unsaved draft, unsaved edits, no pin), or null when they may run. */
  blocked: string | null
  onPrepare: (force: boolean) => void
  onUpload: (file: File, note: string) => void
  onRemoveUpload: () => void
}

/** The vicinity map: composed on the server from map tiles ("Prepare the map"), or the office's screen grab, which prints instead. */
function VicinityMapSection({ state, previewUrl, busy, blocked, onPrepare, onUpload, onRemoveUpload }: VicinityControls) {
  const [note, setNote] = useState(state?.upload?.note ?? '')
  const fileRef = useRef<HTMLInputElement | null>(null)
  const off = busy || !!blocked
  const status = state?.upload
    ? `Your screen grab of ${fmtDateShort(state.upload.uploaded_at)} prints on the sheet${state.osm ? ' (the fetched map is kept underneath)' : ''}.`
    : state?.osm
      ? `Composed from map tiles on ${fmtDateShort(state.osm.fetched_at)} (${state.osm.host}); prints on the sheet with "${state.osm.attribution}".`
      : state?.error
        ? `Not fetched: ${state.error.reason}. The sheet prints the pin and this note until a map is on record.`
        : 'Not prepared yet. The first plans download prepares it; or press the button now.'
  const version = state?.upload?.uploaded_at ?? state?.osm?.fetched_at ?? ''
  return (
    <div data-testid="vicinity-map">
      <h3>Vicinity map</h3>
      <div className="muted" style={{ marginBottom: 6 }}>
        Sheet 2 of the plans. Composed from OpenStreetMap tiles under their usage policy (eighteen tiles per project, fetched once and cached; the attribution prints on the sheet), or your own screen grab, which always prints instead when uploaded.
      </div>
      <div className="muted" data-testid="vicinity-status" data-source={state?.source ?? (state?.error ? 'error' : 'none')}>
        {status}
      </div>
      {previewUrl && (
        <div style={{ margin: '6px 0' }}>
          <img src={`${previewUrl}${previewUrl.includes('?') ? '&' : '?'}v=${encodeURIComponent(version)}`} alt="The vicinity map that prints on the plans" style={{ maxHeight: 220, maxWidth: '100%', border: '1px solid var(--line)' }} />
        </div>
      )}
      <div className="row" style={{ alignItems: 'end', gap: 8, flexWrap: 'wrap' }}>
        <button type="button" className="small" disabled={off} title={blocked ?? undefined} onClick={() => onPrepare(!!state?.osm)} data-testid="vicinity-prepare">
          {state?.osm ? 'Refresh map' : 'Prepare the map'}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg"
          style={{ display: 'none' }}
          data-testid="vicinity-file"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) onUpload(f, note)
            e.target.value = ''
          }}
        />
        <button type="button" className="small" disabled={off} title={blocked ?? undefined} onClick={() => fileRef.current?.click()} data-testid="vicinity-upload">
          Upload a screen grab
        </button>
        {state?.upload && (
          <button type="button" className="toggle link danger" disabled={off} onClick={onRemoveUpload} data-testid="vicinity-remove">
            Remove the upload
          </button>
        )}
        <Field label="Attribution printed with the upload" id="vicinity-note" className="narrow" style={{ minWidth: 260, flex: 1 }} help="e.g. screen grab of the office map, © OpenStreetMap contributors">
          {(id) => <input id={id} value={note} onChange={(e) => setNote(e.target.value)} placeholder="screen grab of the office map, © OpenStreetMap contributors" maxLength={200} />}
        </Field>
      </div>
      {blocked && <div className="muted">{blocked}</div>}
    </div>
  )
}

/** The site plan's survey (4.2): where the equipment, the point of interconnection and the meter go, and the lot and house outlines. */
export function SitePlanCard({ value, onChange, vicinity }: { value: SitePlan; onChange: (v: SitePlan) => void; vicinity?: VicinityControls }) {
  const set = (p: Partial<SitePlan>) => onChange({ ...value, ...p })
  return (
    <div className="card" id="card-siteplan" data-testid="card-siteplan">
      <h2>Site plan</h2>
      <div className="muted" style={{ marginBottom: 8 }}>
        Typed coordinates for now, as the map pin shows them (latitude, longitude in degrees); drawing the outlines and dragging the points on the map is a later step. A blank prints "not surveyed" on the site plan sheet, never a guess.
      </div>
      {vicinity && <VicinityMapSection {...vicinity} />}
      <h3>Equipment, the point of interconnection and the meter</h3>
      <div className="form-grid cols-3">
        {POINTS.map((p) => (
          <PointRow key={p.key} label={p.label} placeholder={p.placeholder} location={value[`${p.key}_location`]} point={value[`${p.key}_point`]} onLocation={(v) => set({ [`${p.key}_location`]: v } as Partial<SitePlan>)} onPoint={(pt) => set({ [`${p.key}_point`]: pt } as Partial<SitePlan>)} idPrefix={`site-${p.key}`} />
        ))}
      </div>
      <h3>Lot and house outlines</h3>
      <div className="form-grid cols-2">
        <PolygonInput key={`lot-${JSON.stringify(value.lot_polygon)}`} label="Property line (lot corners)" id="site-lot" value={value.lot_polygon} onChange={(lot_polygon) => set({ lot_polygon })} help="One corner per line, in order around the lot; the setbacks print when the house outline is typed too" />
        <PolygonInput key={`house-${JSON.stringify(value.house_polygon)}`} label="House outline (corners)" id="site-house" value={value.house_polygon} onChange={(house_polygon) => set({ house_polygon })} help="One corner per line, in order around the house" />
      </div>
    </div>
  )
}

function PointRow({ label, placeholder, location, point, onLocation, onPoint, idPrefix }: { label: string; placeholder: string; location: string; point: GeoPoint | null; onLocation: (v: string) => void; onPoint: (p: GeoPoint | null) => void; idPrefix: string }) {
  return (
    <>
      <Field label={`${label}: where`} id={`${idPrefix}-location`}>
        {(id) => <input id={id} value={location} onChange={(e) => onLocation(e.target.value)} placeholder={placeholder} />}
      </Field>
      <PointInput key={JSON.stringify(point)} label={label} value={point} onChange={onPoint} idPrefix={idPrefix} />
    </>
  )
}
