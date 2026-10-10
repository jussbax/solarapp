import { useEffect, useMemo, useRef, useState } from 'react'
import { emit, isUnavailable, makeApi, readSource } from './api'
import DayScene from './DayScene'
import type { EstimateResult, EstimateStatus, Goal, Pattern, Town, Variant } from './types'
import Wizard from './Wizard'

const php0 = (v: number | null | undefined) => (v == null || !Number.isFinite(v) ? '-' : `${v < 0 ? '-' : ''}₱${Math.abs(Math.round(v)).toLocaleString()}`)
/** A savings figure as a person says it: "₱1.03 million", "₱61,000", "₱3,800" (the price and the bill stay exact). */
const phpAbout = (v: number) => {
  const a = Math.abs(v)
  const text = a >= 1_000_000 ? `₱${(Math.round(a / 10_000) / 100).toString()} million` : a >= 10_000 ? `₱${(Math.round(a / 1000) * 1000).toLocaleString()}` : `₱${(Math.round(a / 100) * 100).toLocaleString()}`
  return `${v < 0 ? '-' : ''}${text}`
}
const n0 = (v: number) => Math.round(v).toLocaleString()
const years = (v: number | null | undefined, horizon: number) => (v == null ? `more than ${horizon} years` : v < 1 ? 'under a year' : `${v.toFixed(1)} years`)
/** A bill under this prints as "a small bill": the fixed charges never go away, and the grid still bills the hours it steps in. */
const SMALL_BILL = 100

const TIMES = ['Morning', 'Afternoon', 'Evening']

const PATTERN_WORDS: Record<string, string> = { morning: 'mostly in the morning', balanced: 'spread through the day', evening: 'mostly in the evening' }

/** The battery the price includes (the catalogue unit); anything under half a kWh is no battery at all. */
const hasBattery = (v: Variant) => v.system.battery_kwh >= 0.5
/** The place after "estimate" or "a house": " for Pila, Laguna" / " in Pila, Laguna"; a pin reads " near Quezon City, Metro Manila";
 * a pin outside the Philippines adds nothing (the warning says where it fell). */
const placeAfter = (place: string, word: 'for' | 'in') => (place.startsWith('near ') ? ` ${place}` : place.startsWith('outside') ? '' : ` ${word} ${place}`)

/** What goes on the house, in words: the panel count and what the battery carries; the sizes wait for the proposal. */
function systemLine(v: Variant) {
  const s = v.system
  const panels = `${s.panels} ${s.panels === 1 ? 'panel' : 'panels'} on the roof`
  if (!hasBattery(v)) return `${panels} and a hybrid inverter on the wall; a battery can be added whenever you want lights in a brownout too`
  return `${panels}, a hybrid inverter on the wall and a lithium battery${s.battery_note ? `, ${s.battery_note}` : ''}`
}

/** What the system does for the house, by goal; "a small bill" only where the panels make more than the house uses. */
function doesLine(v: Variant, makesPct: number) {
  if (v.goal === 'off_grid') return 'The panels and the battery carry an ordinary day on their own, and the grid is only the spare; nothing is sold back, so once the battery is full the extra sun goes unused. In long rainy spells the grid still steps in; your proposal says how much.'
  if (v.goal === 'net_metering') return "By day the panels run the house; the rest of the day's sun goes back through the meter as credit on your bill, at your electric company's generation rate; the evening runs on the grid, as it does today, so what still comes is a smaller bill."
  return `By day the panels run the house and fill the battery; the battery carries the evening; the extra goes to your electric company and comes back as credit at its generation rate, so what still comes is ${makesPct > 100 ? 'a small bill for the fixed charges and the hours the grid covers' : 'a smaller bill'}.`
}

/** The system in the forwarded summary: the panel count and the battery in words, sized to a typical roof (and house) until the visit;
 * the proposal, never the visit's readings, is what fits them to the reader's own. */
function summarySystem(v: Variant) {
  const s = v.system
  const panels = `${s.panels} ${s.panels === 1 ? 'panel' : 'panels'}`
  const battery = hasBattery(v) ? ` and a battery${s.battery_note ? `, ${s.battery_note}` : ''}` : ', and a battery can be added later'
  const typical = hasBattery(v) ? 'a typical roof and a typical house' : 'a typical roof'
  return `${panels}${battery}; sized to ${typical} until the free on-site assessment, and fitted to yours in the proposal.`
}

/** The other variant's bill inside a clause: "the bill about ₱1,252 a month", or "a small bill" under SMALL_BILL. */
const billWords = (after: number) => (after < SMALL_BILL ? 'a small bill' : `the bill about ${php0(after)} a month`)

/** "https://m.me/pldev" -> "m.me/pldev", for text that gets copied and forwarded. */
const bareUrl = (u: string) => u.replace(/^https?:\/\//, '').replace(/\/$/, '')
/** "Maria Santos" -> "Maria" on the thank-you; a single word stays as typed. */
const firstName = (name: string) => {
  const words = name.trim().split(/\s+/)
  return words.length >= 2 ? words[0] : name.trim()
}

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
  const [found, setFound] = useState('')   // "Pila, Laguna": the town the phone's location pointed at, shown under the pickers
  const [geoBusy, setGeoBusy] = useState(false)
  const [kwh, setKwh] = useState('')
  const [pattern, setPattern] = useState<Pattern>('balanced')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<EstimateResult | null>(null)
  const [withBattery, setWithBattery] = useState<boolean | null>(null)
  const [lead, setLead] = useState({ name: '', contact: '', address: '', preferred_time: '', website: '' })
  const [leadBusy, setLeadBusy] = useState(false)
  const [leadError, setLeadError] = useState<string | null>(null)
  const [leadSent, setLeadSent] = useState(false)
  const [showForm, setShowForm] = useState(true)   // the form folds away once the estimate is on screen; "Try other answers" brings a fresh one back
  const [copied, setCopied] = useState(false)
  const [bookInView, setBookInView] = useState(false)
  const resultRef = useRef<HTMLDivElement>(null)
  const formRef = useRef<HTMLElement>(null)
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
  // every province of the country; a province's towns are fetched when it is picked (1,600 rows in all, a few dozen each)
  const provinces = useMemo(() => {
    if (!status || status === 'down') return []
    return status.provinces ?? Array.from(new Set((status.towns ?? []).map((t) => t.province)))
  }, [status])
  const [fetched, setFetched] = useState<Record<string, Town[]>>({})
  const townsHere = useMemo(() => {
    if (!province) return []
    const local = status && status !== 'down' ? (status.towns ?? []).filter((t) => t.province === province) : []
    return (local.length ? local : (fetched[province] ?? [])).slice().sort((a, b) => a.name.localeCompare(b.name))
  }, [province, status, fetched])
  useEffect(() => {
    if (!province || townsHere.length || fetched[province]) return
    let live = true
    api
      .towns(province)
      .then((rows) => {
        if (live) setFetched((f) => ({ ...f, [province]: rows }))
      })
      .catch(() => {
        if (live) setFetched((f) => ({ ...f, [province]: [] }))
      })
    return () => {
      live = false
    }
  }, [province, townsHere.length, fetched, api])
  const kwhNum = parseFloat(kwh.replace(/,/g, ''))
  const hasUse = Number.isFinite(kwhNum) && kwhNum > 0
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
      async (p) => {
        const at = { lat: +p.coords.latitude.toFixed(5), lon: +p.coords.longitude.toFixed(5) }
        try {
          const r = await api.place(at.lat, at.lon)
          if (!r.inside) {
            setError("Your location is outside the Philippines. Pick the town of the house instead.")
          } else {
            // the pickers show the town the location points at; the visitor can still change it
            setProvince(r.province)
            setTownName(r.town)
            setPin(null)
            setFound(`${r.town}, ${r.province}`)
          }
        } catch {
          setPin(at)   // the lookup failed: the estimate still runs on the location itself
          setTownName('')
          setFound('')
        }
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
    monthly_php: null,
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
      setShowForm(false)
      // a visit already booked stays booked: the thank-you keeps its place under a second or third estimate
      emit('estimate_shown', { goal: r.goal, panels: r.system.panels, price: r.price.total })
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
    } catch (e) {
      showError(e)
    } finally {
      setBusy(false)
    }
  }

  const estimateAnother = () => {
    setResult(null)
    setShowForm(true)
    setGoal('combination')
    setProvince('')
    setTownName('')
    setPin(null)
    setFound('')
    setKwh('')
    setPattern('balanced')
    setError(null)
    setTimeout(() => formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }
  const goBook = (ev: { preventDefault: () => void }) => {
    ev.preventDefault()
    document.getElementById('pld-book')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  // the variant on screen: the one asked for, or the battery alternative the visitor toggled to
  const shown: Variant | null = useMemo(() => {
    if (!result) return null
    if (withBattery == null || result.alternative == null) return result
    return withBattery === hasBattery(result) ? result : result.alternative
  }, [result, withBattery])
  const other: Variant | null = result && shown ? (shown === result ? result.alternative : result) : null
  const stickyShown = !!(result && shown && !leadSent && !bookInView)

  // the sticky bar steps aside while the booking form (with its own button) is on screen:
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
  const validDays = (status && status !== 'down' && status.proposal_valid_days) || 15
  const summaryText = () => {
    if (!shown || !result) return ''
    const e = shown.economics
    const links = [messengerHref ? `Questions: ${bareUrl(messengerHref)}` : '', estimateUrl ? `Run your own: ${bareUrl(estimateUrl)}` : ''].filter(Boolean).join(' · ')
    return [
      `Solar estimate from ${profile?.company_name || 'PL Development Inc.'} for a house${placeAfter(result.inputs.place, 'in')}:`,
      e ? `Bill ${php0(e.bill_before_monthly)} → ${e.bill_after_monthly < SMALL_BILL ? 'a small bill' : `about ${php0(e.bill_after_monthly)} a month`}; about ${phpAbout(e.savings_year1)} saved in the first year; pays for itself in ${years(e.payback_years, e.analysis_years)}.` : '',
      `Price ${php0(shown.price.total)}, installed, permits and VAT included.`,
      summarySystem(shown),
      'This is an estimate, not a quotation; the free on-site assessment makes it exact.',
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
  const trustHead = profile ? (profile.company_name && profile.address ? `${profile.company_name}, ${profile.address}` : profile.company_name || '') : ''
  const trust = profile
    ? [
        profile.pee_name || profile.pee_license ? 'Electrical plans signed and sealed by a Professional Electrical Engineer' : '',
        profile.brands,
        ...(status && status !== 'down' ? status.warranty ?? [] : []),
        profile.owner_name && profile.phone ? `${profile.owner_name}, ${profile.phone}` : '',
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

      {showForm && (
      <section className="pld-card" ref={formRef}>
        <h1 className="pld-h1">Your new bill is a minute away.</h1>
        <p className="pld-lead">
          Four questions, then the bill you would pay instead, the price of the whole job, and how many panels it takes. The only call you get is the one you book.
        </p>
        <Wizard
          goal={goal} setGoal={setGoal}
          province={province} setProvince={setProvince}
          townName={townName} setTownName={setTownName}
          provinces={provinces} townsHere={townsHere}
          pin={pin} setPin={setPin} found={found} setFound={setFound}
          useGps={useGps} geoBusy={geoBusy}
          kwh={kwh} setKwh={setKwh}
          pattern={pattern} setPattern={setPattern}
          ready={ready} enabled={enabled} busy={busy} error={error} run={run}
          downNote={downNote} status={status}
        />
      </section>
      )}

      {result && shown && prod && (
        <section className="pld-card" id="pld-result" ref={resultRef}>
          <h2 className="pld-h2">Your estimate{placeAfter(result.inputs.place, 'for')}</h2>
          {result.warnings.map((w, i) => (
            <div key={i} className="pld-note pld-warn">
              {w}
            </div>
          ))}
          <DayScene variant={shown} />
          <div className="pld-hero">
            {e ? (
              <>
                <div className="pld-hero-row">
                  <div className="pld-hero-label">Your monthly bill</div>
                  <div className="pld-hero-big">
                    {php0(e.bill_before_monthly)} <span className="pld-arrow">→</span> {e.bill_after_monthly < SMALL_BILL ? 'a small bill' : `about ${php0(e.bill_after_monthly)}`}
                  </div>
                  <div className="pld-hero-sub">
                    {e.bill_after_monthly < SMALL_BILL
                      ? `about ${php0(e.savings_monthly)} a month stays in your pocket; what still comes is your electric company's fixed charges, and the grid's hours in long rainy spells`
                      : `about ${php0(e.savings_monthly)} a month stays in your pocket; what still comes is your electric company's fixed charges and the hours the grid covers`}
                  </div>
                </div>
                <div className="pld-hero-grid">
                  <div>
                    <div className="pld-hero-label">Pays for itself in</div>
                    <div className="pld-hero-mid">{years(e.payback_years, e.analysis_years)}</div>
                    <div className="pld-hero-sub">about {phpAbout(e.savings_year1)} saved in the first year</div>
                  </div>
                  <div>
                    <div className="pld-hero-label">Estimated price</div>
                    <div className="pld-hero-mid pld-gold">{php0(shown.price.total)}</div>
                    <div className="pld-hero-sub">the whole job: installed, permits and papers filed, VAT included</div>
                  </div>
                </div>
              </>
            ) : (
              <div className="pld-hero-row">
                <div className="pld-hero-label">Estimated price</div>
                <div className="pld-hero-big pld-gold">{php0(shown.price.total)}</div>
                <div className="pld-hero-sub">the whole job: installed, permits and papers filed, VAT included</div>
              </div>
            )}
          </div>

          <div className="pld-actions">
            <a className="pld-btn pld-primary" href="#pld-book" onClick={goBook}>Book my free on-site assessment</a>
            <button type="button" className="pld-btn" onClick={estimateAnother}>Try other answers</button>
          </div>

          <div className="pld-line">
            <b>What you get:</b> {systemLine(shown)}.
          </div>
          <div className="pld-line">
            <b>What it does:</b> {doesLine(shown, makesPct)}
          </div>
          {other && (
            <div className="pld-line pld-alt">
              {hasBattery(shown) ? (
                <>
                  <b>Panels only, without the battery:</b> {php0(other.price.total)}
                  {other.economics && `, ${billWords(other.economics.bill_after_monthly)}, pays for itself in ${years(other.economics.payback_years, other.economics.analysis_years)}`}.
                  {' '}The panels do the saving either way; the battery is what keeps the lights on when the street goes dark.{' '}
                  <button type="button" className="pld-link" onClick={() => setWithBattery(false)}>
                    Show it without the battery
                  </button>
                </>
              ) : (
                <>
                  <b>Want the lights on when the street goes dark?</b> A battery is about {php0(other.price.total - shown.price.total)} more{other.system.battery_note ? `, ${other.system.battery_note}` : ''}
                  {other.economics && `; ${billWords(other.economics.bill_after_monthly)}, pays for itself in ${years(other.economics.payback_years, other.economics.analysis_years)}`}.{' '}
                  <button type="button" className="pld-link" onClick={() => setWithBattery(true)}>
                    Show it with the battery
                  </button>
                </>
              )}
            </div>
          )}

          <div className="pld-line pld-visit">
            <h3 className="pld-h3">What you miss if you stop here</h3>
            <p>Close this page and nothing changes. Next month's bill comes as it does today, and this estimate stays a typical roof's, not yours. What you are left with:</p>
            <ul>
              {e && e.savings_monthly > 0 && <li>about {php0(e.savings_monthly)} a month, by this estimate, paid to your electric company instead of kept in your pocket</li>}
              <li>a roof nobody has measured for the panels it holds and the shade on it, so the exact price and the exact bill stay unknown</li>
              <li>{hasBattery(shown) ? 'a battery sized to a typical house, not to your fridge, fans, Wi-Fi and aircon, until your appliances are on the table' : 'a battery, if you want the lights on in a brownout, sized to a typical house until your own fridge, fans, Wi-Fi and aircon are on the table'}</li>
              <li>{shown.goal === 'off_grid' ? 'no plans signed and sealed, no permit, and nobody filing them' : 'no plans signed and sealed, no permit, no net metering papers, and nobody filing them'}</li>
              <li>{shown.goal === 'off_grid' ? 'no dates on the calendar: not the permit, not the installation, not the switch-on' : 'no dates on the calendar: not the permit, not the installation, not the switch-on, not the two-way meter'}</li>
            </ul>
            <p>The visit is free, and nothing is decided until you say so; book it below and every line above is answered in your proposal, within two working days.</p>
          </div>

          <div className="pld-book" id="pld-book" ref={bookRef}>
            <h3 className="pld-h3">{leadSent ? `Your on-site assessment is booked, ${firstName(lead.name)}.` : 'The exact figure is one free visit away.'}</h3>
            {leadSent ? (
              <div className="pld-thanks">
                <p>
                  Thank you, {firstName(lead.name)}. {profile?.owner_name || 'We'} will message or call you {profile?.callback_promise || 'within one working day'} to set the day; visits are usually within the week. That is all for now. Keep a recent bill where you can find it; it goes on the table at the visit.
                </p>
                <p>
                  What happens next: one free visit, with the test panel on the roof and your bill and appliances at the table; then your proposal within two working days, valid {validDays} days. You decide with all of it in front of you.
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
                  Most installers quote from a satellite photo. We put a test panel and meters on your roof, read the sun and the shade, and sit down with your bill. Then your proposal, exact to your roof, every peso and every part on paper. You decide after.
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
                  {leadBusy ? 'Sending…' : 'Book my free on-site assessment'}
                </button>
                {(!lead.name.trim() || !lead.contact.trim()) && <div className="pld-hint pld-center">Your name and a number or Messenger name are enough.</div>}
                <div className="pld-privacy">{profile?.privacy_note || 'We use your name and number only to arrange your visit and send your estimate. We never pass them on.'}</div>
              </>
            )}
            {embedded && (trustHead || trust.length > 0) && (
              <div className="pld-trust-book">
                {trustHead && <div className="pld-trust-head">{trustHead}</div>}
                {trust.length > 0 && (
                  <ul className="pld-trust">
                    {trust.map((t, i) => (
                      <li key={i}>{t}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          <p className="pld-hint pld-basis">
            Worked out for a house{placeAfter(result.inputs.place, 'in')} using about {n0(result.inputs.monthly_kwh)} kWh a month, {PATTERN_WORDS[result.inputs.pattern] ?? 'spread through the day'}.
            {' '}This is an estimate, not a quotation: on the free on-site assessment we measure your roof and the sun on it, and the proposal that follows is exact.
          </p>
        </section>
      )}

      {stickyShown && shown && (
        <div className="pld-sticky">
          <div>
            <div className="pld-sticky-label">{e ? 'Your new monthly bill' : 'Estimated price'}</div>
            <div className="pld-sticky-price">{e ? (e.bill_after_monthly < SMALL_BILL ? 'a small bill' : `about ${php0(e.bill_after_monthly)}`) : php0(shown.price.total)}</div>
          </div>
          <a className="pld-btn pld-primary" href="#pld-book" onClick={goBook}>
            Book my free on-site assessment
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
