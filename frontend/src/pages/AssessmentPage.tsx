import { useCallback, useEffect, useRef, useState } from 'react'
import { useBlocker, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import type { AssessmentDoc, AssessmentOut, DataStatus } from '../types'
import MapPicker from '../components/MapPicker'
import FacesEditor from '../components/FacesEditor'
import PanelsEditor from '../components/PanelsEditor'
import ReadingsEditor from '../components/ReadingsEditor'
import ResultsView from '../components/ResultsView'
import NumberInput from '../components/NumberInput'
import AuditEditor from '../components/AuditEditor'
import AuditResults from '../components/AuditResults'
import ErrorBoundary from '../components/ErrorBoundary'
import { PricingInputs, PricingResults } from '../components/PricingSection'
import { ProgramInputs, ProgramResults } from '../components/ProgramSection'
import { EconomicsInputs, EconomicsResults } from '../components/EconomicsSection'
import { emptyEconomicsJob, emptyPricingJob, emptyProgramJob } from '../types'
import { clearDraft, readDraft, writeDraft, type Draft } from '../draft'
import { fmtDateTime } from '../fmt'

/** Which card an error message is about, so the page can scroll there. */
function cardForError(msg: string): string | null {
  const m = msg.toLowerCase()
  if (m.includes('location') || m.includes('map pin') || m.includes('weather')) return 'card-site'
  if (m.includes('roof face') || m.includes('no panel fits') || m.includes('face')) return 'card-faces'
  if (m.includes('reading')) return 'card-readings'
  if (m.includes('panel')) return 'card-panels'
  if (m.includes('audit') || m.includes('consumption') || m.includes('bill') || m.includes('appliance')) return 'card-audit'
  return null
}

export default function AssessmentPage({ status }: { status: DataStatus | null }) {
  const { id } = useParams()
  const aid = Number(id)
  const navigate = useNavigate()
  const [a, setA] = useState<AssessmentOut | null>(null)
  const [doc, setDoc] = useState<AssessmentDoc | null>(null)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const draftTimer = useRef<number | null>(null)

  useEffect(() => {
    api
      .getAssessment(aid)
      .then((r) => {
        setA(r)
        setDoc(r.doc)
        setDirty(false)
        const d = readDraft(aid)
        setDraft(d && JSON.stringify(d.doc) !== JSON.stringify(r.doc) ? d : null)
        if (d && JSON.stringify(d.doc) === JSON.stringify(r.doc)) clearDraft(aid)
      })
      .catch((e) => setError(e.message))
  }, [aid])

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
    if (!dirty || !doc || !a) return
    if (draftTimer.current) window.clearTimeout(draftTimer.current)
    draftTimer.current = window.setTimeout(() => writeDraft(aid, doc, a.updated_at), 600)
    return () => {
      if (draftTimer.current) window.clearTimeout(draftTimer.current)
    }
  }, [dirty, doc, a, aid])

  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(null), 2500)
    return () => window.clearTimeout(t)
  }, [toast])

  if (error && !doc) return <div className="banner bad">{error}</div>
  if (!doc || !a) return <div className="muted">Loading...</div>

  const fail = (e: unknown) => {
    const msg = (e as Error).message
    setError(msg)
    const card = cardForError(msg)
    if (card) document.getElementById(card)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const save = async () => {
    setBusy('Saving...')
    setError(null)
    try {
      const r = await api.updateAssessment(aid, doc)
      setA(r)
      setDoc(r.doc)
      setDirty(false)
      clearDraft(aid)
      setDraft(null)
      setToast('Saved')
    } catch (e) {
      fail(e)
    } finally {
      setBusy(null)
    }
  }

  const compute = async () => {
    setBusy('Computing...')
    setError(null)
    try {
      const r = await api.computeAssessment(aid, doc)
      setA(r)
      setDoc(r.doc)
      setDirty(false)
      clearDraft(aid)
      setDraft(null)
      setToast('Saved and computed')
      setTimeout(() => document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (e) {
      fail(e)
    } finally {
      setBusy(null)
    }
  }

  const remove = async () => {
    if (!window.confirm('Delete this assessment? This cannot be undone.')) return
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

  const results = a.results
  const kResults = results?.k.sets ?? null
  const pdfAllowed = results && !a.results_stale && !results.dataset.synthetic
  const statusText = busy ?? (dirty ? 'Unsaved changes' : a.results_stale ? 'Needs recalculating' : results ? 'Up to date' : '')
  const statusClass = busy ? 'busy' : dirty ? 'unsaved' : a.results_stale ? 'stale' : 'ok'

  return (
    <div>
      {draft && (
        <div className="banner info">
          Unsaved edits from {fmtDateTime(draft.saved_at)} are saved on this device
          {draft.base_updated_at !== a.updated_at && ' (the assessment was saved elsewhere since, so they may be older)'}.{' '}
          <button type="button" className="small primary" onClick={restoreDraft} style={{ marginLeft: 6 }}>
            Restore them
          </button>{' '}
          <button type="button" className="small" onClick={discardDraft}>
            Discard
          </button>
        </div>
      )}

      <div className="card" id="card-site">
        <h2>Site</h2>
        <div className="row">
          <div>
            <label>Customer name</label>
            <input value={doc.customer_name} onChange={(e) => patch({ customer_name: e.target.value })} />
          </div>
          <div>
            <label>Address</label>
            <input value={doc.address} onChange={(e) => patch({ address: e.target.value })} />
          </div>
        </div>
        <div className="field">
          <label>Notes (internal)</label>
          <textarea rows={2} value={doc.notes} onChange={(e) => patch({ notes: e.target.value })} />
        </div>
        <MapPicker lat={doc.lat} lon={doc.lon} onChange={(lat, lon) => patch({ lat, lon })} />
      </div>

      <div className="card" id="card-faces">
        <h2>Roof faces</h2>
        <FacesEditor faces={doc.faces} onChange={(faces) => patch({ faces })} />
        <div className="row" style={{ marginTop: 10 }}>
          <div className="narrow" style={{ width: 160 }}>
            <label>Edge setback (m)</label>
            <NumberInput value={doc.setback_m} onChange={(v) => patch({ setback_m: v ?? 0 })} min={0} step={0.1} />
          </div>
          <div className="narrow" style={{ width: 160 }}>
            <label>Gap between panels (m)</label>
            <NumberInput value={doc.gap_m} onChange={(v) => patch({ gap_m: v ?? 0 })} min={0} step={0.01} />
          </div>
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
          <div className="narrow" style={{ width: 160 }}>
            <label>Test panel rating (W)</label>
            <NumberInput value={doc.test_panel_rating_w} onChange={(v) => patch({ test_panel_rating_w: v ?? 50 })} min={1} />
          </div>
          <div className="narrow" style={{ width: 200 }}>
            <label>Calibration factor</label>
            <NumberInput value={doc.test_panel_calibration} onChange={(v) => patch({ test_panel_calibration: v ?? 1 })} min={0.5} max={1.5} step={0.01} />
          </div>
        </div>
        <ReadingsEditor
          sets={doc.reading_sets}
          faces={doc.faces}
          results={dirty ? null : kResults}
          selectedIndex={results?.k.selected_set_index}
          onChange={(reading_sets) => patch({ reading_sets })}
        />
      </div>

      <div className="card" id="card-audit">
        <h2>Energy audit</h2>
        <AuditEditor audit={doc.audit} onChange={(audit) => patch({ audit })} />
      </div>

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
        <button className="primary" onClick={compute} disabled={!!busy || !status?.pvgis.available} title={!status?.pvgis.available ? 'Weather data is not downloaded yet' : ''}>
          Save and compute
        </button>
        {results && (
          <a href={pdfAllowed ? api.reportUrl(aid) : undefined} onClick={(e) => !pdfAllowed && e.preventDefault()}>
            <button disabled={!pdfAllowed} title={!pdfAllowed ? 'Compute with current inputs on real data first' : ''}>
              Roof check PDF
            </button>
          </a>
        )}
        {results && (
          <a href={pdfAllowed ? api.cardUrl(aid) : undefined} target="_blank" rel="noreferrer" onClick={(e) => !pdfAllowed && e.preventDefault()}>
            <button disabled={!pdfAllowed} title={!pdfAllowed ? 'Compute with current inputs on real data first' : 'Phone-sized image to send to the customer'}>
              Roof check card
            </button>
          </a>
        )}
        {results && !pdfAllowed && <span className="muted">Documents need a fresh compute on real data.</span>}
        <button className="danger" onClick={remove} disabled={!!busy} style={{ marginLeft: 'auto' }}>
          Delete
        </button>
      </div>

      {results && (
        <div className="card" id="results">
          <h2>Results</h2>
          <ErrorBoundary title="The production results" onRecalculate={compute}>
            <ResultsView doc={a.doc} results={results} stale={a.results_stale || dirty} />
          </ErrorBoundary>
        </div>
      )}
      {results && results.audit && (
        <div className="card" id="sizing">
          <h2>Energy audit and system sizing</h2>
          <ErrorBoundary title="The sizing results" onRecalculate={compute}>
            <AuditResults
              audit={results.audit}
              sizing={results.sizing}
              panelName={results.panels.find((p) => p.panel.id === results.selected_panel_id)?.panel.name || ''}
              panelWp={results.panels.find((p) => p.panel.id === results.selected_panel_id)?.panel.watt_peak || 0}
            />
          </ErrorBoundary>
        </div>
      )}
      {results && results.pricing && (
        <div className="card" id="pricing">
          <h2>Pricing and bill of materials</h2>
          <ErrorBoundary title="The pricing" onRecalculate={compute}>
            <PricingResults
              pricing={results.pricing}
              job={doc.pricing ?? emptyPricingJob()}
              onJobChange={(pricing) => patch({ pricing })}
              quotationUrl={api.quotationUrl(aid)}
              stale={a.results_stale || dirty}
            />
          </ErrorBoundary>
        </div>
      )}
      {results && results.economics && (
        <div className="card" id="economics">
          <h2>Savings for the customer</h2>
          <ErrorBoundary title="The savings" onRecalculate={compute}>
            <EconomicsResults eco={results.economics} />
          </ErrorBoundary>
        </div>
      )}
      {results && results.program && (
        <div className="card" id="program">
          <h2>Program of works and cashflow</h2>
          <ErrorBoundary title="The program of works" onRecalculate={compute}>
            <ProgramResults program={results.program} programUrl={api.programUrl(aid)} stale={a.results_stale || dirty} />
          </ErrorBoundary>
        </div>
      )}
    </div>
  )
}
