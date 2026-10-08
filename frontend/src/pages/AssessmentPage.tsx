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
import { fmtDateTime, php0 } from '../fmt'

type Step = 'site' | 'audit' | 'pricing' | 'results'
const STEPS: { id: Step; label: string; short: string }[] = [
  { id: 'site', label: 'On site', short: 'Site' },
  { id: 'audit', label: 'Energy audit', short: 'Audit' },
  { id: 'pricing', label: 'Pricing and program', short: 'Pricing' },
  { id: 'results', label: 'Results', short: 'Results' },
]
const CARD_STEP: Record<string, Step> = { 'card-site': 'site', 'card-faces': 'site', 'card-panels': 'site', 'card-readings': 'site', 'card-audit': 'audit' }

/** Which card an error message is about, so the page can open its step and scroll there. */
function cardForError(msg: string): string | null {
  const m = msg.toLowerCase()
  if (m.includes('location') || m.includes('map pin') || m.includes('weather')) return 'card-site'
  if (m.includes('roof face') || m.includes('no panel fits') || m.includes('face')) return 'card-faces'
  if (m.includes('reading') || m.includes('calibration') || m.includes('test_panel')) return 'card-readings'
  if (m.includes('panel')) return 'card-panels'
  if (m.includes('audit') || m.includes('consumption') || m.includes('bill') || m.includes('appliance')) return 'card-audit'
  return null
}

function stepFromHash(): Step {
  const h = (window.location.hash || '').replace('#', '')
  return (STEPS.some((s) => s.id === h) ? h : 'site') as Step
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
  const [step, setStepState] = useState<Step>(stepFromHash)
  const draftTimer = useRef<number | null>(null)

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
    api
      .getAssessment(aid)
      .then((r) => {
        setA(r)
        setDoc(r.doc)
        setDirty(false)
        const d = readDraft(aid)
        setDraft(d && JSON.stringify(d.doc) !== JSON.stringify(r.doc) ? d : null)
        if (d && JSON.stringify(d.doc) === JSON.stringify(r.doc)) clearDraft(aid)
        if (!r.results && stepFromHash() === 'results') setStep('site')
      })
      .catch((e) => setError(e.message))
  }, [aid, setStep])

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
    setBusy('Calculating...')
    setError(null)
    try {
      const r = await api.computeAssessment(aid, doc)
      setA(r)
      setDoc(r.doc)
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
  const stale = a.results_stale || dirty
  const pdfAllowed = results && !a.results_stale && !results.dataset.synthetic
  const statusText = busy ?? (dirty ? 'Unsaved changes' : a.results_stale ? 'Needs recalculating' : results ? 'Up to date' : 'Not calculated yet')
  const statusClass = busy ? 'busy' : dirty ? 'unsaved' : a.results_stale ? 'stale' : results ? 'ok' : ''

  // the on-site checklist: what Calculate needs
  const hasPin = doc.lat != null && doc.lon != null
  const hasFace = doc.faces.length > 0 && doc.faces.some((f) => f.length_m > 0 && f.width_m > 0)
  const hasPanel = doc.panels.length > 0
  const hasReadings = doc.reading_sets.length > 0
  const canCalculate = hasPin && hasFace && hasPanel

  const sizing = results?.sizing
  const pricing = results?.pricing
  const eco = results?.economics
  const summaryPanels = sizing?.panels ?? results?.production.total_panels
  const summaryKwp = sizing?.kwp ?? results?.production.system_kwp
  const batteryKwh = sizing?.battery?.installed_kwh ?? 0

  const go = (cardId: string) => () => document.getElementById(cardId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

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

      <div className="page-head">
        <div>
          <h1 className="page-title">{doc.customer_name || 'New assessment'}</h1>
          <div className="muted">{doc.address || 'No address yet'}</div>
        </div>
      </div>

      <nav className="tabs" aria-label="Steps">
        {STEPS.map((s) => {
          const disabled = s.id === 'results' && !results
          return (
            <button key={s.id} type="button" className={`tab ${step === s.id ? 'on' : ''}`} onClick={() => setStep(s.id)} disabled={disabled} title={disabled ? 'Calculate first' : ''}>
              <span className="tab-long">{s.label}</span>
              <span className="tab-short">{s.short}</span>
              {s.id === 'results' && results && a.results_stale && <span className="dot warn" title="Needs recalculating" />}
            </button>
          )
        })}
      </nav>

      {step === 'site' && (
        <>
          {!results && (
            <div className="checklist card">
              <b>To calculate, the app needs:</b>
              <span className={`check-item ${hasPin ? 'done' : ''}`}>{hasPin ? '✓' : '○'} Map pin</span>
              <span className={`check-item ${hasFace ? 'done' : ''}`}>{hasFace ? '✓' : '○'} A roof face</span>
              <span className={`check-item ${hasPanel ? 'done' : ''}`}>{hasPanel ? '✓' : '○'} A panel</span>
              <span className={`check-item ${hasReadings ? 'done' : ''}`}>{hasReadings ? '✓' : '○'} Roof readings (optional)</span>
            </div>
          )}
          <div className="card" id="card-site">
            <div className="card-head">
              <h2>Site</h2>
              <button type="button" className="toggle link danger" onClick={remove} disabled={!!busy}>
                Delete assessment
              </button>
            </div>
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
            <div className="card summary">
              <h2>At a glance</h2>
              <div className="kpis">
                <button type="button" className="kpi kpi-link" onClick={go('results-production')}>
                  <div className="label">{sizing ? 'Recommended system' : 'Roof can hold'}</div>
                  <div className="value">
                    {summaryPanels} panels · {summaryKwp?.toFixed(2)} kWp
                  </div>
                  <div className="sub">{batteryKwh > 0 ? `${batteryKwh.toFixed(0)} kWh battery` : sizing ? 'no battery' : 'full roof'}</div>
                </button>
                {pricing?.available && pricing.totals && (
                  <button type="button" className="kpi kpi-link" onClick={go('pricing')}>
                    <div className="label">Contract price</div>
                    <div className="value">{php0(pricing.totals.contract_rounded)}</div>
                    <div className="sub">VAT included</div>
                  </button>
                )}
                {eco?.available && (
                  <>
                    <button type="button" className="kpi kpi-link" onClick={go('economics')}>
                      <div className="label">Monthly bill</div>
                      <div className="value">
                        {php0(eco.bill_before_monthly)} → {php0(eco.bill_after_monthly)}
                      </div>
                      <div className="sub">about {php0(eco.savings_monthly)} less a month</div>
                    </button>
                    <button type="button" className="kpi kpi-link" onClick={go('economics')}>
                      <div className="label">Pays for itself in</div>
                      <div className="value">{eco.payback_years != null ? `${eco.payback_years.toFixed(1)} years` : `more than ${eco.assumptions?.analysis_years ?? 25} years`}</div>
                      <div className="sub">{php0(eco.year1?.savings)} saved in year one</div>
                    </button>
                  </>
                )}
                {results.program?.available && (
                  <button type="button" className="kpi kpi-link" onClick={go('program')}>
                    <div className="label">Installation</div>
                    <div className="value">{results.program.install_start ? new Date(results.program.install_start + 'T00:00:00').toLocaleDateString('en-PH', { day: 'numeric', month: 'short' }) : '-'}</div>
                    <div className="sub">{results.program.install?.days} {results.program.install?.days === 1 ? 'day' : 'days'} on site</div>
                  </button>
                )}
              </div>
            </div>

            <div className="card" id="results-production">
              <h2>Roof and production</h2>
              <ErrorBoundary title="The production results" onRecalculate={compute}>
                <ResultsView doc={a.doc} results={results} stale={false} />
              </ErrorBoundary>
            </div>
            {results.audit && (
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
            {results.pricing && (
              <div className="card" id="pricing">
                <h2>Pricing and bill of materials</h2>
                <ErrorBoundary title="The pricing" onRecalculate={compute}>
                  <PricingResults
                    pricing={results.pricing}
                    job={doc.pricing ?? emptyPricingJob()}
                    onJobChange={(pricing) => patch({ pricing })}
                    quotationUrl={api.quotationUrl(aid)}
                    stale={false}
                  />
                </ErrorBoundary>
              </div>
            )}
            {results.economics && (
              <div className="card" id="economics">
                <h2>Savings for the customer</h2>
                <ErrorBoundary title="The savings" onRecalculate={compute}>
                  <EconomicsResults eco={results.economics} />
                </ErrorBoundary>
              </div>
            )}
            {results.program && (
              <div className="card" id="program">
                <h2>Program of works and cashflow</h2>
                <ErrorBoundary title="The program of works" onRecalculate={compute}>
                  <ProgramResults program={results.program} programUrl={api.programUrl(aid)} stale={false} />
                </ErrorBoundary>
              </div>
            )}
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
          title={!status?.pvgis.available ? 'Weather data is not downloaded yet' : !canCalculate ? 'Needs a map pin, a roof face and a panel' : 'Saves, then runs the model'}
        >
          Calculate
        </button>
        {results && (
          <a href={pdfAllowed ? api.reportUrl(aid) : undefined} onClick={(e) => !pdfAllowed && e.preventDefault()}>
            <button disabled={!pdfAllowed} title={!pdfAllowed ? 'Calculate with current inputs on real data first' : ''}>
              Roof check PDF
            </button>
          </a>
        )}
        {results && (
          <button
            disabled={!pdfAllowed}
            title={!pdfAllowed ? 'Calculate with current inputs on real data first' : 'Phone-sized image to send to the customer'}
            onClick={() => {
              const t = window.prompt('Next step shown on the card. A date and time help, e.g. "Energy audit: Saturday 18 Oct, 9 am, about an hour".', 'Next step: your free energy audit')
              if (t === null) return
              window.open(`${api.cardUrl(aid)}?next_step=${encodeURIComponent(t.trim())}`, '_blank', 'noopener')
            }}
          >
            Roof check card
          </button>
        )}
        {results && !pdfAllowed && <span className="muted">Documents need a fresh calculation on real data.</span>}
        {!results && !canCalculate && <span className="muted">Needs a map pin, a roof face and a panel.</span>}
      </div>
    </div>
  )
}
