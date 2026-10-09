import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { JOB_STAGES, LEAD_STATUSES, type AssessmentSummary, type JobStage, type Lead, type LeadStatus } from '../types'
import { fmtDateTime, php0, plural } from '../fmt'

/** A booking that has not become a project and was not closed by the CRM. */
const OPEN: LeadStatus[] = ['new', 'contacted', 'visit_booked']

/** The project list: one record per site, engineering facts only. Website bookings are the CRM's; the only thing
 *  this page does with one is start a project from it. */
export default function AssessmentListPage() {
  const [items, setItems] = useState<AssessmentSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [stage, setStage] = useState<JobStage | 'all'>('all')
  const [q, setQ] = useState('')
  const [params] = useSearchParams()
  const focusBooking = Number(params.get('booking')) || null // the e-mail notice links here
  const [showBookings, setShowBookings] = useState(focusBooking != null)
  const [bookings, setBookings] = useState<Lead[] | null>(null)
  const [busy, setBusy] = useState<number | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    api.listAssessments().then(setItems).catch((e) => setError(e.message))
  }, [])
  useEffect(() => {
    if (!showBookings) return
    api
      .bookings()
      .then((rows) => setBookings(rows.filter((b) => OPEN.includes(b.status) && !b.anonymised)))
      .catch((e) => setError(e.message))
  }, [showBookings])
  useEffect(() => {
    if (focusBooking != null && bookings) document.getElementById(`booking-${focusBooking}`)?.scrollIntoView({ block: 'center' })
  }, [focusBooking, bookings])

  /** New project opens an unsaved draft; the record is created on its first Save, so a mis-tap leaves no "Unnamed" row. */
  const create = () => navigate('/assessments/new')

  /** Start a project from a booking: the customer, the place or pin and the bill are copied; the booking stays with the website's records. */
  const start = async (b: Lead) => {
    setBusy(b.id)
    try {
      const r = await api.convertLead(b.id)
      navigate(`/assessments/${r.project_id}`)
    } catch (e) {
      setError((e as Error).message)
      setBusy(null)
    }
  }

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
  const saw = (b: Lead) => {
    const e = b.estimate
    if (!e || !e.price) return 'No estimate shown'
    const parts = [`${plural(e.panels, 'panel')} · ${e.kwp.toFixed(1)} kWp`]
    if (e.battery_kwh > 0) parts.push(`${e.battery_kwh} kWh battery`)
    parts.push(`about ${php0(e.price)}`)
    if (e.monthly_kwh) parts.push(`bill ${e.monthly_kwh} kWh/month`)
    return `Saw on the website: ${parts.join(' · ')}`
  }

  return (
    <>
      <div className="card">
        <div className="row" style={{ alignItems: 'center', marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Projects</h2>
          <div className="narrow inline" style={{ display: 'flex', gap: 8 }}>
            <button className="primary" onClick={create}>
              New project
            </button>
            <button type="button" onClick={() => setShowBookings((v) => !v)} aria-expanded={showBookings} aria-controls="bookings" data-testid="from-booking">
              From a website booking
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
          <div className="muted">No projects yet. Press New project to start one on site, or start one from a website booking.</div>
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
      {showBookings && (
        <div className="card" id="bookings">
          <h2>From a website booking</h2>
          <div className="muted" style={{ marginBottom: 8 }}>
            Visitors who booked a free roof visit on the website and have no project yet. Start project copies their name, the place or pin and the
            bill into a new project; the booking itself stays with the website's records.
          </div>
          {bookings === null ? (
            <div className="muted">Loading...</div>
          ) : bookings.length === 0 ? (
            <div className="muted">No open bookings. New ones appear here as they come in from the website.</div>
          ) : (
            bookings.map((b) => (
              <div key={b.id} id={`booking-${b.id}`} className={`list-item ${b.id === focusBooking ? 'focus' : ''}`} data-testid={`booking-${b.id}`}>
                <div className="title">
                  {b.name || <span className="muted">No name</span>}{' '}
                  <span className={`badge ${b.status === 'new' ? 'gold' : 'neutral'}`}>{LEAD_STATUSES.find((s) => s.id === b.status)?.label ?? b.status}</span>
                </div>
                <div className="muted">
                  {[b.place || 'No place', b.contact ? `contact ${b.contact}` : 'no contact', b.preferred_time ? `best time ${b.preferred_time}` : '', `booked ${fmtDateTime(b.created_at)}`]
                    .filter(Boolean)
                    .join(' · ')}
                </div>
                <div className="muted">{saw(b)}</div>
                <div style={{ marginTop: 6 }}>
                  <button type="button" className="primary" disabled={busy === b.id} onClick={() => start(b)}>
                    Start project
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </>
  )
}
