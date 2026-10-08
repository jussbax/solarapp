import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { emptyDoc, JOB_STAGES, type AssessmentSummary } from '../types'
import { fmtDateTime, php0 } from '../fmt'

export default function AssessmentListPage() {
  const [items, setItems] = useState<AssessmentSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    api.listAssessments().then(setItems).catch((e) => setError(e.message))
  }, [])

  const create = async () => {
    const a = await api.createAssessment(emptyDoc())
    navigate(`/assessments/${a.id}`)
  }

  return (
    <div className="card">
      <div className="row" style={{ alignItems: 'center', marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Assessments</h2>
        <div className="narrow inline">
          <button className="primary" onClick={create}>
            New assessment
          </button>
        </div>
      </div>
      {error && <div className="banner bad">{error}</div>}
      {items === null ? (
        <div className="muted">Loading...</div>
      ) : items.length === 0 ? (
        <div className="muted">No assessments yet. Press New assessment to start one.</div>
      ) : (
        items.map((a) => (
          <Link key={a.id} to={`/assessments/${a.id}`} className="list-item">
            <div className="title">
              {a.customer_name || <span className="muted">Unnamed</span>}{' '}
              <span className="badge neutral">{JOB_STAGES.find((s) => s.id === a.stage)?.label ?? a.stage}</span>{' '}
              {a.results_stale && <span className="badge neutral">needs recalculating</span>}
            </div>
            <div className="muted">
              {a.address || 'No address'} · {fmtDateTime(a.updated_at)}
              {a.has_results && a.system_kwp != null && (
                <>
                  {' '}
                  · {a.panel_count} panels · {a.system_kwp.toFixed(2)} kWp · {Math.round(a.annual_kwh ?? 0).toLocaleString()} kWh/yr
                  {a.contract_php != null && ` · ${php0(a.contract_php)}`}
                </>
              )}
            </div>
          </Link>
        ))
      )}
    </div>
  )
}
