import { useEffect, useMemo, useRef, useState } from 'react'
import { emit, isUnavailable, makeApi, readSource } from './api'
import type { EstimateResult, EstimateStatus, Goal, Pattern, Town, Variant } from './types'

const php0 = (v: number | null | undefined) => (v == null || !Number.isFinite(v) ? '-' : `${v < 0 ? '-' : ''}₱${Math.abs(Math.round(v)).toLocaleString()}`)
const n0 = (v: number) => Math.round(v).toLocaleString()
const years = (v: number | null | undefined, horizon: number) => (v == null ? `more than ${horizon} years` : v < 1 ? 'under a year' : `${v.toFixed(1)} years`)

const GOALS: { id: Goal; title: string; text: string }[] = [
  { id: 'net_metering', title: 'A lower bill', text: 'Solar runs the house by day. Extra power goes to your electric company as credit on your bill (net metering). No battery, so no power during a brownout.' },
  { id: 'combination', title: 'A lower bill, and lights in a brownout', text: 'Solar by day, battery at night and during brownouts. Extra power still earns credit on your bill.' },
  { id: 'off_grid', title: 'Battery first, nothing sold back', text: 'The panels and a bigger battery carry the house day and night. The grid only steps in when both fall short, and no power is exported.' },
]
const PATTERNS: { id: Pattern; title: string; text: string }[] = [
  { id: 'morning', title: 'Mostly morning', text: 'Cooking, laundry, the pump and aircon early in the day.' },
  { id: 'balanced', title: 'All day', text: 'Someone is home most of the day.' },
  { id: 'evening', title: 'Mostly evening', text: 'The house is busiest after dark: aircon, TV, cooking.' },
]
const TIMES = ['Morning', 'Afternoon', 'Evening']

/** The battery the price includes (the catalogue unit); anything under half a kWh is no battery at all. */
const hasBattery = (v: Variant) => v.system.battery_kwh >= 0.5

function systemLine(v: Variant) {
  const s = v.system
  const parts = [`${s.panels} × ${Math.round(s.panel_wp)} W ${s.panels === 1 ? 'panel' : 'panels'} (${s.kwp.toFixed(2)} kWp)`, `${s.inverter_units > 1 ? `${s.inverter_units} × ` : ''}${s.inverter_kw} kW hybrid inverter`]
  if (hasBattery(v)) parts.push(`${s.battery_kwh.toFixed(0)} kWh lithium battery`)
  return parts.join(', ')
}

/** "https://m.me/pldev" -> "m.me/pldev", for text that gets copied and forwarded. */
const bareUrl = (u: string) => u.replace(/^https?:\/\//, '').replace(/\/$/, '')

// embedded: the company website already has a header and a footer around the widget, so the widget
// shows neither and keeps the trust lines inside the booking card. Standalone (/estimate on the app host) keeps both.
export default function Estimate({ apiBase = '', embedded = false }: { apiBase?: string; embedded?: boolean }) {
  const source = useMemo(() => readSource(), [])
  const api = useMemo(() => makeApi(apiBase, source), [apiBase, source])
  const [status, setStatus] = useState<EstimateStatus | null | 'down'>(null)
  const [goal, setGoal] = useState<Goal>('combination')
  const [province, setProvince] = useState('')
  const [townName, setTownName] = useState('')
  const [pin, setPin] = useState<{ lat: number; lon: number } | null>(null)
  const [geoBusy, setGeoBusy] = useState(false)
  const [kwh, setKwh] = useState('')
  const [php, setPhp] = useState('')
  const [pattern, setPattern] = useState<Pattern>('balanced')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<EstimateResult | null>(null)
  const [withBattery, setWithBattery] = useState<boolean | null>(null)
  const [lead, setLead] = useState({ name: '', contact: '', address: '', preferred_time: '', website: '' })
  const [leadBusy, setLeadBusy] = useState(false)
  const [leadError, setLeadError] = useState<string | null>(null)
  const [leadSent, setLeadSent] = useState(false)
  const [copied, setCopied] = useState(false)
  const [bookInView, setBookInView] = useState(false)
  const resultRef = useRef<HTMLDivElement>(null)
  const bookRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.status().then(setStatus).catch(() => setStatus('down'))
  }, [api])

  const profile = status && status !== 'down' ? status.profile : null
  const messengerHref = profile?.messenger ? profile.messenger : ''
  // "message us on Facebook" only when there is somewhere to message; otherwise just ask for patience
  const contactHref = messengerHref || profile?.facebook || ''
  const downNote = contactHref ? (
    <>
      The estimate is taking a break. <a href={contactHref} target="_blank" rel="noreferrer">Message us on Facebook</a> and we'll work it out for you.
    </>
  ) : (
    'The estimate is taking a break. Please try again later.'
  )
  const unavailableText = contactHref ? "The estimate isn't available right now. Please try again later or message us on Facebook." : "The estimate isn't available right now. Please try again later."
  const showError = (e: unknown) => setError(isUnavailable(e) ? unavailableText : (e as Error).message)
  const towns: Town[] = status && status !== 'down' ? status.towns : []
  const provinces = useMemo(() => Array.from(new Set(towns.map((t) => t.province))), [towns])
  const townsHere = useMemo(() => towns.filter((t) => t.province === province).sort((a, b) => a.name.localeCompare(b.name)), [towns, province])
  const kwhNum = parseFloat(kwh.replace(/,/g, ''))
  const phpNum = parseFloat(php.replace(/,/g, ''))
  const hasUse = (Number.isFinite(kwhNum) && kwhNum > 0) || (Number.isFinite(phpNum) && phpNum > 0)
  const hasPlace = !!townName || !!pin
  const ready = hasUse && hasPlace
  const enabled = status !== 'down' && (status?.enabled ?? true)

  const useGps = () => {
    setGeoBusy(true)
    setError(null)
    if (!navigator.geolocation) {
      setGeoBusy(false)
      setError("Your phone didn't share its location. Pick your town instead.")
      return
    }
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setPin({ lat: +p.coords.latitude.toFixed(5), lon: +p.coords.longitude.toFixed(5) })
        setTownName('')
        setGeoBusy(false)
      },
      () => {
        setGeoBusy(false)
        setError("Your phone didn't share its location. Pick your town instead.")
      },
      { enableHighAccuracy: true, timeout: 15000 },
    )
  }

  const request = () => ({
    goal,
    town: townName,
    province: townName ? province : '',
    lat: townName ? null : pin?.lat ?? null,
    lon: townName ? null : pin?.lon ?? null,
    monthly_kwh: Number.isFinite(kwhNum) && kwhNum > 0 ? kwhNum : null,
    monthly_php: Number.isFinite(phpNum) && phpNum > 0 ? phpNum : null,
    pattern,
  })

  const run = async () => {
    if (!ready) return
    setBusy(true)
    setError(null)
    try {
      const r = await api.estimate(request())
      setResult(r)
      setWithBattery(hasBattery(r))
      // a visit already booked stays booked: the thank-you keeps its place under a second or third estimate
      emit('estimate_shown', { goal: r.goal, panels: r.system.panels, price: r.price.total })
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
    } catch (e) {
      showError(e)
    } finally {
      setBusy(false)
    }
  }

  // the variant on screen: the one asked for, or the battery alternative the visitor toggled to
  const shown: Variant | null = useMemo(() => {
    if (!result) return null
    if (withBattery == null || result.alternative == null) return result
    return withBattery === hasBattery(result) ? result : result.alternative
  }, [result, withBattery])
  const other: Variant | null = result && shown ? (shown === result ? result.alternative : result) : null
  const stickyShown = !!(result && shown && !leadSent && !bookInView)

  // the sticky price bar steps aside while the booking form (with its own button) is on screen:
  // from the point where a good part of the form is visible, not from its first pixel
  useEffect(() => {
    const el = bookRef.current
    if (!el || !result || typeof IntersectionObserver === 'undefined') return
    const io = new IntersectionObserver((entries) => setBookInView(entries.some((x) => x.isIntersecting)), { threshold: 0.4 })
    io.observe(el)
    return () => io.disconnect()
  }, [result])
  // room under the page while the bar is up, so it never covers the host page's footer
  useEffect(() => {
    document.body.classList.toggle('pld-sticky-on', stickyShown)
    return () => document.body.classList.remove('pld-sticky-on')
  }, [stickyShown])

  const sendLead = async () => {
    if (!result || !shown || !lead.name.trim() || !lead.contact.trim()) return
    setLeadBusy(true)
    setLeadError(null)
    try {
      await api.lead({
        ...request(),
        goal: shown.goal,
        name: lead.name.trim(),
        contact: lead.contact.trim(),
        address: lead.address.trim(),
        preferred_time: lead.preferred_time,
        consent: true,
        website: lead.website,
        source,
        estimate: {
          goal: shown.goal,
          panels: shown.system.panels,
          kwp: shown.system.kwp,
          battery_kwh: shown.system.battery_kwh,
          price: shown.price.total,
          bill_before_monthly: shown.economics?.bill_before_monthly ?? null,
          bill_after_monthly: shown.economics?.bill_after_monthly ?? null,
          payback_years: shown.economics?.payback_years ?? null,
        },
      })
      setLeadSent(true)
      emit('lead_submitted', { goal: shown.goal, price: shown.price.total })
    } catch (e) {
      setLeadError(isUnavailable(e) ? unavailableText : (e as Error).message)
    } finally {
      setLeadBusy(false)
    }
  }

  // where a forwarded summary sends the reader: the website's estimate page and the Messenger handle, when set
  const estimateUrl = status && status !== 'down' ? status.estimate_url || '' : ''
  const summaryText = () => {
    if (!shown || !result) return ''
    const e = shown.economics
    const links = [messengerHref ? `Questions: ${bareUrl(messengerHref)}` : '', estimateUrl ? `Run your own: ${bareUrl(estimateUrl)}` : ''].filter(Boolean).join(' · ')
    return [
      `Solar estimate from ${profile?.company_name || 'PL Development Inc.'} for ${result.inputs.place}:`,
      systemLine(shown) + '.',
      `Estimated price ${php0(shown.price.total)} installed, VAT included.`,
      e ? `Bill ${php0(e.bill_before_monthly)} → about ${php0(e.bill_after_monthly)} a month; pays for itself in ${years(e.payback_years, e.analysis_years)}.` : '',
      'This is an estimate, not a quotation.',
      links,
    ]
      .filter(Boolean)
      .join('\n')
  }
  const copySummary = async () => {
    try {
      await navigator.clipboard.writeText(summaryText())
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      window.prompt('Copy your estimate:', summaryText())
    }
  }

  const telHref = profile?.phone ? `tel:${profile.phone.replace(/[^+\d]/g, '')}` : ''
  const trust = profile
    ? [
        profile.company_name && profile.address ? `${profile.company_name}, ${profile.address}` : profile.company_name,
        profile.service_area ? `Installs in ${profile.service_area}` : '',
        profile.pee_name || profile.pee_license ? 'Electrical plans signed and sealed by a Professional Electrical Engineer' : '',
        profile.brands,
      ].filter(Boolean)
    : []

  const e = shown?.economics
  const prod = shown?.production
  const makesPct = prod ? Math.round(prod.production_vs_use_pct) : 0

  return (
    <div className={`pld${embedded ? ' pld-embedded' : ''}`}>
      {!embedded && (
        <header className="pld-head">
          <img src={`${apiBase}/brand/logo-mark.png`} alt="" className="pld-logo" />
          <div>
            <div className="pld-company">{profile?.company_name || 'PL Development Inc.'}</div>
            {profile?.service_area && <div className="pld-sub">Solar engineering for homes in {profile.service_area}</div>}
          </div>
        </header>
      )}

      <section className="pld-card">
        <h1 className="pld-h1">How much solar does your house need?</h1>
        <p className="pld-lead">
          Four questions, about a minute. You'll see the system size, the price and what it saves each month. For an exact figure, we measure your roof. The visit is free.
        </p>
        {(status === 'down' || (status && !status.enabled)) && <div className="pld-note pld-warn">{downNote}</div>}

        <div className="pld-step">1. What do you want from solar?</div>
        <div className="pld-choices">
          {GOALS.map((g) => (
            <button key={g.id} type="button" className={`pld-choice ${goal === g.id ? 'on' : ''}`} onClick={() => setGoal(g.id)} aria-pressed={goal === g.id}>
              <b>{g.title}</b>
              <small>{g.text}</small>
            </button>
          ))}
        </div>

        <div className="pld-step">2. Where is your house?</div>
        <div className="pld-row">
          <label className="pld-field">
            <span>Province</span>
            <select
              value={province}
              onChange={(ev) => {
                setProvince(ev.target.value)
                setTownName('')
              }}
            >
              <option value="">Choose</option>
              {provinces.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label className="pld-field">
            <span>Town or city</span>
            <select
              value={townName}
              disabled={!province}
              onChange={(ev) => {
                setTownName(ev.target.value)
                if (ev.target.value) setPin(null)
              }}
            >
              <option value="">{province ? 'Choose' : 'Pick a province first'}</option>
              {townsHere.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <div className="pld-field pld-field-btn">
            <span>Or</span>
            <button type="button" className="pld-btn" onClick={useGps} disabled={geoBusy}>
              {geoBusy ? 'Finding you…' : "Use my phone's location"}
            </button>
          </div>
        </div>
        {pin && !townName && <div className="pld-hint">Location set from your phone. Pick a town instead if that's not where the house is.</div>}
        {!pin && !townName && <div className="pld-hint">Not in the list? Use your phone's location at the house, or message us.</div>}

        <div className="pld-step">3. How much electricity do you use in a month?</div>
        <div className="pld-row">
          <label className="pld-field">
            <span>kWh on your latest bill</span>
            <input inputMode="decimal" value={kwh} onChange={(ev) => setKwh(ev.target.value)} placeholder="e.g. 338" />
          </label>
          <label className="pld-field">
            <span>or the amount you paid (₱)</span>
            <input inputMode="decimal" value={php} onChange={(ev) => setPhp(ev.target.value)} placeholder="e.g. 4,000" />
          </label>
        </div>
        <div className="pld-hint">The kWh is printed on the bill, usually near "consumption". Either one is fine.</div>

        <div className="pld-step">4. When does your house use the most power?</div>
        <div className="pld-choices">
          {PATTERNS.map((p) => (
            <button key={p.id} type="button" className={`pld-choice ${pattern === p.id ? 'on' : ''}`} onClick={() => setPattern(p.id)} aria-pressed={pattern === p.id}>
              <b>{p.title}</b>
              <small>{p.text}</small>
            </button>
          ))}
        </div>

        {error && <div className="pld-note pld-bad">{error}</div>}
        <button type="button" className="pld-btn pld-primary pld-wide" onClick={run} disabled={!ready || busy || !enabled}>
          {busy ? 'Working it out…' : 'Show my estimate'}
        </button>
        {!ready && <div className="pld-hint pld-center">{!hasPlace ? 'Pick your town and enter your monthly use first.' : 'Enter your monthly use first.'}</div>}
      </section>

      {result && shown && prod && (
        <section className="pld-card" id="pld-result" ref={resultRef}>
          <h2 className="pld-h2">Your estimate</h2>
          {result.warnings.map((w, i) => (
            <div key={i} className="pld-note pld-warn">
              {w}
            </div>
          ))}
          <div className="pld-hero">
            {e ? (
              <>
                <div className="pld-hero-row">
                  <div className="pld-hero-label">Your monthly bill</div>
                  <div className="pld-hero-big">
                    {php0(e.bill_before_monthly)} <span className="pld-arrow">→</span> about {php0(e.bill_after_monthly)}
                  </div>
                  <div className="pld-hero-sub">about {php0(e.savings_monthly)} less each month, before any fixed charges on your bill</div>
                </div>
                <div className="pld-hero-grid">
                  <div>
                    <div className="pld-hero-label">Pays for itself in</div>
                    <div className="pld-hero-mid">{years(e.payback_years, e.analysis_years)}</div>
                    <div className="pld-hero-sub">{php0(e.savings_year1)} saved in the first year</div>
                  </div>
                  <div>
                    <div className="pld-hero-label">Estimated price</div>
                    <div className="pld-hero-mid pld-gold">{php0(shown.price.total)}</div>
                    <div className="pld-hero-sub">installed, with permits, VAT included</div>
                  </div>
                </div>
              </>
            ) : (
              <div className="pld-hero-row">
                <div className="pld-hero-label">Estimated price</div>
                <div className="pld-hero-big pld-gold">{php0(shown.price.total)}</div>
                <div className="pld-hero-sub">installed, with permits, VAT included</div>
              </div>
            )}
          </div>

          <div className="pld-line">
            <b>The system:</b> {systemLine(shown)}. Needs about {Math.round(shown.system.roof_area_m2)} m² of roof.
          </div>
          <div className="pld-line">
            <b>What it makes:</b> about {n0(prod.annual_kwh / 12)} kWh a month, {makesPct}% of the {n0(result.inputs.monthly_kwh)} kWh you use.
            {makesPct > 100 && shown.goal !== 'off_grid' && " Daytime power is used directly; the surplus is credited by your electric company at its generation rate, which is why the bill does not reach zero."}
            {shown.goal === 'off_grid' && ' Sized so the panels and the battery carry a typical day; surplus beyond the battery earns nothing, because nothing is sold back.'}
            {shown.goal === 'off_grid' && prod.annual_import_kwh > 50 && ` The grid would still supply about ${n0(prod.annual_import_kwh)} kWh a year, mostly in the rainy months.`}
          </div>
          {other && (
            <div className="pld-line pld-alt">
              {hasBattery(shown) ? (
                <>
                  <b>Without the battery:</b> {php0(other.price.total)}
                  {other.economics && `, bill about ${php0(other.economics.bill_after_monthly)} a month, pays for itself in ${years(other.economics.payback_years, other.economics.analysis_years)}`}.
                  {' '}The battery is for brownouts; it adds little to the savings.{' '}
                  <button type="button" className="pld-link" onClick={() => setWithBattery(false)}>
                    Show without the battery
                  </button>
                </>
              ) : (
                <>
                  <b>Add a battery ({other.system.battery_kwh.toFixed(0)} kWh) for brownouts:</b> about {php0(other.price.total - shown.price.total)} more
                  {other.economics && `, bill about ${php0(other.economics.bill_after_monthly)} a month, pays for itself in ${years(other.economics.payback_years, other.economics.analysis_years)}`}.{' '}
                  <button type="button" className="pld-link" onClick={() => setWithBattery(true)}>
                    Show with the battery
                  </button>
                </>
              )}
            </div>
          )}

          <div className="pld-book" id="pld-book" ref={bookRef}>
            <h3 className="pld-h3">Want the exact figure? The roof visit is free.</h3>
            {leadSent ? (
              <div className="pld-thanks">
                <p>
                  Thank you, {lead.name.trim()}. {profile?.owner_name || 'We'} will message or call you {profile?.callback_promise || 'within one working day'} to pick a visit day; visits are usually within the week. Have a recent bill handy.
                </p>
                <div className="pld-row">
                  {messengerHref && (
                    <a className="pld-btn pld-primary" href={messengerHref} target="_blank" rel="noreferrer">
                      Open Messenger
                    </a>
                  )}
                  <button type="button" className="pld-btn" onClick={copySummary}>
                    {copied ? 'Copied' : 'Copy my estimate'}
                  </button>
                </div>
              </div>
            ) : (
              <>
                <p className="pld-hint">
                  Most installers quote from a satellite photo. We put a test panel and meters on your roof, measure the sun and the shade, and quote exactly. No cost, no obligation.
                </p>
                <div className="pld-row">
                  <label className="pld-field">
                    <span>Your name</span>
                    <input value={lead.name} autoComplete="name" onChange={(ev) => setLead({ ...lead, name: ev.target.value })} />
                  </label>
                  <label className="pld-field">
                    <span>Mobile number or Messenger name</span>
                    <input value={lead.contact} inputMode="tel" autoComplete="tel" onChange={(ev) => setLead({ ...lead, contact: ev.target.value })} placeholder="0917 123 4567" />
                  </label>
                </div>
                <div className="pld-row">
                  <label className="pld-field">
                    <span>Address or a landmark near you (optional)</span>
                    <input value={lead.address} onChange={(ev) => setLead({ ...lead, address: ev.target.value })} placeholder={result.inputs.town ? `${result.inputs.town}, ${result.inputs.province}` : ''} />
                  </label>
                  <div className="pld-field">
                    <span>Best time to reach you</span>
                    <div className="pld-chips">
                      {TIMES.map((t) => (
                        <button key={t} type="button" className={`pld-chip ${lead.preferred_time === t ? 'on' : ''}`} onClick={() => setLead({ ...lead, preferred_time: lead.preferred_time === t ? '' : t })}>
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                <label className="pld-honey" aria-hidden="true">
                  Website
                  <input tabIndex={-1} autoComplete="off" value={lead.website} onChange={(ev) => setLead({ ...lead, website: ev.target.value })} />
                </label>
                {leadError && <div className="pld-note pld-bad">{leadError}</div>}
                <button type="button" className="pld-btn pld-primary pld-wide" onClick={sendLead} disabled={!lead.name.trim() || !lead.contact.trim() || leadBusy}>
                  {leadBusy ? 'Sending…' : 'Book my free roof visit'}
                </button>
                {(!lead.name.trim() || !lead.contact.trim()) && <div className="pld-hint pld-center">Your name and a number or Messenger name are enough.</div>}
                <div className="pld-privacy">{profile?.privacy_note || 'We use your name and number only to arrange your visit and send your estimate. We never pass them on.'}</div>
              </>
            )}
            {embedded && trust.length > 0 && (
              <ul className="pld-trust pld-trust-book">
                {trust.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            )}
          </div>

          <details className="pld-details">
            <summary>How we worked this out</summary>
            <div className="pld-breakdown">
              <div>
                <span>Materials</span>
                <b>{php0(shown.price.materials)}</b>
              </div>
              <div>
                <span>Installation and permits</span>
                <b>{php0(shown.price.labor)}</b>
              </div>
              <div>
                <span>Installation tools</span>
                <b>{php0(shown.price.equipment)}</b>
              </div>
              <div>
                <span>VAT (12%)</span>
                <b>{php0(shown.price.tax)}</b>
              </div>
              {shown.price.battery_part > 0 && (
                <div>
                  <span>Of which the battery</span>
                  <b>{php0(shown.price.battery_part)}</b>
                </div>
              )}
            </div>
            {e && (
              <p>
                Saved over {e.analysis_years} years: about {php0(e.lifetime_net)}, after paying for the system, upkeep and replacement parts. About {e.co2_t_per_year.toFixed(1)} tonnes of CO₂ avoided a year.
              </p>
            )}
            <ul>
              {result.assumptions.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
            <p className="pld-hint">This is an estimate from your answers, not a quotation. On the free roof visit we measure your roof and the sun on it, then give you an exact proposal.</p>
          </details>
        </section>
      )}

      {stickyShown && shown && (
        <div className="pld-sticky">
          <div>
            <div className="pld-sticky-label">Estimated price</div>
            <div className="pld-sticky-price">{php0(shown.price.total)}</div>
          </div>
          <a className="pld-btn pld-primary" href="#pld-book" onClick={(ev) => { ev.preventDefault(); document.getElementById('pld-book')?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }}>
            Book my free roof visit
          </a>
        </div>
      )}

      {!embedded && profile && (
        <footer className="pld-foot">
          {trust.length > 0 && (
            <ul className="pld-trust">
              {trust.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          )}
          {status && status !== 'down' && status.warranty.length > 0 && (
            <ul className="pld-trust pld-warranty">
              {status.warranty.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
          <div className="pld-contact">
            {profile.owner_name && <span>{profile.owner_name}</span>}
            {profile.phone && <a href={telHref}>{profile.phone}</a>}
            {messengerHref && (
              <a href={messengerHref} target="_blank" rel="noreferrer">
                Messenger
              </a>
            )}
            {profile.facebook && (
              <a href={profile.facebook} target="_blank" rel="noreferrer">
                Facebook
              </a>
            )}
            {profile.email && <a href={`mailto:${profile.email}`}>{profile.email}</a>}
          </div>
        </footer>
      )}
    </div>
  )
}
