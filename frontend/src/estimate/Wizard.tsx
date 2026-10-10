// The four questions of the public estimate, one card at a time: the visitor answers, the card slides
// away and the next one slides in. Every answer draws a cue above the question (an inline SVG that
// reacts to the choice: the house under the sun, the pin dropping on the town, the meter filling, the
// day and the night over the house). The state lives in Estimate.tsx and comes in as props; this
// file holds the order of the cards, the slide and the cues. The words of the questions and the
// choices are the ones the form carried before.
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import type { EstimateStatus, Goal, Pattern, Town } from './types'

const GOALS: { id: Goal; title: string; text: string }[] = [
  { id: 'net_metering', title: 'A lower bill', text: 'Solar runs the house by day. Extra power goes to your electric company as credit on your bill (net metering). A battery can be added later for brownouts.' },
  { id: 'combination', title: 'A lower bill, and lights in a brownout', text: 'Solar by day, battery at night and during brownouts. Extra power still earns credit on your bill.' },
  { id: 'off_grid', title: 'Battery first, nothing sold back', text: 'More panels and a battery carry the house day and night; the grid steps in only when both fall short, and nothing is sold back. For homes that would rather keep their own power than sell it, and for places where net metering is out of reach.' },
]
const PATTERNS: { id: Pattern; title: string; text: string }[] = [
  { id: 'morning', title: 'Mostly morning', text: 'Cooking, laundry, the pump and aircon early in the day.' },
  { id: 'balanced', title: 'All day', text: 'Someone is home most of the day.' },
  { id: 'evening', title: 'Mostly evening', text: 'The house is busiest after dark: aircon, TV, cooking.' },
]
const QUESTIONS = ['What do you want from solar?', 'Where is your house?', 'How much electricity do you use in a month?', 'When does your house use the most power?']
const LAST = QUESTIONS.length - 1
/** The slide between two cards, and the pause after a choice so the visitor sees it land before the card moves. */
const SLIDE_MS = 320
const LAND_MS = 350
/** The meter dial on card 3 is full at this much a month; anything past it stays full. */
const DIAL_KWH = 1000
const DIAL_PHP = 15000

const reducedMotion = () => typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
const num = (s: string) => parseFloat(s.replace(/,/g, ''))
const n0 = (v: number) => Math.round(v).toLocaleString()

type Dir = 'next' | 'back'

export interface WizardProps {
  goal: Goal
  setGoal: (g: Goal) => void
  province: string
  setProvince: (p: string) => void
  townName: string
  setTownName: (t: string) => void
  provinces: string[]
  townsHere: Town[]
  pin: { lat: number; lon: number } | null
  setPin: (p: { lat: number; lon: number } | null) => void
  found: string
  setFound: (f: string) => void
  useGps: () => void
  geoBusy: boolean
  kwh: string
  setKwh: (v: string) => void
  php: string
  setPhp: (v: string) => void
  pattern: Pattern
  setPattern: (p: Pattern) => void
  ready: boolean
  enabled: boolean
  busy: boolean
  error: string | null
  run: () => void
  downNote: ReactNode
  status: EstimateStatus | null | 'down'
}

export default function Wizard(p: WizardProps) {
  const id = useId()
  const [card, setCard] = useState(0)
  const [dir, setDir] = useState<Dir>('next')
  // the card on its way out: rendered once more, inert, for the length of the slide
  const [ghost, setGhost] = useState<{ index: number; dir: Dir } | null>(null)
  const [minH, setMinH] = useState(0)
  // cards 1 and 4 start with nothing pressed: the state carries a default, but the question has not been answered yet
  const [goalDone, setGoalDone] = useState(false)
  const [patternDone, setPatternDone] = useState(false)
  const stageRef = useRef<HTMLDivElement>(null)
  const qRef = useRef<HTMLHeadingElement>(null)
  const pending = useRef(0)
  const mounted = useRef(false)
  // the latest run and go: a choice schedules them 350 ms later, after the state it set has rendered
  const latest = useRef({ run: p.run, go: (_to: number) => {} })

  const kwhNum = num(p.kwh)
  const phpNum = num(p.php)
  const hasUse = (Number.isFinite(kwhNum) && kwhNum > 0) || (Number.isFinite(phpNum) && phpNum > 0)
  const hasPlace = !!p.townName || !!p.pin
  const answered = [goalDone, hasPlace, hasUse, patternDone]

  const go = (to: number) => {
    if (to === card || to < 0 || to > LAST) return
    window.clearTimeout(pending.current)
    const d: Dir = to > card ? 'next' : 'back'
    if (!reducedMotion()) {
      setMinH(stageRef.current?.offsetHeight ?? 0)
      setGhost({ index: card, dir: d })
    }
    setDir(d)
    setCard(to)
  }
  useEffect(() => {
    latest.current = { run: p.run, go }
  })

  useEffect(() => {
    if (!ghost) return
    const t = window.setTimeout(() => {
      setGhost(null)
      setMinH(0)
    }, SLIDE_MS + 40)
    return () => window.clearTimeout(t)
  }, [ghost])
  // the new card's question takes the focus (not on the first paint: the page has just loaded)
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true
      return
    }
    const h = qRef.current
    if (!h) return
    h.focus({ preventScroll: true })
    const top = stageRef.current?.getBoundingClientRect().top ?? 0
    if (top < 0) window.scrollBy({ top: top - 12, behavior: reducedMotion() ? 'auto' : 'smooth' })
  }, [card])
  useEffect(() => () => window.clearTimeout(pending.current), [])

  const chooseGoal = (g: Goal) => {
    p.setGoal(g)
    setGoalDone(true)
    window.clearTimeout(pending.current)
    pending.current = window.setTimeout(() => latest.current.go(1), LAND_MS)
  }
  const choosePattern = (pt: Pattern) => {
    if (p.busy) return
    p.setPattern(pt)
    setPatternDone(true)
    window.clearTimeout(pending.current)
    // the last answer lands; the visitor presses "Show my estimate" when ready
  }
  const enterGoesNext = (ev: KeyboardEvent<HTMLInputElement>) => {
    if (ev.key !== 'Enter') return
    ev.preventDefault()
    if (hasUse) go(card + 1)
  }

  const renderCard = (i: number, copy: boolean) => {
    const qid = `${id}-q${i}${copy ? '-out' : ''}`
    let cue: ReactNode = null
    let body: ReactNode = null
    if (i === 0) {
      cue = <GoalCue goal={goalDone ? p.goal : ''} />
      body = (
        <div className="pld-choices">
          {GOALS.map((g) => {
            const on = goalDone && p.goal === g.id
            return (
              <button key={g.id} type="button" className={`pld-choice ${on ? 'on' : ''}`} onClick={() => chooseGoal(g.id)} aria-pressed={on}>
                <b>{g.title}</b>
                <small>{g.text}</small>
              </button>
            )
          })}
        </div>
      )
    } else if (i === 1) {
      cue = <PlaceCue town={p.townName} province={p.province} busy={p.geoBusy} located={!!p.pin} />
      body = (
        <>
          <div className="pld-row">
            <label className="pld-field">
              <span>Province</span>
              <select
                value={p.province}
                onChange={(ev) => {
                  p.setProvince(ev.target.value)
                  p.setTownName('')
                  p.setFound('')
                }}
              >
                <option value="">Choose</option>
                {p.provinces.map((x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ))}
              </select>
            </label>
            <label className="pld-field">
              <span>Town or city</span>
              <select
                value={p.townName}
                disabled={!p.province}
                onChange={(ev) => {
                  p.setTownName(ev.target.value)
                  if (ev.target.value) p.setPin(null)
                  if (ev.target.value !== p.townName) p.setFound('')
                }}
              >
                <option value="">{p.province ? 'Choose' : 'Pick a province first'}</option>
                {p.townsHere.map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {p.found && p.townName ? (
            <div className="pld-hint">Your location points at {p.found}. Change it if that's not where the house is.</div>
          ) : p.pin && !p.townName ? (
            <div className="pld-hint">Location set from your phone. Pick a town instead if that's not where the house is.</div>
          ) : (
            <div className="pld-hint">
              At the house?{' '}
              <button type="button" className="pld-link" onClick={p.useGps} disabled={p.geoBusy}>
                {p.geoBusy ? 'Finding your town…' : 'Use my location'}
              </button>{' '}
              and the town fills in. Not in the list? Message us.
            </div>
          )}
        </>
      )
    } else if (i === 2) {
      cue = <UseCue kwh={kwhNum} php={phpNum} />
      body = (
        <>
          <div className="pld-row">
            <label className="pld-field">
              <span>kWh on your latest bill</span>
              <input inputMode="decimal" value={p.kwh} onChange={(ev) => p.setKwh(ev.target.value)} onKeyDown={enterGoesNext} placeholder="e.g. 338" />
            </label>
            <label className="pld-field">
              <span>or the amount you paid (₱)</span>
              <input inputMode="decimal" value={p.php} onChange={(ev) => p.setPhp(ev.target.value)} onKeyDown={enterGoesNext} placeholder="e.g. 4,000" />
            </label>
          </div>
          <div className="pld-hint">The kWh is printed on the bill, usually near "consumption". Either one is fine.</div>
        </>
      )
    } else {
      cue = <TimeCue pattern={patternDone ? p.pattern : ''} />
      body = (
        <div className="pld-choices">
          {PATTERNS.map((pt) => {
            const on = patternDone && p.pattern === pt.id
            return (
              <button key={pt.id} type="button" className={`pld-choice ${on ? 'on' : ''}`} onClick={() => choosePattern(pt.id)} aria-pressed={on}>
                <b>{pt.title}</b>
                <small>{pt.text}</small>
              </button>
            )
          })}
        </div>
      )
    }
    return (
      <>
        <div className="pld-wz-cue" aria-hidden="true">
          {cue}
        </div>
        <h2 className="pld-wz-q" id={qid} tabIndex={-1} ref={copy ? undefined : qRef}>
          {QUESTIONS[i]}
        </h2>
        {body}
      </>
    )
  }

  const last = card === LAST
  return (
    <div className="pld-wz">
      {(p.status === 'down' || (p.status && !p.status.enabled)) && <div className="pld-note pld-warn">{p.downNote}</div>}
      <div className="pld-wz-progress">
        <span className="pld-wz-dots" aria-hidden="true">
          {QUESTIONS.map((_, i) => (
            <i key={i} className={i === card ? 'on' : i < card ? 'done' : ''} />
          ))}
        </span>
        <span className="pld-wz-count">
          {card + 1} of {QUESTIONS.length}
        </span>
      </div>
      <div className="pld-wz-stage" ref={stageRef} style={minH ? { minHeight: minH } : undefined}>
        {ghost && (
          <div className={`pld-wz-card pld-wz-leave pld-wz-leave-${ghost.dir}`} aria-hidden="true" inert>
            {renderCard(ghost.index, true)}
          </div>
        )}
        <div key={card} className={`pld-wz-card pld-wz-enter pld-wz-enter-${dir}`} role="group" aria-labelledby={`${id}-q${card}`}>
          {renderCard(card, false)}
        </div>
      </div>
      {p.error && <div className="pld-note pld-bad">{p.error}</div>}
      <div className="pld-wz-nav">
        {card > 0 && (
          <button type="button" className="pld-btn pld-wz-back" onClick={() => go(card - 1)} disabled={p.busy}>
            Back
          </button>
        )}
        {last ? (
          <button type="button" className="pld-btn pld-primary pld-wide" onClick={p.run} disabled={!p.ready || p.busy || !p.enabled || !patternDone}>
            {p.busy ? 'Working it out…' : 'Show my estimate'}
          </button>
        ) : (
          <button type="button" className="pld-btn pld-primary pld-wz-next" onClick={() => go(card + 1)} disabled={!answered[card]}>
            Next
          </button>
        )}
      </div>
      {last && !p.ready && <div className="pld-hint pld-center">{!hasPlace ? 'Pick your town and enter your monthly use first.' : 'Enter your monthly use first.'}</div>}
      {last && p.ready && !patternDone && <div className="pld-hint pld-center">Choose one first.</div>}
    </div>
  )
}

/* ---------- the cues: inline SVG, 800×260, gold on dark; the words carry the meaning, these are aria-hidden ---------- */

const SUN_RAYS = Array.from({ length: 8 }, (_, k) => {
  const a = (k * Math.PI) / 4
  const c = Math.cos(a)
  const s = Math.sin(a)
  return `M${(30 * c).toFixed(1)} ${(30 * s).toFixed(1)}L${(38 * c).toFixed(1)} ${(38 * s).toFixed(1)}`
}).join('')
const STARS: [number, number, number][] = [[62, 42, 2], [128, 24, 1.5], [214, 62, 1.5], [296, 30, 2], [462, 22, 1.5], [524, 46, 2], [592, 72, 1.5], [704, 30, 2], [762, 74, 1.5], [360, 48, 1.2]]
/** A crescent, 44 units tall, centred on its group's origin. */
const MOON = 'M0-22A22 22 0 1 1 0 22A26 26 0 0 0 0-22Z'

/** The house every cue shares: walls, roof, door, two windows, the panels on the roof, the aircon unit on the right wall. */
function House() {
  return (
    <g className="wz-house">
      <rect className="wz-wall" x="320" y="132" width="160" height="74" />
      <path className="wz-roof" d="M304 134L400 78L496 134" />
      <path className="wz-panel" d="M322 122L379 90L374 81L317 113Z" />
      <path className="wz-panel-lines" d="M341 111L336 102M361 100L356 91" />
      <path className="wz-panel" d="M478 122L421 90L426 81L483 113Z" />
      <path className="wz-panel-lines" d="M459 111L464 102M439 100L444 91" />
      <rect className="wz-door" x="389" y="168" width="22" height="38" />
      <g className="wz-lit">
        <rect className="wz-win-halo" x="330" y="140" width="46" height="40" rx="8" />
        <rect className="wz-win-halo" x="424" y="140" width="46" height="40" rx="8" />
        <rect className="wz-win-fill" x="338" y="148" width="30" height="24" />
        <rect className="wz-win-fill" x="432" y="148" width="30" height="24" />
        <rect className="wz-ac-halo" x="480" y="154" width="36" height="26" rx="6" />
      </g>
      <rect className="wz-win" x="338" y="148" width="30" height="24" />
      <path className="wz-win-bars" d="M353 148V172M338 160H368" />
      <rect className="wz-win" x="432" y="148" width="30" height="24" />
      <path className="wz-win-bars" d="M447 148V172M432 160H462" />
      <rect className="wz-ac" x="486" y="159" width="26" height="16" rx="2" />
      <circle className="wz-fan" cx="499" cy="167" r="5" />
      <path className="wz-fan-blades" d="M499 162V172M494 167H504" />
    </g>
  )
}

/** The pole at the right, its wire to the house, the street lamp, and the neighbour's house beyond it. */
function Street() {
  return (
    <g className="wz-street">
      <line className="wz-pole" x1="640" y1="206" x2="640" y2="92" />
      <path className="wz-pole" d="M622 100H658" />
      <path className="wz-wire" d="M497 136Q560 126 626 102" />
      <path className="wz-wire wz-wire-far" d="M654 102Q720 118 800 112" />
      <path className="wz-pole" d="M640 120H612" />
      <circle className="wz-lamp-halo" cx="608" cy="123" r="16" />
      <circle className="wz-lamp" cx="608" cy="123" r="5" />
      <rect className="wz-nwall" x="690" y="160" width="70" height="46" />
      <path className="wz-nroof" d="M684 162L725 130L766 162" />
      <rect className="wz-nwin" x="700" y="172" width="16" height="14" />
      <rect className="wz-nwin" x="734" y="172" width="16" height="14" />
    </g>
  )
}

function Sky({ clip }: { clip: string }) {
  return (
    <g clipPath={clip}>
      <rect className="wz-night" x="0" y="0" width="800" height="206" />
      <g className="wz-stars">
        {STARS.map(([x, y, r], i) => (
          <circle key={i} cx={x} cy={y} r={r} />
        ))}
      </g>
    </g>
  )
}

/** Card 1: the house; the sun and the meter running backwards for a lower bill; a dark street with lit windows and a glowing battery for the brownout; the battery and a faded grid line for nothing sold back. */
function GoalCue({ goal }: { goal: Goal | '' }) {
  const id = useId()
  return (
    <svg className="pld-wz-svg pld-wz-goal" viewBox="0 0 800 260" data-goal={goal} focusable="false">
      <defs>
        <clipPath id={`${id}-r`}>
          <rect x="0" y="0" width="800" height="260" rx="14" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id}-r)`}>
        <rect className="wz-bg" x="0" y="0" width="800" height="260" />
        <Sky clip={`url(#${id}-r)`} />
        <rect className="wz-ground" x="0" y="206" width="800" height="54" />
      </g>
      <line className="wz-horizon" x1="0" y1="206" x2="800" y2="206" />
      <g className="wz-sun" transform="translate(150 72)">
        <path className="wz-rays" d={SUN_RAYS} />
        <circle r="22" />
      </g>
      <g className="wz-moon" transform="translate(640 58)">
        <path d={MOON} />
      </g>
      <Street />
      <House />
      <g className="wz-meter">
        <rect className="wz-meter-box" x="296" y="150" width="22" height="24" rx="2" />
        <circle className="wz-meter-dial" cx="307" cy="160" r="6" />
        <line className="wz-meter-needle" x1="307" y1="160" x2="307" y2="155" />
        <path className="wz-meter-back" d="M296 182A12 12 0 0 1 318 182" />
        <path className="wz-meter-back" d="M300 178L296 182L300 186" />
      </g>
      <g className="wz-battery">
        <rect className="wz-bat-halo" x="254" y="164" width="46" height="48" rx="10" />
        <rect className="wz-bat-nub" x="272" y="171" width="10" height="5" />
        <rect className="wz-bat" x="262" y="176" width="30" height="30" rx="3" />
        <rect className="wz-cell" x="267" y="181" width="20" height="5" />
        <rect className="wz-cell" x="267" y="189" width="20" height="5" />
        <rect className="wz-cell" x="267" y="197" width="20" height="5" />
      </g>
    </svg>
  )
}

/** Card 2: a simple outline with a pin that drops and bounces onto it; the town's name under it once chosen, "near you" while the phone's location is being read. */
function PlaceCue({ town, province, busy, located }: { town: string; province: string; busy: boolean; located: boolean }) {
  const id = useId()
  const state = town ? 'town' : busy ? 'busy' : located ? 'located' : province ? 'province' : ''
  const dropped = state === 'town' || state === 'located'
  const label = town ? town : busy || located ? 'near you' : province
  const sub = town ? province : ''
  return (
    <svg className="pld-wz-svg pld-wz-place" viewBox="0 0 800 260" data-place={state} focusable="false">
      <defs>
        <clipPath id={`${id}-r`}>
          <rect x="0" y="0" width="800" height="260" rx="14" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id}-r)`}>
        <rect className="wz-bg" x="0" y="0" width="800" height="260" />
        <path className="wz-grid" d="M160 0V260M320 0V260M480 0V260M640 0V260M0 70H800M0 140H800M0 210H800" />
        <path className="wz-land" d="M70 150C120 92 220 70 320 96C380 112 420 68 500 80C600 94 700 68 740 122C772 164 702 222 600 232C480 246 380 216 280 236C180 252 84 218 70 150Z" />
        <path className="wz-road" d="M110 190C250 170 300 118 420 142S600 192 720 150" />
        <g className="wz-towns">
          <circle cx="212" cy="150" r="3" />
          <circle cx="318" cy="112" r="3" />
          <circle cx="528" cy="110" r="3" />
          <circle cx="612" cy="172" r="3" />
          <circle cx="690" cy="120" r="3" />
        </g>
      </g>
      <circle className="wz-target" cx="400" cy="150" r="14" />
      <circle className="wz-ring" cx="400" cy="150" r="14" />
      <ellipse className="wz-shadow" cx="400" cy="151" rx="18" ry="5" />
      <g key={`${state}:${town}`} className={`wz-pin ${dropped ? 'wz-drop' : state ? 'wz-hover' : 'wz-away'}`} transform="translate(400 150)">
        <path d="M0 0C-4-14-22-22-22-40a22 22 0 1 1 44 0C22-22 4-14 0 0Z" />
        <circle cy="-40" r="8" />
      </g>
      {label && (
        <text className="wz-town" x="400" y="196" textAnchor="middle">
          {label}
        </text>
      )}
      {sub && (
        <text className="wz-prov" x="400" y="226" textAnchor="middle">
          {sub}
        </text>
      )}
    </svg>
  )
}

const DIAL_LEN = Math.PI * 120
const TICKS = [180, 135, 90, 45, 0]
  .map((a) => {
    const r = (a * Math.PI) / 180
    const c = Math.cos(r)
    const s = Math.sin(r)
    return `M${(400 + 108 * c).toFixed(1)} ${(196 - 108 * s).toFixed(1)}L${(400 + 120 * c).toFixed(1)} ${(196 - 120 * s).toFixed(1)}`
  })
  .join('')

/** Card 3: a meter dial that fills as the number grows, 0–1,000 kWh or ₱0–15,000; past the end it stays full. */
function UseCue({ kwh, php }: { kwh: number; php: number }) {
  const id = useId()
  const useKwh = Number.isFinite(kwh) && kwh > 0
  const usePhp = !useKwh && Number.isFinite(php) && php > 0
  const frac = useKwh ? Math.min(1, kwh / DIAL_KWH) : usePhp ? Math.min(1, php / DIAL_PHP) : 0
  const value = useKwh ? n0(kwh) : usePhp ? `₱${n0(php)}` : ''
  const unit = useKwh ? ' kWh a month' : usePhp ? ' a month' : ''
  return (
    <svg className="pld-wz-svg pld-wz-use" viewBox="0 0 800 260" data-full={frac >= 1 ? 'yes' : 'no'} focusable="false">
      <defs>
        <clipPath id={`${id}-r`}>
          <rect x="0" y="0" width="800" height="260" rx="14" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id}-r)`}>
        <rect className="wz-bg" x="0" y="0" width="800" height="260" />
      </g>
      <path className="wz-track" d="M280 196A120 120 0 0 1 520 196" />
      <path className="wz-fill" d="M280 196A120 120 0 0 1 520 196" style={{ strokeDasharray: DIAL_LEN, strokeDashoffset: DIAL_LEN * (1 - frac) }} />
      <path className="wz-ticks" d={TICKS} />
      <line className="wz-needle" x1="400" y1="196" x2="400" y2="104" style={{ transform: `rotate(${-90 + 180 * frac}deg)` }} />
      <circle className="wz-hub" cx="400" cy="196" r="8" />
      {value && (
        <text className="wz-reading" x="400" y="248" textAnchor="middle">
          <tspan className="wz-num">{value}</tspan>
          <tspan className="wz-unit">{unit}</tspan>
        </text>
      )}
    </svg>
  )
}

/** Card 4: the sun arcs and the moon rises over the house; the windows and the aircon light in the morning, all day or in the evening to match the pattern. A 6-second loop; a still frame under reduced motion. */
function TimeCue({ pattern }: { pattern: Pattern | '' }) {
  const id = useId()
  return (
    <svg className="pld-wz-svg pld-wz-time" viewBox="0 0 800 260" data-pattern={pattern} focusable="false">
      <defs>
        <clipPath id={`${id}-r`}>
          <rect x="0" y="0" width="800" height="260" rx="14" />
        </clipPath>
        <clipPath id={`${id}-sky`}>
          <rect x="0" y="0" width="800" height="206" rx="14" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id}-r)`}>
        <rect className="wz-bg" x="0" y="0" width="800" height="260" />
        <Sky clip={`url(#${id}-r)`} />
        <rect className="wz-ground" x="0" y="206" width="800" height="54" />
      </g>
      <g clipPath={`url(#${id}-sky)`}>
        <g className="wz-sun">
          <g transform="translate(400 70)">
            <path className="wz-rays" d={SUN_RAYS} />
            <circle r="22" />
          </g>
        </g>
        <g className="wz-moon">
          <g transform="translate(400 70)">
            <path d={MOON} />
          </g>
        </g>
      </g>
      <line className="wz-horizon" x1="0" y1="206" x2="800" y2="206" />
      <Street />
      <House />
    </svg>
  )
}
