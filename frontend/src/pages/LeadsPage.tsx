import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { LEAD_STATUSES, type Lead, type LeadFunnel, type LeadStatus } from '../types'
import { fmtDateTime, php0, plural } from '../fmt'

/** The leads inbox: website bookings, worked here until Start assessment makes a project. A future CRM module takes this page over. */

const OPEN: LeadStatus[] = ['new', 'contacted', 'visit_booked']
type Filter = LeadStatus | 'open' | 'all'

/** Tap to call a number, mail an address, or message a Messenger handle. */
function contactLink(contact: string): ReactNode {
  const digits = contact.replace(/[^\d+]/g, '')
  if (digits.length >= 10) return <a href={`tel:${digits}`}>{contact}</a>
  if (contact.includes('@')) return <a href={`mailto:${contact}`}>{contact}</a>
  if (/^[A-Za-z0-9._-]{3,}$/.test(contact))
    return (
      <a href={`https://m.me/${contact}`} target="_blank" rel="noreferrer">
        {contact} (Messenger)
      </a>
    )
  return <span>{contact}</span>
}

const pct = (part: number, whole: number) => (whole ? `${Math.round((100 * part) / whole)}%` : null)

function sawLine(e: Lead['estimate']): string | null {
  if (!e.panels) return null
  const parts = [plural(e.panels, 'panel'), `${e.kwp.toFixed(2)} kWp`]
  if (e.battery_kwh >= 0.5) parts.push(`${e.battery_kwh.toFixed(0)} kWh battery`)
  parts.push(php0(e.price))
  if (e.bill_before_monthly != null && e.bill_after_monthly != null) parts.push(`bill ${php0(e.bill_before_monthly)} → about ${php0(e.bill_after_monthly)}`)
  return parts.join(', ')
}

const GOAL: Record<string, string> = { net_metering: 'a lower bill, no battery', combination: 'a lower bill and backup in brownouts', off_grid: 'to go off the grid' }
const PATTERN: Record<string, string> = { morning: 'mostly in the morning', balanced: 'spread through the day', evening: 'mostly in the evening' }

export default function LeadsPage() {
  const { id } = useParams()
  const focusId = id ? Number(id) : null
  const [items, setItems] = useState<Lead[] | null>(null)
  const [funnel, setFunnel] = useState<LeadFunnel | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<Filter>(focusId != null ? 'all' : 'open')
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState<number | null>(null)
  const [closing, setClosing] = useState<{ id: number; reason: string } | null>(null)
  const [drafts, setDrafts] = useState<Record<number, string>>({})
  const navigate = useNavigate()

  const refreshFunnel = useCallback(() => {
    api.leadFunnel(30).then(setFunnel).catch(() => setFunnel(null))
  }, [])

  useEffect(() => {
    api.listLeads().then(setItems).catch((e) => setError(e.message))
    refreshFunnel()
  }, [refreshFunnel])

  // opened from the lead email (/leads/123): scroll to that row
  useEffect(() => {
    if (focusId != null && items) document.getElementById(`lead-${focusId}`)?.scrollIntoView({ block: 'center' })
  }, [focusId, items])

  const replace = (lead: Lead) => setItems((xs) => (xs ? xs.map((x) => (x.id === lead.id ? lead : x)) : xs))

  const patch = async (lead: Lead, body: { status?: LeadStatus; notes?: string; closed_reason?: string }) => {
    setBusy(lead.id)
    try {
      replace(await api.updateLead(lead.id, body))
      setError(null)
      if (body.status) refreshFunnel()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  const saveNotes = (lead: Lead) => {
    const text = drafts[lead.id]
    if (text === undefined || text === lead.notes) return
    patch(lead, { notes: text })
  }

  const convert = async (lead: Lead) => {
    setBusy(lead.id)
    try {
      const r = await api.convertLead(lead.id)
      navigate(`/assessments/${r.project_id}`)
    } catch (e) {
      setError((e as Error).message)
      setBusy(null)
    }
  }

  const remove = async (lead: Lead) => {
    if (!window.confirm(`Delete the lead from ${lead.name || 'this visitor'}? This cannot be undone.`)) return
    setBusy(lead.id)
    try {
      await api.deleteLead(lead.id)
      setItems((xs) => (xs ? xs.filter((x) => x.id !== lead.id) : xs))
      refreshFunnel()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  const counts = useMemo(() => {
    const c: Record<string, number> = { open: 0, all: items?.length ?? 0 }
    for (const l of items ?? []) {
      c[l.status] = (c[l.status] ?? 0) + 1
      if (OPEN.includes(l.status)) c.open += 1
    }
    return c
  }, [items])
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return (items ?? []).filter(
      (l) =>
        (filter === 'all' || (filter === 'open' ? OPEN.includes(l.status) : l.status === filter)) &&
        (!needle || `${l.name} ${l.contact} ${l.place} ${l.address} ${l.notes}`.toLowerCase().includes(needle)),
    )
  }, [items, filter, q])

  const chip = (key: Filter, label: string) =>
    (key === 'all' || key === 'open' || counts[key]) ? (
      <button key={key} type="button" className={`toggle ${filter === key ? 'on' : ''}`} onClick={() => setFilter(key)}>
        {label} {counts[key] ?? 0}
      </button>
    ) : null

  return (
    <>
      <div className="card">
        <h2>Last {funnel?.days ?? 30} days</h2>
        {funnel ? (
          <>
            <div className="kpis">
              <div className="kpi">
                <div className="label">Estimates run</div>
                <div className="value">{funnel.estimates}</div>
                <div className="sub">
                  {Object.entries(funnel.estimates_by_source)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 3)
                    .map(([k, v]) => `${k} ${v}`)
                    .join(' · ') || 'on the website'}
                </div>
              </div>
              <div className="kpi">
                <div className="label">Leads</div>
                <div className="value">{funnel.leads}</div>
                <div className="sub">{pct(funnel.leads, funnel.estimates) ? `${pct(funnel.leads, funnel.estimates)} of estimates` : 'booked a visit'}</div>
              </div>
              <div className="kpi">
                <div className="label">Visits booked</div>
                <div className="value">{funnel.visits_booked}</div>
                <div className="sub">{pct(funnel.visits_booked, funnel.leads) ? `${pct(funnel.visits_booked, funnel.leads)} of leads` : 'date agreed'}</div>
              </div>
              <div className="kpi">
                <div className="label">Converted</div>
                <div className="value">{funnel.converted}</div>
                <div className="sub">{pct(funnel.converted, funnel.leads) ? `${pct(funnel.converted, funnel.leads)} of leads` : 'became projects'}</div>
              </div>
            </div>
            <div className="muted">
              Projects started in the same {funnel.days} days: {funnel.quoted} quoted, {funnel.signed} signed.
            </div>
          </>
        ) : (
          <div className="muted">Can't reach the server for the counts.</div>
        )}
      </div>
      <div className="card">
        <div className="row" style={{ alignItems: 'center', marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Leads</h2>
        </div>
        <div className="row" style={{ marginBottom: 10, alignItems: 'center' }}>
          <div className="narrow" style={{ width: 260 }}>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, contact, town, notes" aria-label="Search leads" />
          </div>
          <div className="toggles" style={{ flex: '1 1 auto' }}>
            {chip('open', 'Open')}
            {LEAD_STATUSES.map((s) => chip(s.id, s.label))}
            {chip('all', 'All')}
          </div>
        </div>
        {error && <div className="banner bad">{error}</div>}
        {items === null ? (
          <div className="muted">Loading...</div>
        ) : items.length === 0 ? (
          <div className="muted">
            No leads yet. When someone books a free roof visit on the website, they show up here with their number and what they saw. The estimate page link is under
            Settings › Website.
          </div>
        ) : shown.length === 0 ? (
          <div className="muted">Nothing matches. Clear the search or pick another status.</div>
        ) : (
          shown.map((l) => {
            const saw = sawLine(l.estimate)
            const e = l.estimate
            return (
              <div key={l.id} id={`lead-${l.id}`} className={`lead-row ${focusId === l.id ? 'focus' : ''}`}>
                <div className="lead-main">
                  <div className="title">
                    {l.anonymised ? <span className="muted">Anonymised lead</span> : l.name || <span className="muted">No name</span>}{' '}
                    <span className={`badge ${l.status === 'new' ? 'gold' : 'neutral'}`}>{LEAD_STATUSES.find((s) => s.id === l.status)?.label ?? l.status}</span>{' '}
                    {l.project_id != null && (
                      <Link to={`/assessments/${l.project_id}`} className="badge good">
                        Project #{l.project_id}
                      </Link>
                    )}
                  </div>
                  <div className="lead-facts">
                    {l.contact && (
                      <div>
                        Contact: {contactLink(l.contact)}
                        {l.preferred_time && ` · best time ${l.preferred_time.toLowerCase()}`}
                      </div>
                    )}
                    {(l.address || l.place) && <div>{[...new Set([l.address, l.place].filter(Boolean))].join(' · ')}</div>}
                    {(e.goal || e.monthly_kwh) && (
                      <div>
                        {e.goal && GOAL[e.goal] ? `Wants ${GOAL[e.goal]}` : ''}
                        {e.monthly_kwh ? `${e.goal && GOAL[e.goal] ? ' · ' : ''}about ${Math.round(e.monthly_kwh).toLocaleString()} kWh a month${e.monthly_php ? ` (${php0(e.monthly_php)})` : ''}` : ''}
                        {e.pattern && PATTERN[e.pattern] ? ` · uses power ${PATTERN[e.pattern]}` : ''}
                      </div>
                    )}
                    {saw && <div>Saw: {saw}</div>}
                    <div>
                      Source: {l.source_label} · {fmtDateTime(l.created_at)}
                      {l.status === 'closed' && l.closed_reason && ` · closed: ${l.closed_reason}`}
                    </div>
                  </div>
                  <textarea
                    rows={2}
                    value={drafts[l.id] ?? l.notes}
                    onChange={(ev) => setDrafts({ ...drafts, [l.id]: ev.target.value })}
                    onBlur={() => saveNotes(l)}
                    placeholder="Notes: what was said, when to call back"
                    aria-label={`Notes for ${l.name || 'lead'}`}
                  />
                </div>
                <div className="lead-side">
                  <label htmlFor={`lead-status-${l.id}`}>Status</label>
                  <select
                    id={`lead-status-${l.id}`}
                    value={l.status}
                    disabled={busy === l.id}
                    onChange={(ev) => {
                      const s = ev.target.value as LeadStatus
                      if (s === 'closed') setClosing({ id: l.id, reason: l.closed_reason })
                      else patch(l, { status: s })
                    }}
                  >
                    {LEAD_STATUSES.map((s) => (
                      <option key={s.id} value={s.id} disabled={s.id === 'converted' && l.project_id == null}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                  <div className="lead-actions">
                    {l.project_id != null ? (
                      <Link to={`/assessments/${l.project_id}`}>
                        <button type="button">Open project</button>
                      </Link>
                    ) : (
                      !l.anonymised && (
                        <button type="button" className="primary" onClick={() => convert(l)} disabled={busy === l.id}>
                          Start assessment
                        </button>
                      )
                    )}
                    {l.status !== 'closed' && l.project_id == null && (
                      <button type="button" onClick={() => setClosing({ id: l.id, reason: '' })} disabled={busy === l.id}>
                        Close
                      </button>
                    )}
                    <button type="button" className="danger" onClick={() => remove(l)} disabled={busy === l.id}>
                      Delete
                    </button>
                  </div>
                  {closing?.id === l.id && (
                    <div className="lead-close">
                      <input
                        autoFocus
                        value={closing.reason}
                        onChange={(ev) => setClosing({ id: l.id, reason: ev.target.value })}
                        placeholder="Why? e.g. renting, out of area, no reply"
                        aria-label="Reason for closing"
                      />
                      <button
                        type="button"
                        className="primary"
                        onClick={() => {
                          patch(l, { status: 'closed', closed_reason: closing.reason.trim() })
                          setClosing(null)
                        }}
                      >
                        Close lead
                      </button>
                      <button type="button" onClick={() => setClosing(null)}>
                        Keep
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </>
  )
}
