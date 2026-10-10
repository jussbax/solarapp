// The four questions of the public estimate, one card at a time: the visitor answers, the card slides
// away and the next one slides in. Two cards carry a cue above the question (an inline SVG that reacts
// to the answer): the meter dial that fills with the monthly kWh, and the house in section with the
// people in it, more of them in the morning or in the evening as the slider moves. The state lives in
// Estimate.tsx and comes in as props; this file holds the order of the cards, the slide and the cues.
// The questions stay the engine's four; each choice sells the want, and the kind's name opens its small text.
import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import type { EstimateStatus, Goal, Pattern, Town } from './types'

const GOALS: { id: Goal; title: string; text: string }[] = [
  { id: 'net_metering', title: 'I just want a lower bill.', text: 'Solar with net metering. The panels run the house by day, and the extra comes back as credit on your bill. A battery can come later, whenever you want lights in a brownout too.' },
  { id: 'combination', title: 'I want the lights on when the street goes dark.', text: 'Solar with a battery. The panels run the house by day and bring the bill down; the battery carries the evening and the brownouts. The extra still earns credit on your bill.' },
  { id: 'off_grid', title: 'I want my roof to run my house.', text: 'Battery first, nothing sold back. More panels and a battery carry the house day and night, and the grid steps in only when both fall short. For homes that would rather keep their own power than sell it, and for places where net metering is out of reach.' },
]
/** The three stops of the slider on the last card, left to right. */
const PATTERNS: { id: Pattern; title: string; text: string }[] = [
  { id: 'morning', title: 'Mostly morning', text: 'Cooking, laundry, the pump and aircon early in the day, when the panels are already at work.' },
  { id: 'balanced', title: 'All day', text: 'Someone is home most of the day, so the house uses the sun as the panels make it.' },
  { id: 'evening', title: 'Mostly evening', text: 'The house is busiest after dark: aircon, TV, cooking. This is the evening a battery would carry.' },
]
const QUESTIONS = ['What do you want from solar?', 'Where is your house?', 'How much electricity do you use in a month?', 'When does your house use the most power?']
const LAST = QUESTIONS.length - 1
/** The slide between two cards, and the pause after a choice so the visitor sees it land before the card moves. */
const SLIDE_MS = 320
const LAND_MS = 350
/** The meter dial on card 3 is full at this much a month; anything past it stays full. */
const DIAL_KWH = 1000

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
  // card 1 starts with nothing pressed: the state carries a default, but the question has not been answered yet
  const [goalDone, setGoalDone] = useState(false)
  const stageRef = useRef<HTMLDivElement>(null)
  const qRef = useRef<HTMLHeadingElement>(null)
  const pending = useRef(0)
  const mounted = useRef(false)
  // the stage's height before a change, for the easing to the new card's height
  const fromH = useRef(0)
  // the latest go: a choice schedules it 350 ms later, after the state it set has rendered
  const goRef = useRef((_to: number) => {})

  const kwhNum = num(p.kwh)
  const hasUse = Number.isFinite(kwhNum) && kwhNum > 0
  const hasPlace = !!p.townName || !!p.pin
  const patternIdx = Math.max(0, PATTERNS.findIndex((s) => s.id === p.pattern))
  // the last card always has an answer: the slider stands at "All day" until it is moved
  const answered = [goalDone, hasPlace, hasUse, true]

  const go = (to: number) => {
    if (to === card || to < 0 || to > LAST) return
    window.clearTimeout(pending.current)
    const d: Dir = to > card ? 'next' : 'back'
    if (!reducedMotion()) {
      fromH.current = stageRef.current?.offsetHeight ?? 0
      setGhost({ index: card, dir: d })
    }
    setDir(d)
    setCard(to)
  }
  useEffect(() => {
    goRef.current = go
  })

  useEffect(() => {
    if (!ghost) return
    const t = window.setTimeout(() => setGhost(null), SLIDE_MS + 40)
    return () => window.clearTimeout(t)
  }, [ghost])
  // the stage eases from the old card's height to the new one's over the slide, so the buttons under it do not jump
  useLayoutEffect(() => {
    const stage = stageRef.current
    const from = fromH.current
    fromH.current = 0
    if (!stage || !from) return
    const to = stage.offsetHeight
    if (Math.abs(to - from) < 2) return
    stage.style.transition = 'none'
    stage.style.height = `${from}px`
    stage.getBoundingClientRect()
    stage.style.transition = `height ${SLIDE_MS}ms cubic-bezier(0.2, 0.7, 0.2, 1)`
    stage.style.height = `${to}px`
    const clear = () => {
      stage.style.transition = ''
      stage.style.height = ''
    }
    const t = window.setTimeout(clear, SLIDE_MS + 40)
    return () => {
      window.clearTimeout(t)
      clear()
    }
  }, [card])
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
    pending.current = window.setTimeout(() => goRef.current(1), LAND_MS)
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
              Your town picks the sun records your estimate is built on. At the house?{' '}
              <button type="button" className="pld-link" onClick={p.useGps} disabled={p.geoBusy}>
                {p.geoBusy ? 'Finding your town…' : 'Use my location'}
              </button>{' '}
              and the town fills in. Not in the list? Message us; we come to wherever the house is.
            </div>
          )}
        </>
      )
    } else if (i === 2) {
      cue = <UseCue kwh={kwhNum} />
      body = (
        <>
          <div className="pld-row">
            <label className="pld-field">
              <span>kWh on your latest bill</span>
              <input inputMode="decimal" value={p.kwh} onChange={(ev) => p.setKwh(ev.target.value)} onKeyDown={enterGoesNext} placeholder="e.g. 338" />
            </label>
          </div>
          <div className="pld-hint">The kWh is printed on the bill, usually next to "consumption". It sets how many panels your house needs, so you buy only what the house uses.</div>
        </>
      )
    } else {
      const stop = PATTERNS[patternIdx]
      cue = <PeopleCue pattern={stop.id} />
      body = (
        <div className="pld-wz-slider">
          <input
            type="range"
            className="pld-wz-range"
            min={0}
            max={PATTERNS.length - 1}
            step={1}
            value={patternIdx}
            onChange={(ev) => p.setPattern(PATTERNS[Number(ev.target.value)].id)}
            aria-labelledby={qid}
            aria-valuetext={stop.title}
          />
          <div className="pld-wz-stops" aria-hidden="true">
            {PATTERNS.map((s, k) => (
              <span key={s.id} className={k === patternIdx ? 'on' : ''}>
                {s.title}
              </span>
            ))}
          </div>
          <div className="pld-wz-stop-text">
            <b>{stop.title}.</b> {stop.text}
          </div>
        </div>
      )
    }
    return (
      <>
        {cue && (
          <div className="pld-wz-cue" aria-hidden="true">
            {cue}
          </div>
        )}
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
      <div className="pld-wz-stage" ref={stageRef}>
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
          <button type="button" className="pld-btn pld-primary pld-wide" onClick={p.run} disabled={!p.ready || p.busy || !p.enabled}>
            {p.busy ? 'Working it out…' : 'Show my estimate'}
          </button>
        ) : (
          <button type="button" className="pld-btn pld-primary pld-wz-next" onClick={() => go(card + 1)} disabled={!answered[card]}>
            Next
          </button>
        )}
      </div>
      {last && !p.ready && <div className="pld-hint pld-center">{!hasPlace ? 'Pick your town and type the kWh from your bill first.' : 'Type the kWh from your bill first.'}</div>}
    </div>
  )
}

/* ---------- the cues: inline SVG, 800×260, gold on dark; the words carry the meaning, these are aria-hidden ---------- */

const DIAL_LEN = Math.PI * 120
const TICKS = [180, 135, 90, 45, 0]
  .map((a) => {
    const r = (a * Math.PI) / 180
    const c = Math.cos(r)
    const s = Math.sin(r)
    return `M${(400 + 108 * c).toFixed(1)} ${(196 - 108 * s).toFixed(1)}L${(400 + 120 * c).toFixed(1)} ${(196 - 120 * s).toFixed(1)}`
  })
  .join('')

/** Card 3: a meter dial that fills as the number grows, 0–1,000 kWh; past the end it stays full. */
function UseCue({ kwh }: { kwh: number }) {
  const id = useId()
  const useKwh = Number.isFinite(kwh) && kwh > 0
  const frac = useKwh ? Math.min(1, kwh / DIAL_KWH) : 0
  const value = useKwh ? n0(kwh) : ''
  const unit = useKwh ? ' kWh a month' : ''
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

const SUN_RAYS = Array.from({ length: 8 }, (_, k) => {
  const a = (k * Math.PI) / 4
  const c = Math.cos(a)
  const s = Math.sin(a)
  return `M${(28 * c).toFixed(1)} ${(28 * s).toFixed(1)}L${(36 * c).toFixed(1)} ${(36 * s).toFixed(1)}`
}).join('')
const STARS: [number, number, number][] = [[60, 40, 2], [122, 70, 1.5], [300, 30, 1.8], [470, 24, 1.5], [560, 52, 2], [700, 36, 1.5], [775, 80, 1.5], [220, 44, 1.3]]
/** A crescent, 40 units tall, centred on its group's origin. */
const MOON = 'M0-20A20 20 0 1 1 0 20A24 24 0 0 0 0-20Z'

/** A silhouette with its feet at the group's origin: standing, or seated facing right (mirror it to face left). */
function Person({ x, y = 215, pose, scale = 1, when, basket = false }: { x: number; y?: number; pose: 'stand' | 'sit' | 'sit-left'; scale?: number; when: string; basket?: boolean }) {
  const flip = pose === 'sit-left' ? ' scale(-1 1)' : ''
  return (
    <g className={`wz-person ${when}`} transform={`translate(${x} ${y}) scale(${scale})${flip}`}>
      {pose === 'stand' ? (
        <>
          <circle cy="-70" r="8" />
          <rect x="-10" y="-61" width="20" height="36" rx="7" />
          <rect x="-9" y="-26" width="7" height="26" rx="2.5" />
          <rect x="2" y="-26" width="7" height="26" rx="2.5" />
          {basket && <rect className="wz-basket" x="9" y="-38" width="22" height="16" rx="3" />}
        </>
      ) : (
        <>
          <circle cy="-62" r="8" />
          <rect x="-10" y="-53" width="20" height="31" rx="7" />
          <rect x="-8" y="-25" width="25" height="9" rx="4" />
          <rect x="11" y="-20" width="7" height="20" rx="2.5" />
        </>
      )}
    </g>
  )
}

/** Card 4: the house in section and the people in it. Morning: a dawn sky and four of them (table, stove, laundry, a child); all day: daylight and two; evening: dusk, the lamp and the windows on, four around the TV and the table with the fan on. */
function PeopleCue({ pattern }: { pattern: Pattern }) {
  const id = useId()
  return (
    <svg className="pld-wz-svg pld-wz-people" viewBox="0 0 800 260" data-pattern={pattern} focusable="false">
      <defs>
        <clipPath id={`${id}-r`}>
          <rect x="0" y="0" width="800" height="260" rx="14" />
        </clipPath>
        <clipPath id={`${id}-sky`}>
          <rect x="0" y="0" width="800" height="215" />
        </clipPath>
        <linearGradient id={`${id}-dawn`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#24242e" />
          <stop offset="0.55" stopColor="#5a4626" />
          <stop offset="1" stopColor="#b08a2e" />
        </linearGradient>
        <linearGradient id={`${id}-day`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3b3b3a" />
          <stop offset="1" stopColor="#5e5d58" />
        </linearGradient>
        <linearGradient id={`${id}-dusk`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#171b33" />
          <stop offset="1" stopColor="#3b2a3c" />
        </linearGradient>
      </defs>
      <g clipPath={`url(#${id}-r)`}>
        <rect className="wz-bg" x="0" y="0" width="800" height="260" />
        <rect className="wz-sky wz-sky-morning" x="0" y="0" width="800" height="215" fill={`url(#${id}-dawn)`} />
        <rect className="wz-sky wz-sky-day" x="0" y="0" width="800" height="215" fill={`url(#${id}-day)`} />
        <rect className="wz-sky wz-sky-evening" x="0" y="0" width="800" height="215" fill={`url(#${id}-dusk)`} />
        <g className="wz-stars">
          {STARS.map(([x, y, r], i) => (
            <circle key={i} cx={x} cy={y} r={r} />
          ))}
        </g>
        <g clipPath={`url(#${id}-sky)`}>
          <circle className="wz-sun-low" cx="80" cy="216" r="24" />
        </g>
        <g className="wz-sun-high" transform="translate(92 64)">
          <path className="wz-rays" d={SUN_RAYS} />
          <circle r="20" />
        </g>
        <g className="wz-moon" transform="translate(740 56)">
          <path d={MOON} />
        </g>
        <rect className="wz-ground" x="0" y="215" width="800" height="45" />
      </g>
      <line className="wz-horizon" x1="0" y1="215" x2="800" y2="215" />
      {/* the street lamp */}
      <line className="wz-pole" x1="720" y1="215" x2="720" y2="112" />
      <path className="wz-pole" d="M720 124H694" />
      <circle className="wz-lamp-halo" cx="690" cy="127" r="16" />
      <circle className="wz-lamp" cx="690" cy="127" r="5" />
      {/* the house in section: the rooms, the furniture */}
      <rect className="wz-inside" x="160" y="112" width="480" height="103" />
      <rect className="wz-warm" x="160" y="112" width="480" height="103" />
      <path className="wz-roof" d="M140 114L400 50L660 114" />
      <path className="wz-walls" d="M160 215V112H640V215" />
      <line className="wz-part" x1="400" y1="112" x2="400" y2="150" />
      <rect className="wz-win" x="250" y="126" width="46" height="30" />
      <rect className="wz-win" x="452" y="126" width="46" height="30" />
      <path className="wz-furn" d="M166 215V176H230V215" />
      <circle className="wz-burner-on" cx="184" cy="176" r="7" />
      <circle className="wz-burner-on" cx="208" cy="176" r="7" />
      <circle className="wz-furn" cx="184" cy="176" r="5" />
      <circle className="wz-furn" cx="208" cy="176" r="5" />
      <path className="wz-furn" d="M300 180H390M306 180V215M384 180V215M292 215V168M292 192H304M398 215V168M398 192H386" />
      <rect className="wz-sofa" x="428" y="170" width="98" height="45" rx="8" />
      <path className="wz-furn" d="M434 192H520" />
      <path className="wz-furn" d="M552 215V174M540 215H564" />
      <circle className="wz-fan-on" cx="552" cy="160" r="12" />
      <circle className="wz-furn" cx="552" cy="160" r="14" />
      <rect className="wz-tv-on" x="584" y="146" width="48" height="36" />
      <rect className="wz-furn" x="584" y="146" width="48" height="36" rx="2" />
      <path className="wz-furn" d="M608 182V192M594 192H622" />
      {/* the people: more of them in the morning and in the evening */}
      <Person x={290} pose="sit" when="wz-at-morning wz-at-day" />
      <Person x={248} pose="stand" when="wz-at-morning" />
      <Person x={412} pose="stand" when="wz-at-morning" basket />
      <Person x={344} pose="stand" scale={0.6} when="wz-at-morning wz-at-evening" />
      <Person x={450} pose="sit" when="wz-at-day wz-at-evening" />
      <Person x={486} pose="sit" when="wz-at-evening" />
      <Person x={400} pose="sit-left" when="wz-at-evening" />
    </svg>
  )
}
