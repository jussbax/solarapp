import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { emptyDoc, JOB_STAGES, type AssessmentSummary, type Funnel, type JobStage } from '../types'
import { fmtDateTime, php0 } from '../fmt'

const KIND_LABEL: Record<string, string> = { net_metering: 'Net metering', combination: 'Net metering + battery', off_grid: 'Off-grid' }

function contactLinks(contact: string) {
  const digits = contact.replace(/[^\d+]/g, '')
  const isPhone = digits.length >= 10
  return (
    <>
      {isPhone ? (
        <a href={`tel:${digits}`} onClick={(e) => e.stopPropagation()}>
          {contact}
        </a>
      ) : (
        <span>{contact}</span>
      )}
    </>
  )
}

export default function AssessmentListPage() {
  const [items, setItems] = useState<AssessmentSummary[] | null>(null)
  const [funnel, setFunnel] = useState<Funnel | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [stage, setStage] = useState<JobStage | 'all'>('all')
  const [q, setQ] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api.listAssessments().then(setItems).catch((e) => setError(e.message))
    api.funnel(30).then(setFunnel).catch(() => setFunnel(null))
  }, [])

  const create = async () => {
    const a = await api.createAssessment(emptyDoc())
    navigate(`/assessments/${a.id}`)
  }

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const a of items ?? []) c[a.stage] = (c[a.stage] ?? 0) + 1
    return c
  }, [items])
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return (items ?? []).filter((a) => (stage === 'all' || a.stage === stage) && (!needle || `${a.customer_name} ${a.address} ${a.lead_contact ?? ''} ${a.lead_town ?? ''}`.toLowerCase().includes(needle)))
  }, [items, stage, q])

  return (
    <>
      {funnel && (
        <div className="card">
          <h2>Last {funnel.days} days</h2>
          <div className="kpis">
            <div className="kpi">
              <div className="label">Estimates run</div>
              <div className="value">{funnel.estimates}</div>
              <div className="sub">
                {Object.entries(funnel.estimates_by_source)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 3)
                  .map(([k, v]) => `${k} ${v}`)
                  .join(' · ') || 'on the public page'}
              </div>
            </div>
            <div className="kpi">
              <div className="label">Leads</div>
              <div className="value">{funnel.leads}</div>
              <div className="sub">{funnel.estimates ? `${Math.round((100 * funnel.leads) / funnel.estimates)}% of estimates` : 'booked a visit'}</div>
            </div>
            <div className="kpi">
              <div className="label">Visits</div>
              <div className="value">{funnel.visits}</div>
              <div className="sub">assessed on site</div>
            </div>
            <div className="kpi">
              <div className="label">Proposals</div>
              <div className="value">{funnel.proposals}</div>
              <div className="sub">priced and sent</div>
            </div>
            <div className="kpi">
              <div className="label">Signed</div>
              <div className="value">{funnel.signed}</div>
              <div className="sub">{funnel.proposals ? `${Math.round((100 * funnel.signed) / funnel.proposals)}% of proposals` : 'contracts'}</div>
            </div>
          </div>
        </div>
      )}
      <div className="card">
        <div className="row" style={{ alignItems: 'center', marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Assessments</h2>
          <div className="narrow inline">
            <button className="primary" onClick={create}>
              New assessment
            </button>
          </div>
        </div>
        <div className="row" style={{ marginBottom: 10, alignItems: 'center' }}>
          <div className="narrow" style={{ width: 240 }}>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, address, contact" />
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
          <div className="muted">No assessments yet. Press New assessment to start one.</div>
        ) : shown.length === 0 ? (
          <div className="muted">Nothing matches. Clear the search or pick another stage.</div>
        ) : (
          shown.map((a) => (
            <Link key={a.id} to={`/assessments/${a.id}`} className="list-item">
              <div className="title">
                {a.customer_name || <span className="muted">Unnamed</span>}{' '}
                <span className={`badge ${a.stage === 'lead' ? 'gold' : 'neutral'}`}>{JOB_STAGES.find((s) => s.id === a.stage)?.label ?? a.stage}</span>{' '}
                {a.lead_contact && <span className="badge neutral">website lead{a.lead_source ? ` · ${a.lead_source}` : ''}</span>}{' '}
                {a.results_stale && <span className="badge neutral">needs recalculating</span>}
              </div>
              <div className="muted">
                {a.address || a.lead_town || 'No address'} · {fmtDateTime(a.updated_at)}
                {a.kind && ` · ${KIND_LABEL[a.kind] ?? a.kind}`}
                {a.has_results && a.system_kwp != null && (
                  <>
                    {' '}
                    · {a.panel_count} panels · {a.system_kwp.toFixed(2)} kWp · {Math.round(a.annual_kwh ?? 0).toLocaleString()} kWh/yr
                    {a.contract_php != null && ` · ${php0(a.contract_php)}`}
                  </>
                )}
              </div>
              {a.lead_contact && (
                <div className="muted" style={{ marginTop: 2 }}>
                  Contact: {contactLinks(a.lead_contact)}
                  {a.lead_estimate && (
                    <>
                      {' '}
                      · saw {a.lead_estimate.panels} panels, {a.lead_estimate.kwp.toFixed(2)} kWp{a.lead_estimate.battery_kwh > 0 ? `, ${a.lead_estimate.battery_kwh.toFixed(0)} kWh battery` : ''} at {php0(a.lead_estimate.price)}
                      {a.lead_estimate.bill_before_monthly != null && a.lead_estimate.bill_after_monthly != null && ` · bill ${php0(a.lead_estimate.bill_before_monthly)} → ${php0(a.lead_estimate.bill_after_monthly)}`}
                    </>
                  )}
                </div>
              )}
            </Link>
          ))
        )}
      </div>
    </>
  )
}
