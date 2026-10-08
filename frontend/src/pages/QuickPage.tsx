import { useEffect, useState } from 'react'
import { api } from '../api'
import MapPicker from '../components/MapPicker'
import NumberInput from '../components/NumberInput'
import type { QuickGoal, QuickPattern, QuickResult } from '../types'

const php0 = (v: number | null | undefined) => (v == null ? '-' : `₱${Math.round(v).toLocaleString()}`)
const GOALS: { id: QuickGoal; title: string; text: string }[] = [
  { id: 'net_metering', title: 'Lower my bill', text: 'Grid-tied with net metering. Daytime solar, surplus credited by the utility. No battery.' },
  { id: 'combination', title: 'Lower my bill and keep the lights on', text: 'Net metering with a battery for the evening and brownouts.' },
  { id: 'off_grid', title: 'Independent from the grid', text: 'Off-grid with a battery sized to carry the house. No grid import.' },
]
const PATTERNS: { id: QuickPattern; title: string; text: string }[] = [
  { id: 'morning', title: 'Morning', text: 'Cooking, laundry, pumps and aircon early in the day.' },
  { id: 'balanced', title: 'Spread through the day', text: 'Someone is home most of the day.' },
  { id: 'evening', title: 'Evening', text: 'The house is busiest from dusk: aircon, TV, cooking.' },
]

export default function QuickPage() {
  const [goal, setGoal] = useState<QuickGoal>('combination')
  const [lat, setLat] = useState<number | null>(null)
  const [lon, setLon] = useState<number | null>(null)
  const [kwh, setKwh] = useState<number | null>(null)
  const [php, setPhp] = useState<number | null>(null)
  const [pattern, setPattern] = useState<QuickPattern>('balanced')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<QuickResult | null>(null)
  const [status, setStatus] = useState<{ enabled: boolean; data: boolean } | null>(null)
  const [lead, setLead] = useState({ name: '', contact: '', address: '' })
  const [leadSent, setLeadSent] = useState(false)

  useEffect(() => {
    api.quickStatus().then(setStatus).catch(() => setStatus(null))
  }, [])

  const ready = lat != null && lon != null && ((kwh ?? 0) > 0 || (php ?? 0) > 0)
  const run = async () => {
    if (!ready || lat == null || lon == null) return
    setBusy(true)
    setError(null)
    try {
      const r = await api.quickEstimate({ goal, lat, lon, monthly_kwh: kwh, monthly_php: php, pattern })
      setResult(r)
      setLeadSent(false)
      setTimeout(() => document.getElementById('quick-result')?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  const sendLead = async () => {
    if (!lead.name.trim() || !lead.contact.trim() || lat == null || lon == null) return
    setError(null)
    try {
      await api.quickLead({ goal, lat, lon, monthly_kwh: kwh, monthly_php: php, pattern, ...lead })
      setLeadSent(true)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const sy = result?.system
  const ec = result?.economics
  const pr = result?.production

  return (
    <div>
      <div className="card">
        <h2>Free quick solar estimate</h2>
        <div className="muted" style={{ marginBottom: 12 }}>
          Four questions, one minute. You get the system you need, what it costs and what it saves. For an exact figure we measure your roof on a free visit.
        </div>
        {status && !status.enabled && <div className="banner warn">The quick estimate is not available on this server right now.</div>}

        <div className="step">1. What is your goal?</div>
        <div className="choices" style={{ marginBottom: 14 }}>
          {GOALS.map((g) => (
            <button key={g.id} type="button" className={`choice ${goal === g.id ? 'on' : ''}`} onClick={() => setGoal(g.id)}>
              <b>{g.title}</b>
              <small>{g.text}</small>
            </button>
          ))}
        </div>

        <div className="step">2. Where is the house?</div>
        <div className="muted" style={{ marginBottom: 6 }}>Tap the map on your roof, or use your phone's location.</div>
        <MapPicker lat={lat} lon={lon} onChange={(a, b) => { setLat(a); setLon(b) }} />

        <div className="step" style={{ marginTop: 14 }}>3. What is your monthly electricity use?</div>
        <div className="row">
          <div className="narrow" style={{ width: 200 }}>
            <label>kWh a month (from the bill)</label>
            <NumberInput value={kwh} onChange={setKwh} allowEmpty min={0} placeholder="e.g. 338" />
          </div>
          <div className="narrow" style={{ width: 200 }}>
            <label>or the bill in pesos</label>
            <NumberInput value={php} onChange={setPhp} allowEmpty min={0} placeholder="e.g. 4000" />
          </div>
        </div>

        <div className="step" style={{ marginTop: 14 }}>4. When do you use electricity the most?</div>
        <div className="choices" style={{ marginBottom: 14 }}>
          {PATTERNS.map((p) => (
            <button key={p.id} type="button" className={`choice ${pattern === p.id ? 'on' : ''}`} onClick={() => setPattern(p.id)}>
              <b>{p.title}</b>
              <small>{p.text}</small>
            </button>
          ))}
        </div>
        {error && <div className="banner bad">{error}</div>}
        <button type="button" className="primary" onClick={run} disabled={!ready || busy || (status != null && !status.enabled)}>
          {busy ? 'Working it out...' : 'Show my estimate'}
        </button>
        {!ready && <span className="muted" style={{ marginLeft: 10 }}>Drop the pin and enter your monthly use first.</span>}
      </div>

      {result && sy && pr && (
        <div className="card" id="quick-result">
          <h2>Your estimate</h2>
          {result.warnings.map((w, i) => (
            <div key={i} className="banner warn">
              {w}
            </div>
          ))}
          <div className="hero">
            <div className="hero-grid">
              <div>
                <div className="label">Solar panels</div>
                <div className="big">{sy.panels}</div>
                <div>{sy.kwp.toFixed(2)} kWp, about {Math.round(sy.roof_area_m2)} m² of roof</div>
              </div>
              <div>
                <div className="label">Inverter</div>
                <div className="big">{sy.inverter_units > 1 ? `${sy.inverter_units} x ` : ''}{sy.inverter_kw} kW</div>
                <div>hybrid</div>
              </div>
              {sy.battery_kwh > 0 && (
                <div>
                  <div className="label">Battery</div>
                  <div className="big">{sy.battery_kwh.toFixed(0)} kWh</div>
                  <div>lithium, carries the evening</div>
                </div>
              )}
              <div>
                <div className="label">Estimated price</div>
                <div className="big">{php0(result.price.total)}</div>
                <div>installed, VAT included</div>
              </div>
            </div>
          </div>
          <div className="kpis">
            <div className="kpi">
              <div className="label">Solar production</div>
              <div className="value">{Math.round(pr.annual_kwh / 12).toLocaleString()} kWh/mo</div>
              <div className="sub">covers {Math.round(pr.coverage_pct)}% of your {Math.round(result.inputs.monthly_kwh).toLocaleString()} kWh</div>
            </div>
            {ec && (
              <>
                <div className="kpi">
                  <div className="label">Monthly bill</div>
                  <div className="value">
                    {php0(ec.bill_before_monthly)} → {php0(ec.bill_after_monthly)}
                  </div>
                  <div className="sub">saves about {php0(ec.savings_monthly)} a month</div>
                </div>
                <div className="kpi">
                  <div className="label">Payback</div>
                  <div className="value">{ec.payback_years != null ? `${ec.payback_years.toFixed(1)} years` : `over ${ec.analysis_years} years`}</div>
                  <div className="sub">{php0(ec.savings_year1)} saved in the first year</div>
                </div>
                <div className="kpi">
                  <div className="label">Over {ec.analysis_years} years</div>
                  <div className="value">{php0(ec.lifetime_net)}</div>
                  <div className="sub">net of the system, upkeep and replacements; {ec.co2_t_per_year.toFixed(1)} t CO2 avoided a year</div>
                </div>
              </>
            )}
          </div>
          <div className="muted">
            Price: materials {php0(result.price.materials)}, labor {php0(result.price.labor)}, equipment {php0(result.price.equipment)}, VAT {php0(result.price.tax)}.
          </div>
          <div className="muted" style={{ marginTop: 6 }}>
            {result.assumptions.map((a, i) => (
              <div key={i}>{a}</div>
            ))}
            <div>This is an estimate from your answers, not a quotation. The free roof visit measures your roof and the sun on it and gives you an exact proposal.</div>
          </div>

          <h3>Get the exact figure, free</h3>
          {leadSent ? (
            <div className="banner info">Thank you. We will contact you to arrange the free roof visit.</div>
          ) : (
            <div className="row">
              <div className="narrow" style={{ width: 200 }}>
                <label>Your name</label>
                <input value={lead.name} onChange={(e) => setLead({ ...lead, name: e.target.value })} />
              </div>
              <div className="narrow" style={{ width: 200 }}>
                <label>Mobile or Messenger</label>
                <input value={lead.contact} onChange={(e) => setLead({ ...lead, contact: e.target.value })} />
              </div>
              <div className="narrow" style={{ width: 260 }}>
                <label>Address or landmark (optional)</label>
                <input value={lead.address} onChange={(e) => setLead({ ...lead, address: e.target.value })} />
              </div>
              <div className="narrow inline" style={{ paddingBottom: 4 }}>
                <button type="button" className="primary" onClick={sendLead} disabled={!lead.name.trim() || !lead.contact.trim()}>
                  Book my free roof visit
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
