import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import type { AssessmentDoc, AssessmentOut, DataStatus } from '../types'
import MapPicker from '../components/MapPicker'
import FacesEditor from '../components/FacesEditor'
import PanelsEditor from '../components/PanelsEditor'
import ReadingsEditor from '../components/ReadingsEditor'
import ResultsView from '../components/ResultsView'
import NumberInput from '../components/NumberInput'

export default function AssessmentPage({ status }: { status: DataStatus | null }) {
  const { id } = useParams()
  const aid = Number(id)
  const navigate = useNavigate()
  const [a, setA] = useState<AssessmentOut | null>(null)
  const [doc, setDoc] = useState<AssessmentDoc | null>(null)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getAssessment(aid)
      .then((r) => {
        setA(r)
        setDoc(r.doc)
        setDirty(false)
      })
      .catch((e) => setError(e.message))
  }, [aid])

  const patch = useCallback((p: Partial<AssessmentDoc>) => {
    setDoc((d) => (d ? { ...d, ...p } : d))
    setDirty(true)
  }, [])

  if (error && !doc) return <div className="banner bad">{error}</div>
  if (!doc || !a) return <div className="muted">Loading...</div>

  const save = async () => {
    setBusy('Saving...')
    setError(null)
    try {
      const r = await api.updateAssessment(aid, doc)
      setA(r)
      setDoc(r.doc)
      setDirty(false)
    } catch (e) {
      setError((e as Error).message)
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
      setTimeout(() => document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  const remove = async () => {
    if (!window.confirm('Delete this assessment? This cannot be undone.')) return
    await api.deleteAssessment(aid)
    navigate('/')
  }

  const results = a.results
  const kResults = results?.k.sets ?? null
  const pdfAllowed = results && !a.results_stale && !results.dataset.synthetic

  return (
    <div>
      <div className="card">
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

      <div className="card">
        <h2>Roof faces</h2>
        <FacesEditor faces={doc.faces} onChange={(faces) => patch({ faces })} />
        <div className="row" style={{ marginTop: 10 }}>
          <div className="narrow" style={{ width: 160 }}>
            <label>Setback per dimension (m)</label>
            <NumberInput value={doc.setback_m} onChange={(v) => patch({ setback_m: v ?? 0 })} min={0} step={0.1} />
          </div>
          <div className="narrow" style={{ width: 160 }}>
            <label>Gap between panels (m)</label>
            <NumberInput value={doc.gap_m} onChange={(v) => patch({ gap_m: v ?? 0 })} min={0} step={0.01} />
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Candidate panels</h2>
        <PanelsEditor
          panels={doc.panels}
          selectedId={doc.selected_panel_id}
          results={results?.panels ?? null}
          onChange={(panels) => patch({ panels })}
          onSelect={(selected_panel_id) => patch({ selected_panel_id })}
        />
      </div>

      <div className="card">
          <h2>On-site readings</h2>
          <div className="row" style={{ marginBottom: 10 }}>
            <div className="narrow" style={{ width: 160 }}>
              <label>Test panel rating (W)</label>
              <NumberInput value={doc.test_panel_rating_w} onChange={(v) => patch({ test_panel_rating_w: v ?? 50 })} min={1} />
            </div>
            <div className="narrow" style={{ width: 200 }}>
              <label>Test panel calibration factor</label>
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

      {error && <div className="banner bad">{error}</div>}
      <div className="actions">
        <button onClick={save} disabled={!!busy || !dirty}>
          Save
        </button>
        <button className="primary" onClick={compute} disabled={!!busy || !status?.pvgis.available}>
          Save and compute
        </button>
        {results && (
          <a href={pdfAllowed ? api.reportUrl(aid) : undefined} onClick={(e) => !pdfAllowed && e.preventDefault()}>
            <button disabled={!pdfAllowed} title={!pdfAllowed ? 'Compute with current inputs on real data first' : ''}>
              Customer PDF
            </button>
          </a>
        )}
        <button className="danger" onClick={remove} disabled={!!busy}>
          Delete
        </button>
        <span className="muted">{busy ?? (dirty ? 'Unsaved changes' : a.results_stale ? 'Edited since last compute' : '')}</span>
      </div>

      {results && (
        <div className="card" id="results">
          <h2>Results</h2>
          <ResultsView doc={a.doc} results={results} stale={a.results_stale || dirty} />
        </div>
      )}
    </div>
  )
}
