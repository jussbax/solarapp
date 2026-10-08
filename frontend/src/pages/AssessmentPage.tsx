import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useBlocker, useNavigate, useParams } from 'react-router-dom'
import { api, type ApiError } from '../api'
import type { AssessmentDoc, AssessmentOut, DataStatus, JobStage } from '../types'
import MapPicker from '../components/MapPicker'
import FacesEditor from '../components/FacesEditor'
import PanelsEditor from '../components/PanelsEditor'
import ReadingsEditor from '../components/ReadingsEditor'
import ResultsView from '../components/ResultsView'
import NumberInput from '../components/NumberInput'
import AuditEditor from '../components/AuditEditor'
import SystemDesign from '../components/SystemDesign'
import DocumentsCard, { documentState } from '../components/DocumentsCard'
import ErrorBoundary from '../components/ErrorBoundary'
import Field from '../components/Field'
import { PricingInputs, PricingResults } from '../components/PricingSection'
import { CashflowResults, ProgramInputs, ProgramResults } from '../components/ProgramSection'
import { EconomicsInputs, EconomicsResults } from '../components/EconomicsSection'
import { emptyDoc, emptyEconomicsJob, emptyPricingJob, emptyProgramJob, JOB_STAGES, NEW_DRAFT_ID } from '../types'
import { clearDraft, readDraft, writeDraft, type Draft } from '../draft'
import { fmtDateShort, fmtDateTime, php0 } from '../fmt'
import { useNarrow } from '../components/responsive'

type Step = 'site' | 'audit' | 'pricing' | 'results'
const STEPS: { id: Step; label: string; short: string }[] = [
  { id: 'site', label: 'On site', short: 'Site' },
  { id: 'audit', label: 'Energy audit', short: 'Audit' },
  { id: 'pricing', label: 'Pricing and program', short: 'Pricing' },
  { id: 'results', label: 'Design and outputs', short: 'Outputs' },
]
const CARD_STEP: Record<string, Step> = { 'card-site': 'site', 'card-faces': 'site', 'card-panels': 'site', 'card-readings': 'site', 'card-audit': 'audit' }

/** The seven cards of Design and outputs, in order; the in-step index jumps to them. */
type DesignCardId = 'design-roof' | 'design-system' | 'design-quantities' | 'design-program' | 'design-cashflow' | 'design-savings' | 'design-documents'
const DESIGN_CARDS: { id: DesignCardId; label: string; short: string }[] = [
  { id: 'design-roof', label: 'Roof and production', short: 'Roof' },
  { id: 'design-system', label: 'System design', short: 'System' },
  { id: 'design-quantities', label: 'Quantities', short: 'Quantities' },
  { id: 'design-program', label: 'Program', short: 'Program' },
  { id: 'design-cashflow', label: 'Cashflow', short: 'Cashflow' },
  { id: 'design-savings', label: 'Savings for the customer', short: 'Savings' },
  { id: 'design-documents', label: 'Documents', short: 'Documents' },
]
/** The cards that exist before the energy audit is calculated. */
const FIRST_CARDS = new Set<DesignCardId>(['design-roof', 'design-documents'])

/** What the owner reads when Save or Calculate cannot reach the server; the draft on the device keeps the edits. */
const OFFLINE_EDITS_KEPT = 'No connection. Your edits are kept on this phone; Save again when you have signal.'

/** Which card an error message is about, so the page can open its step and scroll there. The messages use the owner's labels (see api.ts). */
function cardForError(msg: string): string | null {
  const m = msg.toLowerCase()
  if (m.includes('location') || m.includes('map pin') || m.includes('weather')) return 'card-site'
  if (m.includes('roof face') || m.includes('no panel fits') || m.includes('face')) return 'card-faces'
  if (m.includes('reading') || m.includes('calibration') || m.includes('test panel') || m.includes('test_panel')) return 'card-readings'
  if (m.includes('panel')) return 'card-panels'
  if (m.includes('audit') || m.includes('consumption') || m.includes('bill') || m.includes('appliance')) return 'card-audit'
  return null
}

function stepFromHash(): Step {
  const h = (window.location.hash || '').replace('#', '')
  return (STEPS.some((s) => s.id === h) ? h : 'site') as Step
}

/** The inputs without the card's next-step line, which is printed and never computed. */
const inputsOf = (d: AssessmentDoc) => JSON.stringify({ ...d, card_next_step: '' })

export default function AssessmentPage({ status }: { status: DataStatus | null }) {
  const { id } = useParams()
  // "/assessments/new" is an unsaved draft: no record exists until the first Save (or Calculate, which saves first)
  const isNew = id === 'new'
  const aid = isNew ? NEW_DRAFT_ID : Number(id)
  const navigate = useNavigate()
  const narrow = useNarrow()
  const [a, setA] = useState<AssessmentOut | null>(null)
  const [doc, setDoc] = useState<AssessmentDoc | null>(null)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [step, setStepState] = useState<Step>(stepFromHash)
  const [activeCard, setActiveCard] = useState<DesignCardId>('design-roof')
  const draftTimer = useRef<number | null>(null)
  const docBusy = useRef(false)
  const heldId = useRef<number | null>(null) // the record id the page already holds, so the URL switch after the first Save does not refetch

  const setStep = useCallback((s: Step) => {
    setStepState(s)
    window.history.replaceState(null, '', `#${s}`)
    window.scrollTo({ top: 0 })
  }, [])

  useEffect(() => {
    const onHash = () => setStepState(stepFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    if (isNew) {
      heldId.current = null
      setA(null)
      setDoc(emptyDoc())
      setDirty(false)
      setError(null)
      setDraft(readDraft(NEW_DRAFT_ID)) // an abandoned new draft on this device can be restored or discarded
      if (stepFromHash() === 'results') setStep('site')
      return
    }
    if (heldId.current === aid) return
    api
      .getAssessment(aid)
      .then((r) => {
        heldId.current = r.id
        setA(r)
        setDoc(r.doc)
        setDirty(false)
        const d = readDraft(aid)
        setDraft(d && JSON.stringify(d.doc) !== JSON.stringify(r.doc) ? d : null)
        if (d && JSON.stringify(d.doc) === JSON.stringify(r.doc)) clearDraft(aid)
        if (!r.results && stepFromHash() === 'results') setStep('site')
      })
      .catch((e) => setError(e.message))
  }, [aid, isNew, setStep])

  // the first Save of a new draft created the record: the URL switches to its id and the page carries on as a saved record
  useEffect(() => {
    if (isNew && a && a.id) navigate(`/assessments/${a.id}#${step}`, { replace: true })
  }, [isNew, a, step, navigate])

  /** Until the server stores card_next_step, keep what was typed for this session so the card still prints it. */
  const withLocalFields = (server: AssessmentDoc, local: AssessmentDoc | null): AssessmentDoc =>
    server.card_next_step == null && local?.card_next_step ? { ...server, card_next_step: local.card_next_step } : server

  const patch = useCallback((p: Partial<AssessmentDoc>) => {
    setDoc((d) => (d ? { ...d, ...p } : d))
    setDirty(true)
  }, [])

  // Unsaved edits: warn before the tab closes, block in-app navigation, and keep a draft on the device.
  useEffect(() => {
    if (!dirty) return
    const onUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener('beforeunload', onUnload)
    return () => window.removeEventListener('beforeunload', onUnload)
  }, [dirty])

  const blocker = useBlocker(dirty)
  useEffect(() => {
    if (blocker.state !== 'blocked') return
    if (window.confirm('You have unsaved changes. Leave without saving? The edits stay as a draft on this device.')) blocker.proceed()
    else blocker.reset()
  }, [blocker])

  useEffect(() => {
    if (!dirty || !doc) return
    if (draftTimer.current) window.clearTimeout(draftTimer.current)
    draftTimer.current = window.setTimeout(() => writeDraft(aid, doc, a?.updated_at ?? ''), 600)
    return () => {
      if (draftTimer.current) window.clearTimeout(draftTimer.current)
    }
  }, [dirty, doc, a, aid])

  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(null), 2500)
    return () => window.clearTimeout(t)
  }, [toast])

  const results = a?.results ?? null

  // the in-step index follows the scroll: the last card whose top has passed the sticky chrome is the current one
  useEffect(() => {
    if (step !== 'results' || !results) return
    let raf = 0
    const onScroll = () => {
      if (raf) return
      raf = window.requestAnimationFrame(() => {
        raf = 0
        let current: DesignCardId = 'design-roof'
        for (const c of DESIGN_CARDS) {
          const el = document.getElementById(c.id)
          if (el && el.getBoundingClientRect().top <= 140) current = c.id
        }
        // at the foot of the page the last card cannot reach the top of the screen, so it is the current one
        if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) current = 'design-documents'
        setActiveCard(current)
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (raf) window.cancelAnimationFrame(raf)
    }
  }, [step, results])

  // only a change to the inputs makes the results stale; the card's next-step line is printed, never computed
  const dirtyInputs = useMemo(() => dirty && (!a || inputsOf(doc!) !== inputsOf(a.doc)), [dirty, doc, a])

  if (error && !doc)
    return (
      <div className="card">
        <div className="banner bad">{error}</div>
        <Link to="/">Back to the list</Link>
      </div>
    )
  if (!doc || (!isNew && !a)) return <div className="muted">Loading...</div>

  /** Shows an error in the bar; a validation error also opens the step and scrolls to the card it names. */
  const fail = (e: unknown) => {
    const offline = (e as ApiError).status === 0
    const msg = offline && dirty ? OFFLINE_EDITS_KEPT : (e as Error).message
    setError(msg)
    if (offline) return
    const card = cardForError(msg)
    if (card) {
      const s = CARD_STEP[card]
      if (s && s !== step) setStep(s)
      setTimeout(() => {
        const el = document.getElementById(card)
        if (!el) return
        const top = el.getBoundingClientRect().top + window.scrollY - 64 // keep the step tabs clear
        window.scrollTo({ top, behavior: 'smooth' })
      }, 150)
    }
  }

  const save = async () => {
    setBusy('Saving...')
    setError(null)
    try {
      const r = isNew ? await api.createAssessment(doc) : await api.updateAssessment(aid, doc)
      heldId.current = r.id
      setA(r)
      setDoc(withLocalFields(r.doc, doc))
      setDirty(false)
      clearDraft(aid)
      setDraft(null)
      setToast('Saved')
    } catch (e) {
      fail(e) // dirty stays true, so Save stays armed for the next try
    } finally {
      setBusy(null)
    }
  }

  const compute = async () => {
    setBusy('Calculating...')
    setError(null)
    try {
      let target = aid
      if (isNew) {
        // Calculate saves first: a new draft becomes a record here, then the model runs on it
        const created = await api.createAssessment(doc)
        target = created.id
        heldId.current = created.id
        setA(created)
        setDirty(false)
        clearDraft(aid)
        setDraft(null)
      }
      const r = await api.computeAssessment(target, doc)
      heldId.current = r.id
      setA(r)
      setDoc(withLocalFields(r.doc, doc))
      setDirty(false)
      clearDraft(aid)
      setDraft(null)
      setToast('Calculated')
      setStep('results')
    } catch (e) {
      fail(e)
    } finally {
      setBusy(null)
    }
  }

  const remove = async () => {
    if (isNew) return
    if (!window.confirm('Delete this project? This cannot be undone.')) return
    setDirty(false)
    clearDraft(aid)
    await api.deleteAssessment(aid)
    navigate('/')
  }

  const restoreDraft = () => {
    if (!draft) return
    setDoc(draft.doc)
    setDirty(true)
    setDraft(null)
  }
  const discardDraft = () => {
    clearDraft(aid)
    setDraft(null)
  }

  const kResults = results?.k.sets ?? null
  // One rule for every document (roof check PDF, card, proposal, program of works, BOM exports): the server answers 409 in the same cases.
  const stale = (a?.results_stale ?? false) || dirtyInputs
  const synthetic = !!results?.dataset.synthetic
  const exportReason = documentState({ customer: false, needs: 'pricing' }, results, stale, synthetic).reason
  const statusText = busy ?? (isNew ? 'Not saved yet' : dirty ? 'Unsaved changes' : a!.results_stale ? 'Needs recalculating' : results ? 'Up to date' : 'Not calculated yet')
  const statusClass = busy ? 'busy' : isNew || dirty ? 'unsaved' : a!.results_stale ? 'stale' : results ? 'ok' : ''

  /**
   * Opens a document without ever landing a tab on a raw error page: the file is fetched first, a 409 or an outage goes to the bar,
   * and only a real file is shown. An inline document (the card) gets a tab opened inside the click, so phone browsers do not block it;
   * an attachment (the PDFs, the exports) is saved under the server's file name, as the plain link did.
   */
  const openDocument = async (url: string, inlineHint = false) => {
    if (docBusy.current) return
    if (!results || stale) {
      setError(stale ? 'Documents need a fresh calculation. Press Calculate first.' : 'Calculate first.')
      return
    }
    docBusy.current = true
    setError(null)
    const win = inlineHint ? window.open('', '_blank') : null
    try {
      if (win) {
        try {
          win.document.title = 'Preparing the card…'
          win.document.body.textContent = 'Preparing the card…'
        } catch {
          /* a cross-origin shell: it still navigates below */
        }
      }
      const d = await api.fetchDocument(url)
      const objectUrl = URL.createObjectURL(d.blob)
      if (d.inline && win) {
        win.location.replace(objectUrl)
      } else {
        win?.close()
        const link = document.createElement('a')
        link.href = objectUrl
        if (d.inline) link.target = '_blank'
        else link.download = d.filename
        link.rel = 'noopener'
        document.body.appendChild(link)
        link.click()
        link.remove()
      }
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
    } catch (e) {
      win?.close()
      fail(e)
    } finally {
      docBusy.current = false
    }
  }

  // the on-site checklist: what Calculate needs
  const hasPin = doc.lat != null && doc.lon != null
  const hasFace = doc.faces.length > 0 && doc.faces.some((f) => f.length_m > 0 && f.width_m > 0)
  const hasPanel = doc.panels.length > 0
  const hasReadings = doc.reading_sets.length > 0
  const canCalculate = hasPin && hasFace && hasPanel && hasReadings  // the model needs one reading set for the k factor

  const sizing = results?.sizing
  const pricing = results?.pricing
  const eco = results?.economics
  const summaryPanels = sizing?.panels ?? results?.production.total_panels
  const summaryKwp = sizing?.kwp ?? results?.production.system_kwp
  const batteryKwh = sizing?.battery?.installed_kwh ?? 0
  const selectedPanel = results?.panels.find((p) => p.panel.id === results.selected_panel_id)?.panel
  // after the first calculation the downstream cards are all "needs the audit": one line says what comes next instead
  const auditPending =
    !!results && !results.sizing && [results.pricing, results.economics, results.program].every((b) => b != null && !b.available)
  const cardAvailable = (c: DesignCardId) => !auditPending || FIRST_CARDS.has(c)
  const stageValue: JobStage = doc.program?.stage ?? 'assessed'

  const go = (cardId: string) => () => document.getElementById(cardId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  const setStage = (stage: JobStage) => patch({ program: { ...(doc.program ?? emptyProgramJob()), stage } })

  return (
    <div>
      {draft && (
        <div className="banner info">
          Unsaved edits from {fmtDateTime(draft.saved_at)} are saved on this device
          {a && draft.base_updated_at !== a.updated_at && ' (the project was saved elsewhere since, so they may be older)'}.{' '}
          <button type="button" className="small primary" onClick={restoreDraft} style={{ marginLeft: 6 }}>
            Restore them
          </button>{' '}
          <button type="button" className="small" onClick={discardDraft}>
            Discard
          </button>
        </div>
      )}

      <div className="page-head">
        <div className="page-head-main">
          <div className="page-head-row">
            <h1 className="page-title">{doc.customer_name || (isNew ? 'New project' : 'Unnamed project')}</h1>
            {/* the job's own stage, saved with the record; lead and contacted live on the Leads page */}
            <select className="stage-pill" aria-label="Job stage" title="Job stage" value={stageValue} onChange={(e) => setStage(e.target.value as JobStage)} data-testid="stage-pill">
              {JOB_STAGES.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div className="muted">
            {doc.address || 'No address yet'}
            {isNew && ' · not saved yet: Save creates the record'}
          </div>
        </div>
      </div>

      <nav className="tabs" aria-label="Steps">
        {STEPS.map((s) => {
          const disabled = s.id === 'results' && !results
          return (
            <button key={s.id} type="button" className={`tab ${step === s.id ? 'on' : ''}`} onClick={() => setStep(s.id)} disabled={disabled} title={disabled ? 'Calculate first' : ''}>
              <span className="tab-long">{s.label}</span>
              <span className="tab-short">{s.short}</span>
              {s.id === 'results' && results && a?.results_stale && <span className="dot warn" title="Needs recalculating" />}
            </button>
          )
        })}
      </nav>
      {!results && <div className="tabs-note muted">Design and outputs open after the first calculation.</div>}

      {step === 'site' && (
        <>
          {!results && (
            <div className="checklist card">
              <b>To calculate, the app needs:</b>
              <span className={`check-item ${hasPin ? 'done' : ''}`}>{hasPin ? '✓' : '○'} Map pin</span>
              <span className={`check-item ${hasFace ? 'done' : ''}`}>{hasFace ? '✓' : '○'} A roof face</span>
              <span className={`check-item ${hasPanel ? 'done' : ''}`}>{hasPanel ? '✓' : '○'} A panel</span>
              <span className={`check-item ${hasReadings ? 'done' : ''}`}>{hasReadings ? '✓' : '○'} Roof readings (one set with three readings)</span>
            </div>
          )}
          <div className="card" id="card-site">
            <h2>Site</h2>
            <div className="row">
              <Field label="Customer name">{(fid) => <input id={fid} value={doc.customer_name} onChange={(e) => patch({ customer_name: e.target.value })} />}</Field>
              <Field label="Address">{(fid) => <input id={fid} value={doc.address} onChange={(e) => patch({ address: e.target.value })} />}</Field>
            </div>
            <Field label="Notes (internal)" className="field">
              {(fid) => <textarea id={fid} rows={2} value={doc.notes} onChange={(e) => patch({ notes: e.target.value })} />}
            </Field>
            <MapPicker lat={doc.lat} lon={doc.lon} onChange={(lat, lon) => patch({ lat, lon })} />
            {!isNew && (
              <div className="card-foot">
                <button type="button" className="danger" onClick={remove} disabled={!!busy}>
                  Delete project
                </button>
              </div>
            )}
          </div>

          <div className="card" id="card-faces">
            <h2>Roof faces</h2>
            <FacesEditor faces={doc.faces} warnings={dirty ? null : results?.warnings} onChange={(faces) => patch({ faces })} />
            <div className="row" style={{ marginTop: 10 }}>
              <Field label="Edge setback (m)" className="narrow" style={{ width: 160 }}>
                {(fid) => <NumberInput id={fid} value={doc.setback_m} onChange={(v) => patch({ setback_m: v ?? 0 })} min={0} step={0.1} />}
              </Field>
              <Field label="Gap between panels (m)" className="narrow" style={{ width: 160 }}>
                {(fid) => <NumberInput id={fid} value={doc.gap_m} onChange={(v) => patch({ gap_m: v ?? 0 })} min={0} step={0.01} />}
              </Field>
            </div>
          </div>

          <div className="card" id="card-panels">
            <h2>Panel options</h2>
            <PanelsEditor
              panels={doc.panels}
              selectedId={doc.selected_panel_id}
              results={results?.panels ?? null}
              onChange={(panels) => patch({ panels })}
              onSelect={(selected_panel_id) => patch({ selected_panel_id })}
            />
          </div>

          <div className="card" id="card-readings">
            <h2>Roof readings</h2>
            <div className="row" style={{ marginBottom: 10 }}>
              <Field label="Test panel rating (W)" className="narrow" style={{ width: 160 }}>
                {(fid) => <NumberInput id={fid} value={doc.test_panel_rating_w} onChange={(v) => patch({ test_panel_rating_w: v ?? 50 })} min={1} />}
              </Field>
              <Field label="Calibration factor" className="narrow" style={{ width: 200 }}>
                {(fid) => <NumberInput id={fid} value={doc.test_panel_calibration} onChange={(v) => patch({ test_panel_calibration: v ?? 1 })} min={0.5} max={1.5} step={0.01} />}
              </Field>
            </div>
            <ReadingsEditor
              sets={doc.reading_sets}
              faces={doc.faces}
              results={dirty ? null : kResults}
              selectedIndex={results?.k.selected_set_index}
              onChange={(reading_sets) => patch({ reading_sets })}
            />
          </div>
        </>
      )}

      {step === 'audit' && (
        <div className="card" id="card-audit">
          <h2>Energy audit</h2>
          <AuditEditor audit={doc.audit} onChange={(audit) => patch({ audit })} />
        </div>
      )}

      {step === 'pricing' && (
        <>
          {!results?.sizing && <div className="banner info">Pricing and the program follow the sizing. Finish the energy audit and calculate once; these inputs are then prefilled from the settings.</div>}
          <div className="card" id="card-pricing-inputs">
            <h2>Pricing inputs</h2>
            <PricingInputs job={doc.pricing ?? emptyPricingJob()} pricing={results?.pricing ?? null} onChange={(pricing) => patch({ pricing })} />
          </div>
          <div className="card" id="card-economics-inputs">
            <h2>Savings inputs</h2>
            <EconomicsInputs job={doc.economics ?? emptyEconomicsJob()} eco={results?.economics ?? null} onChange={(economics) => patch({ economics })} />
          </div>
          <div className="card" id="card-program-inputs">
            <h2>Schedule and cashflow inputs</h2>
            <ProgramInputs job={doc.program ?? emptyProgramJob()} program={results?.program ?? null} onChange={(program) => patch({ program })} />
          </div>
        </>
      )}

      {step === 'results' && !results && (
        <div className="card">
          <div className="muted">Nothing calculated yet. Fill in the site, one roof face and a panel, then press Calculate.</div>
        </div>
      )}

      {step === 'results' && results && (
        <>
          {stale && (
            <div className="banner warn stale-banner">
              <span>Inputs changed since the last calculation. These results are out of date.</span>
              <button type="button" className="small primary" onClick={compute} disabled={!!busy || !status?.pvgis.available}>
                Calculate
              </button>
            </div>
          )}
          <div className={stale ? 'stale' : ''}>
            <div className="card summary" id="design-glance">
              <h2>At a glance</h2>
              <div className="kpis">
                <button type="button" className="kpi kpi-link" onClick={go('design-roof')}>
                  <div className="label">{sizing ? 'Recommended system' : 'Roof can hold'}</div>
                  <div className="value">
                    {summaryPanels} panels · {summaryKwp?.toFixed(2)} kWp
                  </div>
                  <div className="sub">{batteryKwh > 0 ? `${batteryKwh.toFixed(0)} kWh battery` : sizing ? 'no battery' : 'full roof'}</div>
                </button>
                {pricing?.available && pricing.totals && (
                  <button type="button" className="kpi kpi-link" onClick={go('design-quantities')}>
                    <div className="label">Contract price</div>
                    <div className="value">{php0(pricing.totals.contract_rounded)}</div>
                    <div className="sub">VAT included</div>
                  </button>
                )}
                {eco?.available && (
                  <>
                    <button type="button" className="kpi kpi-link" onClick={go('design-savings')}>
                      <div className="label">Monthly bill</div>
                      <div className="value">
                        {php0(eco.bill_before_monthly)} → {php0(eco.bill_after_monthly)}
                      </div>
                      <div className="sub">about {php0(eco.savings_monthly)} less a month</div>
                    </button>
                    <button type="button" className="kpi kpi-link" onClick={go('design-savings')}>
                      <div className="label">Pays for itself in</div>
                      <div className="value">{eco.payback_years != null ? `${eco.payback_years.toFixed(1)} years` : `more than ${eco.assumptions?.analysis_years ?? 25} years`}</div>
                      <div className="sub">{php0(eco.year1?.savings)} saved in year one</div>
                    </button>
                  </>
                )}
                {results.program?.available && (
                  <button type="button" className="kpi kpi-link" onClick={go('design-program')}>
                    <div className="label">Installation</div>
                    <div className="value">{results.program.install_start ? fmtDateShort(results.program.install_start) : '-'}</div>
                    <div className="sub">{results.program.install?.days} {results.program.install?.days === 1 ? 'day' : 'days'} on site</div>
                  </button>
                )}
              </div>
            </div>

            {/* the in-step index: sticky sub-tabs on the desk, a jump list on the phone */}
            <nav className={`subtabs ${narrow ? 'jump-list' : ''}`} aria-label="Design and outputs">
              {DESIGN_CARDS.map((c) => (
                <button key={c.id} type="button" className={`subtab ${activeCard === c.id ? 'on' : ''}`} disabled={!cardAvailable(c.id)} onClick={go(c.id)} aria-current={activeCard === c.id ? 'location' : undefined}>
                  <span className="sub-long">{c.label}</span>
                  <span className="sub-short">{c.short}</span>
                </button>
              ))}
            </nav>
            {auditPending && <div className="subtabs-note muted">System design, quantities, the program, cashflow and savings follow the energy audit.</div>}

            <div className="card design-card" id="design-roof">
              <h2>Roof and production</h2>
              <ErrorBoundary title="The production results" onRecalculate={compute}>
                <ResultsView doc={a!.doc} results={results} />
              </ErrorBoundary>
            </div>

            {auditPending ? (
              <div className="card next-step" id="design-system">
                Next:{' '}
                <a
                  href="#audit"
                  onClick={(e) => {
                    e.preventDefault()
                    setStep('audit')
                  }}
                >
                  Energy audit
                </a>
                , then Calculate. <span className="muted">System design, quantities, the program of works, cashflow and savings follow the sizing.</span>
              </div>
            ) : (
              <>
                <div className="card design-card" id="design-system">
                  <h2>System design</h2>
                  <ErrorBoundary title="The system design" onRecalculate={compute}>
                    <SystemDesign results={results} panelName={selectedPanel?.name || ''} panelWp={selectedPanel?.watt_peak || 0} />
                  </ErrorBoundary>
                </div>
                <div className="card design-card" id="design-quantities">
                  <h2>Quantities</h2>
                  <ErrorBoundary title="The quantities" onRecalculate={compute}>
                    {results.pricing ? (
                      <PricingResults
                        pricing={results.pricing}
                        job={doc.pricing ?? emptyPricingJob()}
                        onJobChange={(pricing) => patch({ pricing })}
                        exportUrls={{ csv: api.bomCsvUrl(aid), xlsx: api.bomXlsxUrl(aid) }}
                        docReason={exportReason}
                        openDocument={openDocument}
                      />
                    ) : (
                      <div className="muted">Quantities follow the sizing. Press Calculate.</div>
                    )}
                  </ErrorBoundary>
                </div>
                <div className="card design-card" id="design-program">
                  <h2>Program of works</h2>
                  <ErrorBoundary title="The program of works" onRecalculate={compute}>
                    {results.program ? <ProgramResults program={results.program} /> : <div className="muted">The program follows the pricing. Press Calculate.</div>}
                  </ErrorBoundary>
                </div>
                <div className="card design-card" id="design-cashflow">
                  <h2>Cashflow</h2>
                  <ErrorBoundary title="The cashflow" onRecalculate={compute}>
                    {results.program ? <CashflowResults program={results.program} /> : <div className="muted">The cashflow follows the pricing. Press Calculate.</div>}
                  </ErrorBoundary>
                </div>
                <div className="card design-card" id="design-savings">
                  <h2>Savings for the customer</h2>
                  <ErrorBoundary title="The savings" onRecalculate={compute}>
                    {results.economics ? <EconomicsResults eco={results.economics} /> : <div className="muted">The savings follow the pricing. Press Calculate.</div>}
                  </ErrorBoundary>
                </div>
              </>
            )}

            <div className="card design-card" id="design-documents">
              <h2>Documents</h2>
              <DocumentsCard
                results={results}
                stale={stale}
                synthetic={synthetic}
                busy={!!busy}
                nextStep={doc.card_next_step ?? ''}
                onNextStepChange={(card_next_step) => patch({ card_next_step })}
                urls={{
                  report: api.reportUrl(aid),
                  card: api.cardUrl(aid, (doc.card_next_step ?? '').trim()),
                  proposal: api.quotationUrl(aid),
                  program: api.programUrl(aid),
                  bomCsv: api.bomCsvUrl(aid),
                  bomXlsx: api.bomXlsxUrl(aid),
                }}
                openDocument={openDocument}
              />
            </div>
          </div>
        </>
      )}

      <div className="actions">
        {error && (
          <div className="banner bad" role="alert">
            {error}
          </div>
        )}
        <span className={`chip ${statusClass}`}>{toast ?? statusText}</span>
        <button onClick={save} disabled={!!busy || !dirty}>
          Save{dirty ? ' •' : ''}
        </button>
        <button
          className="primary"
          onClick={compute}
          disabled={!!busy || !status?.pvgis.available || !canCalculate}
          title={!status?.pvgis.available ? 'Weather data is not downloaded yet' : !canCalculate ? 'Needs a map pin, a roof face, a panel and one reading set' : 'Saves, then runs the model'}
        >
          Calculate
        </button>
        {!results && !canCalculate && <span className="muted bar-note">Needs a map pin, a roof face, a panel and one reading set.</span>}
        {status && !status.pvgis.available && <span className="muted bar-note">Weather data is not downloaded yet; see Settings.</span>}
      </div>
    </div>
  )
}
