import { useEffect, useState, type FormEvent } from 'react'
import { api, type Me } from '../api'
import PricingSettings from '../components/PricingSettings'
import AccountCard from '../components/AccountCard'
import PeopleCard from '../components/PeopleCard'
import { PROFILE_FIELDS, type AppSettings, type DataStatus } from '../types'
import { fmtDateTime } from '../fmt'

// who you are: on the estimate page and every document
const CONTACT_KEYS = ['company_name', 'address', 'phone', 'email', 'owner_name', 'pee_name', 'pee_license', 'service_area']
const WARRANTY_KEYS = new Set(['warranty_workmanship_years', 'warranty_panels_product_years', 'warranty_panels_performance_years', 'warranty_inverter_years', 'warranty_battery_years'])
// website only: the booking form, the thank-you page and the trust lines (mirrors backend profile.WEBSITE_KEYS)
const WEBSITE_KEYS = ['messenger', 'facebook', 'brands', 'callback_promise']

export default function SettingsPage({ user, onUser, status, onRefresh }: { user: Me; onUser: (me: Me) => void; status: DataStatus | null; onRefresh: () => void }) {
  const owner = user.role === 'owner'
  const [s, setS] = useState<AppSettings | null>(null)
  const [saved, setSaved] = useState<AppSettings | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.settings().then((r) => {
      setS(r)
      setSaved(r)
    })
  }, [])

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

  const field = (key: string, label: string, hint?: string, long = false) =>
    s && (
      <div className="field" key={key}>
        <label>{label}</label>
        {long ? (
          <textarea rows={2} value={s[key] ?? ''} onChange={(e) => setS({ ...s, [key]: e.target.value })} disabled={!owner} />
        ) : (
          <input value={s[key] ?? ''} onChange={(e) => setS({ ...s, [key]: e.target.value })} placeholder={hint} disabled={!owner} />
        )}
        {hint && !long && <div className="hint">{hint}</div>}
      </div>
    )
  const fields = (keys: string[]) => keys.map((k) => PROFILE_FIELDS.find((f) => f.key === k)).filter((f) => f != null).map((f) => field(f.key, f.label, f.hint))

  return (
    <>
      <form className="card" onSubmit={save}>
        <h2>Company profile</h2>
        <div className="muted" style={{ marginBottom: 10 }}>
          Shown on the public estimate page, the proposal, the roof check and the card. Blank fields are left off.
          {!owner && ' Only the owner changes these.'}
        </div>
        {s && (
          <>
            <h3>Who you are and how to reach you</h3>
            <div className="grid">{fields(CONTACT_KEYS)}</div>
            {field('company_contact', 'Contact line on documents', 'Address, phone, email, as one line under the company name.')}
            <h3>Warranties printed on the proposal</h3>
            <div className="grid">{PROFILE_FIELDS.filter((f) => WARRANTY_KEYS.has(f.key)).map((f) => field(f.key, f.label))}</div>
            <h3>Proposal</h3>
            {field('payment_details', 'Where to pay', 'Bank or GCash details printed in the proposal acceptance block.', true)}
            <h3 id="website">Website</h3>
            <div className="muted" style={{ marginBottom: 8 }}>
              What visitors see on the estimate page and the booking form. Bookings land in Leads.{' '}
              <a href="/estimate" target="_blank" rel="noreferrer">
                Open the estimate page
              </a>
            </div>
            <div className="grid">{fields(WEBSITE_KEYS)}</div>
            {field('privacy_note', 'Privacy line under the booking form', undefined, true)}
            {owner && (
              <div className="actions" style={{ position: 'static', border: 0, padding: '6px 0 0' }}>
                <button className="primary" type="submit" disabled={busy || !dirty}>
                  Save profile
                </button>
                {msg && <span className="muted">{msg}</span>}
                {dirty && !msg && <span className="chip unsaved">Unsaved changes</span>}
              </div>
            )}
          </>
        )}
      </form>
      <AccountCard user={user} onUser={onUser} />
      {owner && <PeopleCard me={user} />}
      {owner ? (
        <div className="card">
          <h2>Pricing settings</h2>
          <PricingSettings />
        </div>
      ) : (
        <div className="card">
          <h2>Pricing settings</h2>
          <div className="muted">Markups, labor rates, freight and the program-of-works rules are the owner's to change. The BOQ and the quotation use them as set.</div>
        </div>
      )}
      <div className="card">
        <h2>Weather dataset</h2>
        {status ? (
          <table>
            <tbody>
              <tr>
                <th>PVGIS</th>
                <td>
                  {status.pvgis.available ? `${status.pvgis.cell_count} cells (${status.pvgis.radiation_db})` : 'not downloaded'}
                  {status.pvgis.synthetic && <span className="badge bad"> TEST DATA</span>}
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
        <div style={{ marginTop: 10 }}>
          <button onClick={onRefresh}>Refresh</button>
        </div>
      </div>
    </>
  )
}
