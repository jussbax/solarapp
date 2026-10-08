import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { JOB_STAGES, type AssessmentSummary, type JobStage } from '../types'
import { fmtDateTime, plural } from '../fmt'

/** The project list: one record per site, engineering facts only. Website bookings live on the Leads page until Start assessment. */
export default function AssessmentListPage() {
  const [items, setItems] = useState<AssessmentSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [stage, setStage] = useState<JobStage | 'all'>('all')
  const [q, setQ] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api.listAssessments().then(setItems).catch((e) => setError(e.message))
  }, [])

  /** New project opens an unsaved draft; the record is created on its first Save, so a mis-tap leaves no "Unnamed" row. */
  const create = () => navigate('/assessments/new')

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const a of items ?? []) c[a.stage] = (c[a.stage] ?? 0) + 1
    return c
  }, [items])
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return (items ?? []).filter((a) => (stage === 'all' || a.stage === stage) && (!needle || `${a.customer_name} ${a.address}`.toLowerCase().includes(needle)))
  }, [items, stage, q])

  const facts = (a: AssessmentSummary) => {
    const parts = [a.address || 'No address', plural(a.face_count, 'roof face')]
    if (a.has_results && a.system_kwp != null) {
      parts.push(`${plural(a.panel_count ?? 0, 'panel')} · ${a.system_kwp.toFixed(2)} kWp`)
      if (a.battery_kwh != null && a.battery_kwh > 0) parts.push(`${a.battery_kwh.toFixed(a.battery_kwh % 1 ? 1 : 0)} kWh battery`)
    }
    parts.push(a.computed_at ? `calculated ${fmtDateTime(a.computed_at)}` : 'not calculated yet')
    return parts.join(' · ')
  }

  return (
    <div className="card">
      <div className="row" style={{ alignItems: 'center', marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Projects</h2>
        <div className="narrow inline">
          <button className="primary" onClick={create}>
            New project
          </button>
        </div>
      </div>
      <div className="row" style={{ marginBottom: 10, alignItems: 'center' }}>
        <div className="narrow" style={{ width: 240 }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name or address" aria-label="Search projects" />
        </div>
        <div className="toggles" style={{ flex: '1 1 auto' }}>
          <button type="button" className={`toggle ${stage === 'all' ? 'on' : ''}`} onClick={() => setStage('all')}>
            All {items ? items.length : ''}
          </button>
          {JOB_STAGES.filter((s) => counts[s.id]).map((s) => (
            <button key={s.id} type="button" className={`toggle ${stage === s.id ? 'on' : ''}`} onClick={() => setStage(s.id)}>
              {s.label} {counts[s.id]}
            </button>
          ))}
        </div>
      </div>
      {error && <div className="banner bad">{error}</div>}
      {items === null ? (
        <div className="muted">Loading...</div>
      ) : items.length === 0 ? (
        <div className="muted">No projects yet. Press New project to start one on site, or open Leads and press Start assessment on a website booking.</div>
      ) : shown.length === 0 ? (
        <div className="muted">Nothing matches. Clear the search or pick another stage.</div>
      ) : (
        shown.map((a) => (
          <Link key={a.id} to={`/assessments/${a.id}`} className="list-item">
            <div className="title">
              {a.customer_name || <span className="muted">Unnamed</span>}{' '}
              <span className="badge neutral">{JOB_STAGES.find((s) => s.id === a.stage)?.label ?? a.stage}</span>{' '}
              {a.results_stale && <span className="badge neutral">needs recalculating</span>}
            </div>
            <div className="muted">{facts(a)}</div>
          </Link>
        ))
      )}
    </div>
  )
}
