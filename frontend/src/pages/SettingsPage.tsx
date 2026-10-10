import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, Route, Routes, useBlocker, useLocation, useNavigate } from 'react-router-dom'
import { api, type Me } from '../api'
import { FindSettings, PricingDraftProvider, PricingPage, SectionBody } from '../components/PricingSettings'
import { dirtyEntryIds, settingsIndex, useFindTarget, usePricingDraft, type FindRow } from '../components/pricingMeta'
import { SETTINGS_ENTRIES, WEBSITE_SECTION, settingsEntryFor, type SettingsEntry } from '../components/shared'
import AccountCard from '../components/AccountCard'
import PeopleCard from '../components/PeopleCard'
import Field from '../components/Field'
import { PROFILE_FIELDS, type AppSettings, type DataStatus } from '../types'
import { fmtDateTime } from '../fmt'
import { useNarrow } from '../components/responsive'

// the profile fields, grouped the way the owner reads them: profile, the contact line, the warranties, where to pay, then the website
const WARRANTY_KEYS = ['warranty_workmanship_years', 'warranty_panels_product_years', 'warranty_panels_performance_years', 'warranty_inverter_years', 'warranty_battery_years']
// website only (mirrors backend profile.WEBSITE_KEYS): messenger, facebook, brands, callback_promise, after_sales, privacy_note
const WEBSITE_KEYS = new Set(['messenger', 'facebook', 'brands', 'callback_promise', 'after_sales', 'privacy_note'])
/** A hint that is an example goes in the field as its placeholder; a hint that is an instruction goes under it. Never both. */
const isExample = (hint: string) => /^(e\.g\.|https?:)/i.test(hint)
/** Links from before Settings was a menu (/settings#account, #pricing-labor) land on the page they meant. */
const HASH_ROUTES: Record<string, string> = {
  company: '/settings/company', website: '/settings/website', pricing: '/settings/pricing/materials', 'pricing-materials': '/settings/pricing/materials',
  'pricing-labor': '/settings/pricing/labor', 'pricing-freight': '/settings/pricing/freight', 'pricing-program': '/settings/pricing/program',
  'pricing-economics': '/settings/pricing/savings', 'pricing-system': '/settings/pricing/system', account: '/settings/account', people: '/settings/people', weather: '/settings/data',
}
const entry = (id: string): SettingsEntry => SETTINGS_ENTRIES.find((e) => e.id === id)!
const PROFILE_HELP: Record<string, { help?: string; about?: string; placeholder?: string }> = {
  owner_name: { help: 'Signs the proposal', about: 'Also named in the booking thank-you.' },
  company_contact: { help: 'Address, phone, email, in one line' },
  payment_details: { help: "Printed in the proposal's acceptance block" },
  brands: { help: 'One line', placeholder: 'e.g. Blue Carbon TOPCon panels, Felicity hybrid inverters, LiFePO4 batteries' },
}

/** The settings as a menu of pages: one route each, a left menu on the desk, a list of cards on the phone. The six
 * pricing pages share one draft of the pricing config (PricingDraftProvider), so an owner may edit two pages and save once. */
export default function SettingsPage(props: { user: Me; onUser: (me: Me) => void; status: DataStatus | null; onRefresh: () => void }) {
  return (
    <PricingDraftProvider enabled={props.user.role === 'owner'}>
      <SettingsInner {...props} />
    </PricingDraftProvider>
  )
}

function SettingsInner({ user, onUser, status, onRefresh }: { user: Me; onUser: (me: Me) => void; status: DataStatus | null; onRefresh: () => void }) {
  const owner = user.role === 'owner'
  const narrow = useNarrow()
  const location = useLocation()
  const navigate = useNavigate()
  const draft = usePricingDraft()
  const [s, setS] = useState<AppSettings | null>(null)
  const [saved, setSaved] = useState<AppSettings | null>(null)
  const [needle, setNeedle] = useState('')

  useEffect(() => {
    api.settings().then((r) => {
      setS(r)
      setSaved(r)
    })
  }, [])

  // a link from before the menu (/settings#account) goes to its page
  useEffect(() => {
    const h = location.hash.replace('#', '')
    if (location.pathname === '/settings' && h && HASH_ROUTES[h]) navigate(HASH_ROUTES[h], { replace: true })
  }, [location.pathname, location.hash, navigate])

  const changedKeys = useMemo(() => (s && saved ? Object.keys(s).filter((k) => s[k] !== saved[k]) : []), [s, saved])
  const companyDirty = changedKeys.some((k) => !WEBSITE_KEYS.has(k))
  const websiteDirty = changedKeys.some((k) => WEBSITE_KEYS.has(k)) || draft.dirtySections.includes(WEBSITE_SECTION)
  const anyDirty = changedKeys.length > 0 || draft.dirty

  // leaving Settings (not another settings page) with unsaved edits asks first
  const blocker = useBlocker(({ nextLocation }) => anyDirty && !nextLocation.pathname.startsWith('/settings'))
  useEffect(() => {
    if (blocker.state !== 'blocked') return
    if (window.confirm('Settings have unsaved changes. Leave without saving?')) blocker.proceed()
    else blocker.reset()
  }, [blocker])

  const entries = SETTINGS_ENTRIES.filter((e) => !e.owner || owner)
  const dirtyIds = useMemo(() => {
    const ids = dirtyEntryIds(draft.dirtySections)
    if (companyDirty) ids.add('company')
    if (websiteDirty) ids.add('website')
    return ids
  }, [draft.dirtySections, companyDirty, websiteDirty])
  const current = settingsEntryFor(location.pathname)
  const rows = useMemo(() => settingsIndex(draft.cfg), [draft.cfg])
  const profileRows = useMemo<FindRow[]>(
    () =>
      PROFILE_FIELDS.filter((f) => owner || !WEBSITE_KEYS.has(f.key)).map((f) => {
        const web = WEBSITE_KEYS.has(f.key)
        const block = web ? 'Estimate page and booking form' : WARRANTY_KEYS.includes(f.key) ? 'Warranties' : f.key === 'payment_details' ? 'Where to pay' : 'Profile'
        const e = entry(web ? 'website' : 'company')
        return { id: `profile-${f.key}`, find: `profile.${f.key}`, label: f.label.replace(/\s*\(years\)$/, ''), where: `${e.label} › ${block}`, route: e.route, hay: `${f.label} ${f.key} ${f.hint ?? ''} ${block} ${e.label}`.toLowerCase() }
      }),
    [owner],
  )

  const find = <FindSettings rows={rows} extraRows={profileRows} needle={needle} onNeedle={setNeedle} />
  const pricingEntries = entries.filter((e) => e.sections)
  const plainEntries = entries.filter((e) => !e.sections)
  const row = (e: SettingsEntry) => (
    <Link key={e.id} to={e.route} className={`${current?.id === e.id ? 'on' : ''} ${e.sections ? 'sub' : ''}`} aria-current={current?.id === e.id ? 'page' : undefined} onClick={() => setNeedle('')}>
      <span className="menu-label">{e.label}</span>
      {dirtyIds.has(e.id) && <span className="dot" title="Unsaved changes" aria-label="Unsaved changes" />}
    </Link>
  )
  const menu = (
    <nav className="settings-menu" aria-label="Settings">
      <div className="index-title">Settings</div>
      {find}
      {!needle.trim() && (
        <>
          {plainEntries.slice(0, 2).map(row)}
          {owner && <div className="menu-caption">Pricing</div>}
          {pricingEntries.map(row)}
          {plainEntries.slice(2).map(row)}
        </>
      )}
    </nav>
  )
  const list = (
    <div className="settings-list" data-testid="settings-list">
      <h1 className="settings-title">Settings</h1>
      {find}
      {!needle.trim() &&
        entries.map((e) => (
          <Link key={e.id} to={e.route} className="settings-card">
            <span className="card-text">
              <b>
                {e.label}
                {dirtyIds.has(e.id) && <span className="dot" title="Unsaved changes" aria-label="Unsaved changes" />}
              </b>
              <span className="muted">{e.lead}</span>
            </span>
            <span className="chevron" aria-hidden="true">
              ›
            </span>
          </Link>
        ))}
    </div>
  )
  /** One page: the phone's way back, then the page itself. */
  const page = (e: SettingsEntry, body: ReactNode) => (
    <div className="settings-page" data-page={e.id}>
      {narrow && (
        <Link to="/settings" className="back-link">
          ‹ Settings
        </Link>
      )}
      {body}
    </div>
  )
  const titled = (e: SettingsEntry, body: ReactNode, lead?: ReactNode) => (
    <section className="card settings-section" id={e.id} data-testid={`section-${e.id}`}>
      <h1 className="settings-title">{e.label}</h1>
      <div className="lead">{lead ?? e.lead}</div>
      {body}
    </section>
  )
  const ownerOnly = (e: SettingsEntry, body: ReactNode) => (owner ? page(e, body) : <Navigate to="/settings/company" replace />)

  return (
    <div className={`settings ${narrow ? 'phone' : ''}`}>
      {!narrow && menu}
      <div className="settings-main">
        <Routes>
          <Route index element={narrow ? list : <Navigate to="/settings/company" replace />} />
          <Route path="company" element={page(entry('company'), <ProfilePage which="company" s={s} saved={saved} setS={setS} setSaved={setSaved} owner={owner} titled={titled} />)} />
          <Route path="website" element={ownerOnly(entry('website'), <ProfilePage which="website" s={s} saved={saved} setS={setS} setSaved={setSaved} owner={owner} titled={titled} />)} />
          {pricingEntries.map((e) => (
            <Route key={e.id} path={e.route.replace('/settings/', '')} element={ownerOnly(e, titled(e, <PricingPage entry={e} />))} />
          ))}
          <Route path="account" element={page(entry('account'), <AccountCard user={user} onUser={onUser} />)} />
          <Route path="people" element={ownerOnly(entry('people'), <PeopleCard me={user} />)} />
          <Route
            path="data"
            element={page(
              entry('data'),
              titled(
                entry('data'),
                <>
                  {status ? (
                    <table className="kv weather-table">
                      <tbody>
                        <tr>
                          <th>PVGIS</th>
                          <td>
                            {status.pvgis.available ? `${status.pvgis.cell_count} cells (${status.pvgis.radiation_db})` : 'Not downloaded'}
                            {status.pvgis.synthetic && <span className="badge bad" style={{ marginLeft: 8 }}>TEST DATA</span>}
                          </td>
                        </tr>
                        <tr>
                          <th>Downloaded</th>
                          <td>{status.pvgis.downloaded_at ? fmtDateTime(status.pvgis.downloaded_at) : '-'}</td>
                        </tr>
                        <tr>
                          <th>NASA POWER reference</th>
                          <td>{status.nasa.available ? `${status.nasa.point_count} points` : 'Not downloaded'}</td>
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
                </>,
                'The weather dataset every calculation runs on, downloaded once to the server. The reference dataset is shown beside it for comparison and is not used in results.',
              ),
            )}
          />
          <Route path="*" element={<Navigate to="/settings" replace />} />
        </Routes>
      </div>
    </div>
  )
}

/** The Company page and the Website page: the profile fields in their blocks with one Save at the foot. The Website
 * page also holds the public estimate's assumptions (the pricing config's `quick` section); its Save writes both. */
function ProfilePage({
  which,
  s,
  saved,
  setS,
  setSaved,
  owner,
  titled,
}: {
  which: 'company' | 'website'
  s: AppSettings | null
  saved: AppSettings | null
  setS: (s: AppSettings) => void
  setSaved: (s: AppSettings) => void
  owner: boolean
  titled: (e: SettingsEntry, body: ReactNode, lead?: ReactNode) => ReactNode
}) {
  const e = entry(which)
  const draft = usePricingDraft()
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const rows = useMemo<FindRow[]>(
    () =>
      PROFILE_FIELDS.filter((f) => WEBSITE_KEYS.has(f.key) === (which === 'website')).map((f) => ({ id: `profile-${f.key}`, find: `profile.${f.key}`, label: f.label, where: e.label, route: e.route, hay: `${f.label} ${f.key} ${f.hint ?? ''}`.toLowerCase() })),
    [which, e.label, e.route],
  )
  const quickRows = useMemo(() => (which === 'website' ? settingsIndex(draft.cfg).filter((r) => r.route === e.route) : []), [which, draft.cfg, e.route])
  const allRows = useMemo(() => [...rows, ...quickRows], [rows, quickRows])
  useFindTarget(!!s && (which === 'company' || !!draft.cfg), allRows)

  const changed = s && saved ? Object.keys(s).filter((k) => s[k] !== saved[k]) : []
  const profileDirty = changed.some((k) => WEBSITE_KEYS.has(k) === (which === 'website'))
  const quickDirty = which === 'website' && draft.dirtySections.includes(WEBSITE_SECTION)
  const dirty = profileDirty || quickDirty

  const save = async (ev: FormEvent) => {
    ev.preventDefault()
    if (!s) return
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.saveSettings(s)
      setS(r)
      setSaved(r)
      let ok = true
      if (quickDirty) ok = await draft.save()
      setMsg(ok ? (which === 'website' ? 'Saved. The estimate page uses these right away.' : 'Saved. The documents use these right away.') : null)
    } catch (err) {
      setMsg((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  /** One profile field: the label from PROFILE_FIELDS, an example as the placeholder or an instruction as help, never both. */
  const field = (key: string, opts: { long?: boolean; className?: string; unit?: string; label?: string } = {}) => {
    const def = PROFILE_FIELDS.find((f) => f.key === key)
    if (!s || !def) return null
    const hint = def.hint
    const extra = PROFILE_HELP[key]
    const placeholder = extra?.placeholder ?? (hint && isExample(hint) ? hint : undefined)
    const help = extra?.help ?? (hint && !placeholder ? hint : undefined)
    return (
      <Field key={key} id={`profile-${key}`} label={opts.label ?? def.label} help={help} about={extra?.about} unit={opts.unit} className={opts.className}>
        {(id) =>
          opts.long ? (
            <textarea id={id} rows={2} value={s[key] ?? ''} onChange={(ev) => setS({ ...s, [key]: ev.target.value })} disabled={!owner} />
          ) : (
            <input id={id} value={s[key] ?? ''} onChange={(ev) => setS({ ...s, [key]: ev.target.value })} placeholder={placeholder} disabled={!owner} />
          )
        }
      </Field>
    )
  }
  const yearsLabel = (label: string) => label.replace(/\s*\(years\)$/, '')
  const saveBar = owner && (
    <div className="actions inline" data-testid={`${which}-bar`}>
      <button className="primary" type="submit" disabled={busy || !dirty}>
        Save
      </button>
      {dirty && <span className="chip unsaved">Unsaved changes</span>}
      {msg && !dirty && <span className="muted">{msg}</span>}
    </div>
  )
  if (!s) return titled(e, <div className="muted">Loading…</div>)

  if (which === 'company') {
    return titled(
      e,
      <form onSubmit={save} data-testid="profile-form">
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
        {saveBar}
      </form>,
      <>
        Who you are on the public estimate page, the proposal and the office documents. Blank fields are left off the documents.
        {!owner && ' Only the owner changes these.'}
      </>,
    )
  }
  return titled(
    e,
    <form onSubmit={save} data-testid="website-form">
      <h3>Estimate page and booking form</h3>
      <div className="form-grid">
        {field('messenger')}
        {field('facebook')}
        {field('callback_promise')}
        {field('brands', { className: 'full' })}
        {field('after_sales', { className: 'full' })}
      </div>
      <h3>Privacy line</h3>
      <div className="form-grid">{field('privacy_note', { long: true, className: 'full', label: 'Under the booking form' })}</div>
      <h3>What the estimate assumes</h3>
      {draft.cfg ? <SectionBody sec={WEBSITE_SECTION} /> : <div className="muted">{draft.error ?? 'Loading the estimate settings…'}</div>}
      {saveBar}
    </form>,
    <>
      What visitors see on the estimate page and the booking form, and the typical roof the public estimate assumes. A booking is kept for the CRM and can start a project from the Projects page.{' '}
      <a href="/estimate" target="_blank" rel="noreferrer">
        Open the estimate page
      </a>
    </>,
  )
}
