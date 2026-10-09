import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { api, type Me } from '../api'
import PricingSettings from '../components/PricingSettings'
import { PRICING_GROUPS } from '../components/shared'
import AccountCard from '../components/AccountCard'
import PeopleCard from '../components/PeopleCard'
import Field from '../components/Field'
import { PROFILE_FIELDS, type AppSettings, type DataStatus } from '../types'
import { fmtDateTime } from '../fmt'
import { useNarrow } from '../components/responsive'

// the profile fields, grouped the way the owner reads them: profile, the contact line, the warranties, where to pay, then the website
const WARRANTY_KEYS = ['warranty_workmanship_years', 'warranty_panels_product_years', 'warranty_panels_performance_years', 'warranty_inverter_years', 'warranty_battery_years']
// website only (mirrors backend profile.WEBSITE_KEYS): messenger, facebook, brands, callback_promise, privacy_note
/** A hint that is an example goes in the field as its placeholder; a hint that is an instruction goes under it. Never both. */
const isExample = (hint: string) => /^(e\.g\.|https?:)/i.test(hint)

/** The sections of the page, in reading order; the index on the left (a jump list on the phone) names them. */
const SECTIONS: { id: string; label: string; owner?: boolean; subs?: { id: string; label: string }[] }[] = [
  { id: 'company', label: 'Company and documents' },
  { id: 'website', label: 'Website' },
  { id: 'pricing', label: 'Pricing', subs: PRICING_GROUPS.map((g) => ({ id: g.id, label: g.label })) },
  { id: 'account', label: 'Your account' },
  { id: 'people', label: 'People', owner: true },
  { id: 'weather', label: 'Weather and data' },
]

function Section({ id, title, lead, children, as: Tag = 'section', onSubmit }: { id: string; title: string; lead: ReactNode; children: ReactNode; as?: 'section' | 'form'; onSubmit?: (e: FormEvent) => void }) {
  return (
    <Tag className="card settings-section" id={id} onSubmit={onSubmit} data-testid={`section-${id}`}>
      <h2>{title}</h2>
      <div className="lead">{lead}</div>
      {children}
    </Tag>
  )
}

export default function SettingsPage({ user, onUser, status, onRefresh }: { user: Me; onUser: (me: Me) => void; status: DataStatus | null; onRefresh: () => void }) {
  const owner = user.role === 'owner'
  const narrow = useNarrow()
  const [s, setS] = useState<AppSettings | null>(null)
  const [saved, setSaved] = useState<AppSettings | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [active, setActive] = useState<string>('company')

  useEffect(() => {
    api.settings().then((r) => {
      setS(r)
      setSaved(r)
    })
  }, [])

  // the index follows the scroll: the last section whose top has passed the top of the screen is the current one
  useEffect(() => {
    const ids = SECTIONS.flatMap((x) => [x.id, ...(x.subs ?? []).map((y) => y.id)])
    let raf = 0
    const onScroll = () => {
      if (raf) return
      raf = window.requestAnimationFrame(() => {
        raf = 0
        let current = ids[0]
        for (const id of ids) {
          const el = document.getElementById(id)
          if (el && el.getBoundingClientRect().top <= 120) current = id
        }
        if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) current = 'weather'
        setActive(current)
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (raf) window.cancelAnimationFrame(raf)
    }
  }, [s])

  // a link into the page (/settings#account from the top bar) lands on its section once the cards exist
  useEffect(() => {
    if (!s) return
    const h = window.location.hash.replace('#', '')
    if (h) document.getElementById(h)?.scrollIntoView({ block: 'start' })
  }, [s])

  const dirty = s && saved && JSON.stringify(s) !== JSON.stringify(saved)

  const save = async (e: FormEvent) => {
    e.preventDefault()
    if (!s) return
    setBusy(true)
    try {
      const r = await api.saveSettings(s)
      setS(r)
      setSaved(r)
      setMsg('Saved. The estimate page and the documents use these right away.')
    } catch (err) {
      setMsg((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  /** One profile field: the label from PROFILE_FIELDS, an example as the placeholder or an instruction as help, never both. */
  const field = (key: string, opts: { long?: boolean; className?: string; unit?: string; label?: string; help?: string } = {}) => {
    const def = PROFILE_FIELDS.find((f) => f.key === key)
    if (!s || !def) return null
    const hint = opts.help ?? def.hint
    const placeholder = hint && isExample(hint) ? hint : undefined
    const help = hint && !placeholder ? hint : undefined
    return (
      <Field key={key} label={opts.label ?? def.label} help={help} unit={opts.unit} className={opts.className}>
        {(id) =>
          opts.long ? (
            <textarea id={id} rows={2} value={s[key] ?? ''} onChange={(e) => setS({ ...s, [key]: e.target.value })} disabled={!owner} />
          ) : (
            <input id={id} value={s[key] ?? ''} onChange={(e) => setS({ ...s, [key]: e.target.value })} placeholder={placeholder} disabled={!owner} />
          )
        }
      </Field>
    )
  }
  const yearsLabel = (label: string) => label.replace(/\s*\(years\)$/, '')

  const saveBar = (label: string) =>
    owner && (
      <div className="actions inline">
        <button className="primary" type="submit" disabled={busy || !dirty}>
          {label}
        </button>
        {dirty && <span className="chip unsaved">Unsaved changes</span>}
        {msg && !dirty && <span className="muted">{msg}</span>}
      </div>
    )

  const go = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    window.history.replaceState(null, '', `#${id}`)
  }
  const index = (
    <nav className="settings-index" aria-label="Settings sections">
      <div className="index-title">Settings</div>
      {SECTIONS.filter((x) => !x.owner || owner).map((x) => (
        <span key={x.id} style={{ display: 'contents' }}>
          <a href={`#${x.id}`} className={active === x.id || (x.subs ?? []).some((y) => y.id === active) ? 'on' : ''} onClick={go(x.id)} aria-current={active === x.id ? 'location' : undefined}>
            {x.label}
          </a>
          {owner &&
            !narrow &&
            (x.subs ?? []).map((y) => (
              <a key={y.id} href={`#${y.id}`} className={`sub ${active === y.id ? 'on' : ''}`} onClick={go(y.id)}>
                {y.label}
              </a>
            ))}
        </span>
      ))}
    </nav>
  )

  return (
    <div className="settings">
      {index}
      <div className="settings-main">
        {s ? (
          <form onSubmit={save} data-testid="profile-form">
            <Section
              id="company"
              title="Company and documents"
              lead={
                <>
                  Who you are on the public estimate page, the proposal, the roof check and the card. Blank fields are left off the documents.
                  {!owner && ' Only the owner changes these.'}
                </>
              }
            >
              <h3>Profile</h3>
              <div className="form-grid">
                {field('company_name')}
                {field('owner_name')}
                {field('pee_name')}
                {field('pee_license')}
                {field('address')}
                {field('phone')}
                {field('email')}
                {field('service_area')}
              </div>
              <h3>Contact line on documents</h3>
              <div className="form-grid">{field('company_contact', { className: 'full', label: 'One line under the company name' })}</div>
              <h3>Warranties printed on the proposal</h3>
              <div className="form-grid cols-5">
                {WARRANTY_KEYS.map((k) => {
                  const def = PROFILE_FIELDS.find((f) => f.key === k)
                  return def ? field(k, { label: yearsLabel(def.label), unit: 'years' }) : null
                })}
              </div>
              <h3>Where to pay</h3>
              <div className="form-grid">{field('payment_details', { long: true, className: 'full', label: 'Bank or GCash details' })}</div>
              {saveBar('Save company and documents')}
            </Section>

            <Section
              id="website"
              title="Website"
              lead={
                <>
                  What visitors see on the estimate page and the booking form. A booking is kept for the CRM and can start a project from the Projects page.{' '}
                  <a href="/estimate" target="_blank" rel="noreferrer">
                    Open the estimate page
                  </a>
                  {!owner && '. Only the owner changes these.'}
                </>
              }
            >
              <h3>Estimate page and booking form</h3>
              <div className="form-grid">
                {field('messenger')}
                {field('facebook')}
                {field('callback_promise')}
                {field('brands', { className: 'full' })}
              </div>
              <h3>Privacy line</h3>
              <div className="form-grid">{field('privacy_note', { long: true, className: 'full', label: 'Under the booking form' })}</div>
              {saveBar('Save website text')}
            </Section>
          </form>
        ) : (
          <div className="card settings-section" id="company">
            <h2>Company and documents</h2>
            <div className="muted">Loading…</div>
          </div>
        )}

        <Section
          id="pricing"
          title="Pricing"
          lead={
            owner
              ? 'Every number behind the price build-up, the program of works and the customer savings, in the groups below. Find a setting by name, open its section, edit, then save once at the foot.'
              : "Markups, labor rates, freight and the program-of-works rules are the owner's to change. The BOQ and the proposal use them as set."
          }
        >
          {owner ? <PricingSettings /> : null}
        </Section>

        <AccountCard user={user} onUser={onUser} />
        {owner && <PeopleCard me={user} />}

        <Section id="weather" title="Weather and data" lead="The weather dataset every calculation runs on, downloaded once to the server. The reference dataset is shown beside it for comparison and is not used in results.">
          {status ? (
            <table className="kv weather-table">
              <tbody>
                <tr>
                  <th>PVGIS</th>
                  <td>
                    {status.pvgis.available ? `${status.pvgis.cell_count} cells (${status.pvgis.radiation_db})` : 'not downloaded'}
                    {status.pvgis.synthetic && <span className="badge bad" style={{ marginLeft: 8 }}>TEST DATA</span>}
                  </td>
                </tr>
                <tr>
                  <th>Downloaded</th>
                  <td>{status.pvgis.downloaded_at ? fmtDateTime(status.pvgis.downloaded_at) : '-'}</td>
                </tr>
                <tr>
                  <th>NASA POWER reference</th>
                  <td>{status.nasa.available ? `${status.nasa.point_count} points` : 'not downloaded'}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <div className="muted">Can't reach the server for the weather status.</div>
          )}
          <div className="actions inline">
            <button type="button" onClick={onRefresh}>
              Refresh
            </button>
          </div>
        </Section>
      </div>
    </div>
  )
}
