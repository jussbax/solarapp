import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import PricingSettings from '../components/PricingSettings'
import type { AppSettings, DataStatus } from '../types'

export default function SettingsPage({ status, onRefresh }: { status: DataStatus | null; onRefresh: () => void }) {
  const [s, setS] = useState<AppSettings | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    api.settings().then(setS)
  }, [])

  const save = async (e: FormEvent) => {
    e.preventDefault()
    if (!s) return
    const r = await api.saveSettings({ company_name: s.company_name, company_contact: s.company_contact })
    setS(r)
    setMsg('Saved.')
  }

  return (
    <>
      <form className="card" onSubmit={save}>
        <h2>Company (shown on the customer PDF)</h2>
        {s && (
          <>
            <div className="field">
              <label>Company name</label>
              <input value={s.company_name} onChange={(e) => setS({ ...s, company_name: e.target.value })} />
            </div>
            <div className="field">
              <label>Contact line (address, phone, email)</label>
              <input value={s.company_contact} onChange={(e) => setS({ ...s, company_contact: e.target.value })} />
            </div>
            <button className="primary" type="submit">
              Save
            </button>{' '}
            {msg && <span className="muted">{msg}</span>}
          </>
        )}
      </form>
      <div className="card">
        <h2>Pricing settings</h2>
        <PricingSettings />
      </div>
      <div className="card">
        <h2>Weather dataset</h2>
        {status ? (
          <table>
            <tbody>
              <tr>
                <th>PVGIS</th>
                <td>
                  {status.pvgis.available ? `${status.pvgis.cell_count} cells (${status.pvgis.radiation_db})` : 'not downloaded'}
                  {status.pvgis.synthetic && <span className="badge bad"> SYNTHETIC</span>}
                </td>
              </tr>
              <tr>
                <th>Downloaded</th>
                <td>{status.pvgis.downloaded_at ? new Date(status.pvgis.downloaded_at).toLocaleString() : '-'}</td>
              </tr>
              <tr>
                <th>NASA POWER reference</th>
                <td>{status.nasa.available ? `${status.nasa.point_count} points` : 'not downloaded'}</td>
              </tr>
            </tbody>
          </table>
        ) : (
          <div className="muted">Status unavailable.</div>
        )}
        <div style={{ marginTop: 10 }}>
          <button onClick={onRefresh}>Refresh</button>
        </div>
      </div>
    </>
  )
}
