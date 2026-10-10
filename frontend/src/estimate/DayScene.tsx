// The estimate's day scene: the house, its panels, the inverter, the battery and the grid, built up piece by piece,
// then a typical day one second an hour (24 seconds a day, looping) with the sun's arc, the moon, and dots carrying
// the power between the panels, the house, the battery and the grid. Every figure is the variant's own typical_day
// row; the captions follow the figures, not the clock. Nothing but React; the styles live in estimate.css under
// "the day scene". No controls: the animation runs on its own, pauses off-screen and in a hidden tab, and under
// prefers-reduced-motion (or autoplay={false}) it is one still frame at noon.
import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { TypicalHour, Variant } from './types'

const GOLD = '#C9A227'
const HORIZON = 380            // the ground line, viewBox units
const LIFT = 50                // the house and its ground sit this far below their drawing coordinates (one translated group)
const START_HOUR = 6           // the day runs 06:00 to 05:59
const HOUR_SECONDS = 1         // one second an hour, 24 seconds a day
const SPEED = 140              // a dot's travel, viewBox units per second: one steady speed on every path
const POOL = 60                // dots in the DOM at most; they are recycled
const MIN_KW = 0.05            // under this a flow shows nothing
const KW_PER_DOT = 0.4         // one dot a second per 0.4 kW ...
const MAX_RATE = 8             // ... at most eight a second per path
const PANELS_FROM = 1.1        // the build-up's clock, seconds
const PANELS_TO = 3.5
const SOURCE = { x: 290, y: 208 }   // where the solar stream starts: the middle of the array's bottom edge

type Flow = 'prod' | 'house' | 'charge' | 'discharge' | 'export' | 'import'
const FLOWS: Flow[] = ['prod', 'house', 'charge', 'discharge', 'export', 'import']
/** The wiring. Solar: from the array, along the wall under the eave, down into the inverter's top; from the inverter's
 * side, down the wall beside the window and along it under the windows into the door. Battery: the inverter's bottom to
 * the battery's side. Grid: the inverter's right side, high enough to pass over the battery with clear air (the wire at
 * y 244, the battery's terminal at 255), to the meter and up the service drop to the pole, and back the same way on
 * through the inverter into the house. */
const PATH_D: Record<Flow, string> = {
  prod: `M ${SOURCE.x} ${SOURCE.y - 2} V 221 H 417 V 236`,
  house: 'M 417 272 H 388 V 302 H 270',
  charge: 'M 417 284 V 306 H 478',
  discharge: 'M 478 306 H 417 V 284',
  export: 'M 434 244 H 596 V 240 L 672 174',
  import: 'M 672 174 L 596 240 V 244 H 417 V 272 H 388 V 302 H 270',
}
/** The battery's charge bars, top to bottom; the lit ones fill from the bottom through a clip the state of charge drives. */
const BATT_BARS = [266, 281, 296, 311]
const BATT_BOTTOM = 322, BATT_FULL = 56
const BOLT = 'M 509 272 L 495 297 H 504 L 500 317 L 517 291 H 507 Z'
/** The dots: the sun's power large and bright gold, the battery's gold, the grid's white. */
const FLOW_DOT: Record<Flow, { cls: string; r: number }> = {
  prod: { cls: 'pld-scene-dot-sun', r: 5.5 },
  house: { cls: 'pld-scene-dot-sun', r: 5.5 },
  charge: { cls: 'pld-scene-dot-gold', r: 4 },
  discharge: { cls: 'pld-scene-dot-gold', r: 4 },
  export: { cls: 'pld-scene-dot-grid', r: 4 },
  import: { cls: 'pld-scene-dot-grid', r: 4 },
}
const DASH_COLOR: Record<Flow, string> = { prod: '#ffd54f', house: '#ffd54f', charge: GOLD, discharge: GOLD, export: '#ffffff', import: '#ffffff' }

const ZERO: TypicalHour = { hour: 0, load_kw: 0, production_kw: 0, direct_kw: 0, charge_kw: 0, discharge_kw: 0, soc_kwh: 0, export_kw: 0, import_kw: 0 }
const STARS: [number, number, number][] = [
  [48, 62, 1.6], [112, 34, 1.2], [176, 88, 1.4], [238, 28, 1.1], [318, 74, 1.7], [392, 22, 1.2], [452, 96, 1.3],
  [528, 40, 1.6], [584, 108, 1.1], [642, 30, 1.4], [702, 84, 1.7], [756, 52, 1.2], [96, 150, 1.0], [688, 150, 1.0],
]
const TWINKLE = [0, 4, 7, 10, 13]

type RGB = [number, number, number]
const rgb = (s: string): RGB => [parseInt(s.slice(1, 3), 16), parseInt(s.slice(3, 5), 16), parseInt(s.slice(5, 7), 16)]
const css = (c: RGB) => `rgb(${Math.round(c[0])},${Math.round(c[1])},${Math.round(c[2])})`
const mix = (a: RGB, b: RGB, w: number): RGB => [a[0] + (b[0] - a[0]) * w, a[1] + (b[1] - a[1]) * w, a[2] + (b[2] - a[2]) * w]
const lerp = (a: number, b: number, w: number) => a + (b - a) * w
const clamp01 = (v: number) => Math.max(0, Math.min(1, v))

/** The sky by the sun's height k: -1 deep night, 0 the horizon (dawn and dusk), 1 noon. k is a continuous function of the
 * time, and the colours are interpolated between these stops, so the sky eases through every hour and never steps. */
const SKY: { k: number; top: RGB; bot: RGB; ground: RGB }[] = [
  { k: -1, top: rgb('#070b16'), bot: rgb('#141a2b'), ground: rgb('#121210') },
  { k: -0.35, top: rgb('#141a33'), bot: rgb('#3b3452'), ground: rgb('#151512') },
  { k: 0, top: rgb('#2c2f55'), bot: rgb('#d98a4e'), ground: rgb('#1b1a16') },
  { k: 0.3, top: rgb('#3b6a9e'), bot: rgb('#e8c48f'), ground: rgb('#201f1a') },
  { k: 1, top: rgb('#3e7ebd'), bot: rgb('#bad7ec'), ground: rgb('#22221d') },
]
function skyAt(k: number) {
  let i = 0
  while (i < SKY.length - 2 && k > SKY[i + 1].k) i++
  const a = SKY[i], b = SKY[i + 1]
  const w = clamp01((k - a.k) / (b.k - a.k))
  return { top: css(mix(a.top, b.top, w)), bot: css(mix(a.bot, b.bot, w)), ground: css(mix(a.ground, b.ground, w)) }
}
/** The sun's and the moon's arc: the left horizon at u = 0, the top of the sky at u = 0.5, the right horizon at u = 1.
 * A half ellipse, so the sun climbs clear of the roof in its first hour instead of hiding behind the house. */
const arc = (u: number) => ({ x: 60 + 680 * u, y: HORIZON - (HORIZON - 45) * Math.sqrt(Math.max(0, 1 - (2 * u - 1) ** 2)) })
const SUN_LOW = rgb('#f0a24a'), SUN_HIGH = rgb('#f7dc8a')

/** The roof face: a trapezoid, the ridge narrower than the eaves. Panels follow it, so the rows read in perspective. */
const ROOF = { cx: 290, ridgeY: 122, eaveY: 214, ridgeHalf: 122, eaveHalf: 178 }
const roofHalf = (y: number) => ROOF.ridgeHalf + ((ROOF.eaveHalf - ROOF.ridgeHalf) * (y - ROOF.ridgeY)) / (ROOF.eaveY - ROOF.ridgeY)
const roofX = (f: number, y: number) => ROOF.cx + f * 2 * roofHalf(y)
/** Panel polygons in the order they arrive: rows of up to six, the bottom row first, more panels per row before a fourth row,
 * the panels shrinking to fit so the array is never clipped by the roof. */
function panelPolygons(n: number): string[] {
  if (n <= 0) return []
  let cols = Math.min(6, n)
  let rows = Math.ceil(n / cols)
  while (rows > 3 && cols < 12) {
    cols += 1
    rows = Math.ceil(n / cols)
  }
  const gap = 4, top = 128, bottom = 208
  const ph = Math.min(24, (bottom - top - gap * (rows - 1)) / rows)
  const y0 = bottom - (rows * ph + gap * (rows - 1))
  const budget = 2 * roofHalf(y0) * 0.9
  const pw = Math.min(40, (budget - gap * (cols - 1)) / cols)
  const unit = (pw + gap) / (2 * roofHalf(y0))
  const pwf = pw / (2 * roofHalf(y0))
  const remainder = n - (rows - 1) * cols
  const out: string[] = []
  for (let r = rows - 1; r >= 0; r--) {
    const count = r === 0 ? remainder : cols
    const yT = y0 + r * (ph + gap), yB = yT + ph
    const f0 = -(count * unit - (unit - pwf)) / 2
    for (let i = 0; i < count; i++) {
      const a = f0 + i * unit, b = a + pwf
      out.push(`${roofX(a, yT).toFixed(1)},${yT.toFixed(1)} ${roofX(b, yT).toFixed(1)},${yT.toFixed(1)} ${roofX(b, yB).toFixed(1)},${yB.toFixed(1)} ${roofX(a, yB).toFixed(1)},${yB.toFixed(1)}`)
    }
  }
  return out
}

function normalizeDay(rows: TypicalHour[] | undefined): TypicalHour[] {
  const out: TypicalHour[] = []
  for (let h = 0; h < 24; h++) {
    const r = rows?.find((x) => x.hour === h)
    out.push(r ? { ...ZERO, ...r } : { ...ZERO, hour: h })
  }
  return out
}
/** Sunrise is the first hour with production, sunset the end of the last. */
function sunTimes(day: TypicalHour[]) {
  const lit = day.map((r) => r.production_kw > 0)
  const first = lit.indexOf(true), last = lit.lastIndexOf(true)
  if (first < 0) return { rise: 6, set: 18 }
  return { rise: first, set: Math.min(24, last + 1) }
}
const flowOf = (r: TypicalHour, f: Flow): number =>
  f === 'prod' ? r.production_kw : f === 'house' ? r.direct_kw + r.discharge_kw : f === 'charge' ? r.charge_kw : f === 'discharge' ? r.discharge_kw : f === 'export' ? r.export_kw : r.import_kw
const rateOf = (kw: number) => (kw < MIN_KW ? 0 : Math.min(MAX_RATE, kw / KW_PER_DOT))

const clock = (h: number) => (h === 0 ? '12 MN' : h === 12 ? '12 NN' : h < 12 ? `${h} AM` : `${h - 12} PM`)
const kw = (v: number) => (v >= 10 ? v.toFixed(0) : v.toFixed(1))

type Part = { t: string; b?: boolean }
/** The hour's figures in the customer's words: "Sun 2.8 kW → house 1.1 kW · battery +1.2 kW · to the grid 0.5 kW". */
function readout(r: TypicalHour): Part[] {
  const parts: Part[][] = []
  if (r.production_kw >= MIN_KW) {
    parts.push([{ t: 'Sun ' }, { t: `${kw(r.production_kw)} kW`, b: true }, { t: ' → house ' }, { t: `${kw(r.direct_kw)} kW`, b: true }])
    if (r.charge_kw >= MIN_KW) parts.push([{ t: 'battery ' }, { t: `+${kw(r.charge_kw)} kW`, b: true }])
    if (r.export_kw >= MIN_KW) parts.push([{ t: 'to the grid ' }, { t: `${kw(r.export_kw)} kW`, b: true }])
    if (r.discharge_kw >= MIN_KW) parts.push([{ t: 'battery ' }, { t: `${kw(r.discharge_kw)} kW`, b: true }, { t: ' → house' }])
    if (r.import_kw >= MIN_KW) parts.push([{ t: 'grid ' }, { t: `${kw(r.import_kw)} kW`, b: true }, { t: ' → house' }])
  } else {
    if (r.discharge_kw >= MIN_KW) parts.push([{ t: 'Battery ' }, { t: `${kw(r.discharge_kw)} kW`, b: true }, { t: ' → house' }])
    if (r.import_kw >= MIN_KW) parts.push(parts.length ? [{ t: 'grid ' }, { t: `${kw(r.import_kw)} kW`, b: true }] : [{ t: 'Grid ' }, { t: `${kw(r.import_kw)} kW`, b: true }, { t: ' → house' }])
    if (!parts.length) parts.push([{ t: 'House ' }, { t: `${kw(r.load_kw)} kW`, b: true }])
  }
  return parts.flatMap((p, i) => (i ? [{ t: ' · ' }, ...p] : p))
}
/** One line per phase, read off the row: the family's day, with what the sun, the battery and the grid are doing in that hour. */
function caption(day: TypicalHour[], h: number, hasBattery: boolean): string {
  const r = day[h], next = day[(h + 1) % 24]
  const loads = day.map((x) => x.load_kw)
  const minLoad = Math.min(...loads), maxLoad = Math.max(...loads)
  const maxSoc = Math.max(...day.map((x) => x.soc_kwh))
  const sunUp = r.production_kw >= MIN_KW
  if (sunUp && r.direct_kw >= r.load_kw - MIN_KW) {
    const charging = r.charge_kw >= MIN_KW, exporting = r.export_kw >= MIN_KW
    if (charging && exporting) return "The house runs on the sun; the extra fills tonight's battery, and the rest goes back through the meter as credit."
    if (charging) return "The house runs on the sun; the extra fills tonight's battery."
    if (exporting) return 'The house runs on the sun; the extra goes back through the meter as credit.'
    if (hasBattery && maxSoc > 0 && r.soc_kwh >= 0.97 * maxSoc && r.production_kw > r.load_kw + MIN_KW) return 'The house runs on the sun; the battery is full for tonight.'
    return 'The house runs on the sun.'
  }
  if (sunUp) {
    if (next.production_kw > r.production_kw) return 'The sun is up and the panels are starting to carry the house.'
    return r.discharge_kw >= MIN_KW ? 'The sun goes down and the battery takes over.' : 'The sun goes down and the grid takes over, as it does today.'
  }
  const flat = maxLoad < 1.2 * minLoad
  // before dawn is night whatever the load (a morning house is already cooking at 5 AM)
  const night = h < 6 || (flat ? h >= 22 : r.load_kw <= minLoad * 1.35)
  const onBattery = r.discharge_kw >= MIN_KW
  if (night) return onBattery ? 'Everyone asleep, the fridge on the battery.' : 'Everyone asleep, the fridge on the grid.'
  // the battery alone, or the battery with the grid topping up the hours it cannot carry
  if (onBattery) return r.import_kw >= MIN_KW ? 'The battery carries the evening as far as it goes; the grid tops up the rest.' : 'The battery carries the evening on your own power: the lights, the fan, the TV, the Wi-Fi.'
  // a house without a battery spends its evening on the grid as it does now; where the day sent power back, the evening was paid for in credit
  const exported = day.some((x) => x.export_kw >= MIN_KW)
  return exported ? "The evening runs on the grid, as it does today; the day's extra came back as credit." : 'The evening runs on the grid, as it does today.'
}

function prefersReduced(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

type Dot = { flow: number; s: number }
type Phase = 'build' | 'day'

export default function DayScene({ variant, autoplay = true }: { variant: Variant; autoplay?: boolean }) {
  const sys = variant.system
  const hasBattery = sys.battery_kwh > 0
  const usable = sys.battery_usable_kwh > 0 ? sys.battery_usable_kwh : sys.battery_kwh
  const day = useMemo(() => normalizeDay(variant.production?.typical_day), [variant])
  const sun = useMemo(() => sunTimes(day), [day])
  const polys = useMemo(() => panelPolygons(sys.panels), [sys.panels])
  const gridLabel = variant.goal === 'off_grid' ? 'grid as backup' : 'net metering'
  // the build-up's clock: the house, the panels, the inverter, the battery (skipped without one), the meter, done
  const marks = useMemo(() => (hasBattery ? [0, PANELS_FROM, 3.9, 4.9, 5.9, 7.0] : [0, PANELS_FROM, 3.9, 4.9, 4.9, 6.0]), [hasBattery])

  const [reduced, setReduced] = useState(prefersReduced)
  const isStatic = reduced || !autoplay
  const running = !isStatic   // the loop runs on its own; a still noon frame otherwise
  const [phase, setPhase] = useState<Phase>(isStatic ? 'day' : 'build')
  const [step, setStep] = useState(isStatic ? 6 : 0)
  const [panelsShown, setPanelsShown] = useState(isStatic ? sys.panels : 0)
  const [hour, setHour] = useState(isStatic ? 12 : START_HOUR)

  const rootRef = useRef<HTMLDivElement>(null)
  const phaseRef = useRef<Phase>(isStatic ? 'day' : 'build')
  const buildTRef = useRef(0)
  const timeRef = useRef(isStatic ? 12 : START_HOUR)   // hours, 6 … 29.999
  const stepRef = useRef(step)
  const panelsRef = useRef(panelsShown)
  const hourRef = useRef(hour)
  const lastTsRef = useRef(0)
  const dotsRef = useRef<Dot[]>(Array.from({ length: POOL }, () => ({ flow: -1, s: 0 })))
  const accRef = useRef<number[]>(FLOWS.map(() => 0))
  const lensRef = useRef<number[]>(FLOWS.map(() => 0))
  const dotEls = useRef<(SVGCircleElement | null)[]>([])
  const pathEls = useRef<(SVGPathElement | null)[]>([])
  const starEls = useRef<(SVGCircleElement | null)[]>([])
  const skyTop = useRef<SVGStopElement>(null)
  const skyBot = useRef<SVGStopElement>(null)
  const groundRef = useRef<SVGRectElement>(null)
  const shadeRef = useRef<SVGRectElement>(null)
  const sunGlow = useRef<SVGCircleElement>(null)
  const sunDisc = useRef<SVGCircleElement>(null)
  const moonG = useRef<SVGGElement>(null)
  const moonDisc = useRef<SVGCircleElement>(null)
  const moonShade = useRef<SVGCircleElement>(null)
  const starsG = useRef<SVGGElement>(null)
  const lightsG = useRef<SVGGElement>(null)
  const battFill = useRef<SVGRectElement>(null)

  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const skyId = `pld-sky-${uid}`, glowId = `pld-glow-${uid}`, shadeId = `pld-shade-${uid}`, clipId = `pld-batt-${uid}`

  function clearDots() {
    for (let i = 0; i < POOL; i++) {
      dotsRef.current[i].flow = -1
      dotEls.current[i]?.setAttribute('opacity', '0')
    }
    accRef.current.fill(0.9)   // nearly due, so an active flow shows its first dot right after a start
  }

  /** Paints the sky, the sun or the moon, the battery's level and (while running) the dots for the time T, in hours from 6 to 30. */
  function paint(T: number, dt: number, now: number, withDots: boolean) {
    const t24 = T >= 24 ? T - 24 : T
    const dayLen = Math.max(0.5, sun.set - sun.rise), nightLen = 24 - dayLen
    const isDay = t24 >= sun.rise && t24 < sun.set
    let k: number, sunU = -1, moonU = -1
    if (isDay) {
      sunU = (t24 - sun.rise) / dayLen
      k = Math.sin(Math.PI * sunU)
    } else {
      const since = t24 >= sun.set ? t24 - sun.set : t24 + 24 - sun.set
      const until = Math.max(0, nightLen - since)
      k = -Math.min(1, Math.min(since, until) / 1.5)
      moonU = nightLen > 0 ? since / nightLen : 0
    }
    const night = clamp01(-k)
    const sky = skyAt(k)
    skyTop.current?.setAttribute('stop-color', sky.top)
    skyBot.current?.setAttribute('stop-color', sky.bot)
    groundRef.current?.setAttribute('fill', sky.ground)
    shadeRef.current?.setAttribute('opacity', (0.45 * night).toFixed(3))
    if (sunU >= 0) {
      const p = arc(sunU)
      const warm = clamp01(Math.sin(Math.PI * sunU) * 2.2)
      const show = clamp01(Math.min(sunU, 1 - sunU) / 0.04)   // eased in and out at the horizon, so it never pops
      for (const el of [sunGlow.current, sunDisc.current]) {
        el?.setAttribute('cx', p.x.toFixed(1))
        el?.setAttribute('cy', p.y.toFixed(1))
        el?.setAttribute('opacity', show.toFixed(2))
      }
      sunDisc.current?.setAttribute('fill', css(mix(SUN_LOW, SUN_HIGH, warm)))
    } else {
      sunGlow.current?.setAttribute('opacity', '0')
      sunDisc.current?.setAttribute('opacity', '0')
    }
    if (moonU >= 0) {
      const p = arc(moonU)
      moonDisc.current?.setAttribute('cx', p.x.toFixed(1))
      moonDisc.current?.setAttribute('cy', p.y.toFixed(1))
      moonShade.current?.setAttribute('cx', (p.x - 6).toFixed(1))
      moonShade.current?.setAttribute('cy', (p.y - 4).toFixed(1))
      moonShade.current?.setAttribute('fill', sky.top)
      moonG.current?.setAttribute('opacity', clamp01(night * 1.4).toFixed(3))
    } else moonG.current?.setAttribute('opacity', '0')
    starsG.current?.setAttribute('opacity', night.toFixed(3))
    TWINKLE.forEach((i, j) => starEls.current[i]?.setAttribute('opacity', (0.55 + 0.45 * Math.sin(now / 700 + j * 1.7)).toFixed(2)))
    lightsG.current?.setAttribute('opacity', (0.5 + 0.5 * night).toFixed(3))
    if (hasBattery && usable > 0 && battFill.current) {
      const h = Math.floor(t24) % 24, frac = t24 - Math.floor(t24)
      const soc = lerp(day[(h + 23) % 24].soc_kwh, day[h].soc_kwh, frac)
      const level = clamp01(soc / usable)
      const hgt = Math.max(1, BATT_FULL * level)   // the clip over the lit bars: they fill from the bottom with the charge
      battFill.current.setAttribute('y', (BATT_BOTTOM - hgt).toFixed(1))
      battFill.current.setAttribute('height', hgt.toFixed(1))
    }
    if (!withDots || dt <= 0) return
    // the flows at T: the row's figure sits at the middle of its hour and eases to the neighbours, so the stream never jumps
    const h = Math.floor(t24) % 24, frac = t24 - Math.floor(t24)
    const a = frac < 0.5 ? day[(h + 23) % 24] : day[h]
    const b = frac < 0.5 ? day[h] : day[(h + 1) % 24]
    const w = frac < 0.5 ? frac + 0.5 : frac - 0.5
    const dots = dotsRef.current, acc = accRef.current, lens = lensRef.current
    for (let f = 0; f < FLOWS.length; f++) {
      const el = pathEls.current[f]
      if (!el) continue
      if (!lens[f]) lens[f] = el.getTotalLength()
      const rate = rateOf(lerp(flowOf(a, FLOWS[f]), flowOf(b, FLOWS[f]), w))
      if (rate === 0) {
        acc[f] = 0
        continue
      }
      acc[f] += rate * dt
      while (acc[f] >= 1) {
        acc[f] -= 1
        const free = dots.findIndex((d) => d.flow < 0)
        if (free < 0) {
          acc[f] = 0
          break
        }
        dots[free].flow = f
        dots[free].s = 0
        const look = FLOW_DOT[FLOWS[f]]
        dotEls.current[free]?.setAttribute('class', look.cls)
        dotEls.current[free]?.setAttribute('r', String(look.r))
      }
    }
    for (let i = 0; i < POOL; i++) {
      const d = dots[i]
      if (d.flow < 0) continue
      const el = dotEls.current[i], path = pathEls.current[d.flow]
      const L = lens[d.flow]
      d.s += SPEED * dt
      if (!el || !path || d.s >= L) {
        d.flow = -1
        el?.setAttribute('opacity', '0')
        continue
      }
      const p = path.getPointAtLength(d.s)
      el.setAttribute('cx', p.x.toFixed(1))
      el.setAttribute('cy', p.y.toFixed(1))
      el.setAttribute('opacity', Math.min(1, d.s / 14, (L - d.s) / 14).toFixed(2))
    }
  }
  const stepAt = (t: number) => {
    let s = 0
    while (s < marks.length && t >= marks[s]) s++
    return s
  }
  const panelsAt = (t: number, s: number) => (s < 2 ? 0 : s > 2 ? sys.panels : Math.max(1, Math.min(sys.panels, 1 + Math.floor(((t - PANELS_FROM) / (PANELS_TO - PANELS_FROM)) * sys.panels))))
  // the frame loop reads the latest of these through one ref, refreshed after every render
  const latest = useRef({ paint, marks, stepAt, panelsAt })
  useEffect(() => {
    latest.current = { paint, marks, stepAt, panelsAt }
  })

  // the reduced-motion setting can change while the page is open
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = () => setReduced(mq.matches)
    mq.addEventListener?.('change', onChange)
    return () => mq.removeEventListener?.('change', onChange)
  }, [])

  // the animation loop: requestAnimationFrame only, off while off-screen or in a hidden tab, and on again after
  useEffect(() => {
    if (!running) return
    const root = rootRef.current
    let raf = 0
    let visible = true
    clearDots()
    lastTsRef.current = 0
    const frame = (ts: number) => {
      raf = requestAnimationFrame(frame)
      const last = lastTsRef.current
      lastTsRef.current = ts
      const dt = last ? Math.min(0.1, (ts - last) / 1000) : 0
      if (phaseRef.current === 'build') {
        buildTRef.current += dt
        const t = buildTRef.current
        const s = latest.current.stepAt(t)
        if (s !== stepRef.current) {
          stepRef.current = s
          setStep(s)
        }
        const p = latest.current.panelsAt(t, s)
        if (p !== panelsRef.current) {
          panelsRef.current = p
          setPanelsShown(p)
        }
        const m = latest.current.marks
        if (t >= m[m.length - 1]) {
          phaseRef.current = 'day'
          setPhase('day')
          timeRef.current = START_HOUR
        }
        latest.current.paint(START_HOUR, 0, ts, false)
        return
      }
      let T = timeRef.current + dt / HOUR_SECONDS
      if (T >= START_HOUR + 24) T -= 24
      timeRef.current = T
      const h = Math.floor(T) % 24
      if (h !== hourRef.current) {
        hourRef.current = h
        setHour(h)
      }
      latest.current.paint(T, dt, ts, true)
    }
    const start = () => {
      if (raf || !visible || document.hidden) return
      lastTsRef.current = 0
      raf = requestAnimationFrame(frame)
    }
    const stop = () => {
      if (raf) cancelAnimationFrame(raf)
      raf = 0
    }
    const onVisibility = () => (document.hidden ? stop() : start())
    document.addEventListener('visibilitychange', onVisibility)
    let io: IntersectionObserver | null = null
    if (root && typeof IntersectionObserver !== 'undefined') {
      io = new IntersectionObserver(
        (entries) => {
          visible = entries.some((e) => e.isIntersecting)
          if (visible) start()
          else stop()
        },
        { threshold: 0.05 },
      )
      io.observe(root)
    }
    start()
    return () => {
      stop()
      io?.disconnect()
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [running, variant])

  // the still frame: noon, every piece drawn, and it follows a change of variant
  useEffect(() => {
    if (running) return
    clearDots()
    latest.current.paint(timeRef.current, 0, 0, false)
  }, [running, variant])

  const row = day[hour]
  const parts = readout(row)
  const cap = caption(day, hour, hasBattery)
  const progressAt = (hour - START_HOUR + 24) % 24
  const building = phase === 'build'
  const panelWord = panelsShown === 1 ? 'panel' : 'panels'
  const ariaLabel =
    `${sys.panels} panel${sys.panels === 1 ? '' : 's'} on the roof, an inverter` +
    (hasBattery ? ', a battery' : '') +
    ` and the meter with ${gridLabel}: an ordinary day, the sun up from ${clock(sun.rise)} to ${clock(sun.set % 24)}, the power flowing between the panels, the house${hasBattery ? ', the battery' : ''} and the grid.`
  const live = (f: Flow) => !building && flowOf(row, f) >= MIN_KW
  const dashOpacity = (f: Flow) => {
    const v = flowOf(row, f)
    return v < MIN_KW ? 0 : 0.35 + 0.65 * clamp01(v / 3)
  }
  const sunOn = live('prod')
  const pulseLevel = 0.55 + 0.45 * clamp01(row.production_kw / 3)
  const on = (yes: boolean) => (yes ? ' on' : '')

  return (
    <div className="pld-scene" ref={rootRef}>
      <svg className="pld-scene-svg" viewBox="0 0 800 450" role="img" aria-label={ariaLabel} focusable="false">
        <defs>
          <linearGradient id={skyId} x1="0" y1="0" x2="0" y2="1">
            <stop ref={skyTop} offset="0" stopColor="#2c2f55" />
            <stop ref={skyBot} offset="1" stopColor="#d98a4e" />
          </linearGradient>
          <radialGradient id={glowId}>
            <stop offset="0" stopColor="#f6d77c" stopOpacity="0.85" />
            <stop offset="0.45" stopColor="#f0c860" stopOpacity="0.28" />
            <stop offset="1" stopColor="#f0c860" stopOpacity="0" />
          </radialGradient>
          <linearGradient id={shadeId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#050812" stopOpacity="0" />
            <stop offset="0.4" stopColor="#050812" stopOpacity="0.7" />
            <stop offset="1" stopColor="#050812" stopOpacity="1" />
          </linearGradient>
          <clipPath id={clipId}>
            <rect ref={battFill} x="478" y={BATT_BOTTOM - 1} width="56" height="1" />
          </clipPath>
        </defs>
        <rect x="0" y="0" width="800" height="450" fill={`url(#${skyId})`} />
        <g ref={starsG} opacity="0" fill="#eef0f6">
          {STARS.map(([x, y, r], i) => (
            <circle key={i} cx={x} cy={y} r={r} ref={(el) => { starEls.current[i] = el }} />
          ))}
        </g>
        <circle ref={sunGlow} cx="60" cy={HORIZON} r="58" fill={`url(#${glowId})`} opacity="0" />
        <circle ref={sunDisc} cx="60" cy={HORIZON} r="20" fill="#f0a24a" opacity="0" />
        <g ref={moonG} opacity="0">
          <circle ref={moonDisc} cx="740" cy={HORIZON} r="14" fill="#e6e8ef" />
          <circle ref={moonShade} cx="734" cy={HORIZON - 4} r="12" fill="#070b16" />
        </g>
        <rect ref={groundRef} x="0" y={HORIZON} width="800" height={450 - HORIZON} fill="#1b1a16" />
        <line x1="0" y1={HORIZON} x2="800" y2={HORIZON} stroke="rgba(255,255,255,0.14)" strokeWidth="1.5" />

        {/* everything that stands on the ground is drawn against a ground line at 330 and lifted down to the horizon as one */}
        <g transform={`translate(0 ${LIFT})`}>
          {/* the grid: the pole, its wires, the meter on its post */}
          <g className={'pld-scene-piece' + on(step >= 5)}>
            <path d="M 672 168 L 800 148 M 728 168 L 800 141" fill="none" stroke="#8a8a84" strokeWidth="1.2" />
            <line x1="672" y1="174" x2="596" y2="240" stroke="#8a8a84" strokeWidth="1.2" />
            <rect x="696" y="150" width="8" height={330 - 150} fill="#5a4a3a" />
            <rect x="666" y="168" width="68" height="5" fill="#5a4a3a" />
            <rect x="669" y="162" width="6" height="7" fill="#9a9a92" />
            <rect x="697" y="162" width="6" height="7" fill="#9a9a92" />
            <rect x="725" y="162" width="6" height="7" fill="#9a9a92" />
            <rect x="594" y="272" width="4" height={330 - 272} fill="#6a6a64" />
            <rect x="580" y="240" width="32" height="32" rx="3" fill="#e9e9e4" stroke="#6a6a64" strokeWidth="1" />
            <circle cx="596" cy="253" r="7.5" fill="#fff" stroke="#6a6a64" strokeWidth="1" />
            <line x1="596" y1="253" x2="600" y2="248" stroke="#9b1c1c" strokeWidth="1.2" />
            <rect x="586" y="263" width="20" height="5" fill="#333" />
            <rect className="pld-scene-flash" x="576" y="236" width="40" height="40" rx="5" />
          </g>

          {/* the house: drawn in, then filled */}
          <path className={'pld-scene-outline' + on(step >= 1)} d="M 130 330 V 210 L 112 214 L 168 122 H 412 L 468 214 L 450 210 V 330 Z" pathLength={1} />
          <g className={'pld-scene-house' + on(step >= 1)}>
            <rect x="130" y="210" width="320" height={330 - 210} fill="#e8dcc0" stroke="#5b4a33" strokeWidth="1.5" />
            <polygon points="112,214 168,122 412,122 468,214" fill="#4a3b30" stroke="#2b2118" strokeWidth="1.5" />
            <line x1="112" y1="214" x2="468" y2="214" stroke="#2b2118" strokeWidth="2.5" />
            <rect x="248" y="262" width="44" height="68" fill="#8a5a2b" stroke="#5b3a1a" strokeWidth="1.2" />
            <circle cx="284" cy="298" r="2.2" fill={GOLD} />
            <rect x="160" y="244" width="56" height="44" fill="#3a3a40" stroke="#5b4a33" strokeWidth="1.5" />
            <rect x="318" y="244" width="56" height="44" fill="#3a3a40" stroke="#5b4a33" strokeWidth="1.5" />
          </g>
          <g className={'pld-scene-panels' + on(sunOn)}>
            {polys.map((pts, i) => (
              <g key={i} className={'pld-scene-panel' + on(i < panelsShown)}>
                <polygon points={pts} />
              </g>
            ))}
          </g>

          {/* the inverter on the wall with the solar conduits, the battery beside the house */}
          <g className={'pld-scene-piece' + on(step >= 3)}>
            <path d={PATH_D.prod} className="pld-scene-duct" />
            <path d={PATH_D.house} className="pld-scene-duct" />
            <rect x="400" y="236" width="34" height="48" rx="3" fill="#2a2a2e" stroke="#9a9a92" strokeWidth="1" />
            <rect x="407" y="244" width="20" height="10" rx="1" fill="#44484f" />
            <line x1="407" y1="260" x2="427" y2="260" stroke="#55555c" strokeWidth="1" />
            <line x1="407" y1="264" x2="427" y2="264" stroke="#55555c" strokeWidth="1" />
            <circle cx="417" cy="275" r="2.5" fill={GOLD} />
            <rect className="pld-scene-flash" x="396" y="232" width="42" height="56" rx="5" />
          </g>
          {hasBattery && (
            <g className={'pld-scene-piece' + on(step >= 4)}>
              {/* a battery at a glance: the cell silhouette with its terminal, a light face, four charge bars that fill from
                  the bottom with the state of charge, a gold bolt, and a gold outline while it charges or discharges */}
              <path d={PATH_D.charge} className="pld-scene-wire" />
              <rect className={'pld-scene-batt-glow' + on(live('charge') || live('discharge'))} x="474" y="251" width="64" height="83" rx="8" />
              <rect data-part="battery-nub" x="496" y="255" width="20" height="6" rx="1.5" fill="#3a3a40" />
              <rect data-part="battery-body" x="478" y="261" width="56" height={330 - 261} rx="5" fill="#d9d5ca" stroke="#2a2a2e" strokeWidth="1.5" />
              <g fill="#b9b5aa">
                {BATT_BARS.map((y) => (
                  <rect key={y} x="484" y={y} width="44" height="11" rx="1.5" />
                ))}
              </g>
              <g fill={GOLD} clipPath={`url(#${clipId})`}>
                {BATT_BARS.map((y) => (
                  <rect key={y} x="484" y={y} width="44" height="11" rx="1.5" />
                ))}
              </g>
              <path d={BOLT} fill="#ffd54f" stroke="#2a2a2e" strokeWidth="1.2" strokeLinejoin="round" />
              <rect className="pld-scene-flash" x="473" y="249" width="66" height="86" rx="7" />
            </g>
          )}
          <g className={'pld-scene-piece' + on(step >= 5)}>
            <path d={PATH_D.export} className="pld-scene-wire" />
          </g>

          {/* night falls on the house and the ground; the windows stay lit above it */}
          <rect ref={shadeRef} x="0" y={-LIFT} width="800" height="450" fill={`url(#${shadeId})`} opacity="0" />
          <g ref={lightsG} className={'pld-scene-house' + on(step >= 1)} opacity="0.5">
            <rect x="161" y="245" width="54" height="42" fill="#ffd27a" />
            <rect x="319" y="245" width="54" height="42" fill="#ffd27a" />
            <path d="M 188 245 V 287 M 161 266 H 215 M 346 245 V 287 M 319 266 H 373" stroke="#5b4a33" strokeWidth="1.5" fill="none" />
          </g>

          {/* the source: a soft gold pulse where the solar stream leaves the array, while the panels produce */}
          <circle className={'pld-scene-pulse' + on(sunOn)} cx={SOURCE.x} cy={SOURCE.y} r="22" fill={`url(#${glowId})`} style={{ opacity: sunOn ? pulseLevel : 0 }} />

          {/* the wiring measured for the dots (the two reversed runs are invisible), the still dashes, the dots */}
          <g opacity="0">
            {FLOWS.map((f, i) => (
              <path key={f} d={PATH_D[f]} fill="none" stroke="none" ref={(el) => { pathEls.current[i] = el }} />
            ))}
          </g>
          <g className={'pld-scene-dashes' + on(!running && step >= 6)}>
            {FLOWS.map((f) => (
              <path key={f} d={PATH_D[f]} className="pld-scene-dash" stroke={DASH_COLOR[f]} style={{ opacity: dashOpacity(f) }} />
            ))}
          </g>
          <g className={'pld-scene-dots' + on(running)}>
            {Array.from({ length: POOL }, (_, i) => (
              <circle key={i} r="4" opacity="0" ref={(el) => { dotEls.current[i] = el }} />
            ))}
          </g>

          {/* the flow's words at the path ends, fading with the flow (the readout carries them on a phone) */}
          <text className={'pld-scene-flow' + on(sunOn)} x={SOURCE.x} y="237" textAnchor="middle" fill="#3a3028">from the panels</text>
          <text className={'pld-scene-flow' + on(live('house') || live('import'))} x="238" y="318" textAnchor="end" fill="#3a3028">to the house</text>
          <text className={'pld-scene-flow' + on(live('export') || live('import'))} x="650" y="374" textAnchor="middle" fill="#d8d8d2">{live('import') && !live('export') ? 'from the grid' : 'to the grid'}</text>

          {/* labels (the chips under the scene carry them on a phone) */}
          <g className={'pld-scene-counter' + on(building && step >= 2)}>
            <rect x="125" y="62" width="330" height="44" rx="10" fill="#111111" opacity="0.84" />
            <text x="290" y="92" textAnchor="middle" fontSize="26" fontWeight="700" fill="#ffffff">
              <tspan fill={GOLD}>{panelsShown}</tspan> {panelWord}
            </text>
          </g>
          <text className={'pld-scene-lbl' + on(step >= 3)} x="417" y="352" textAnchor="middle">inverter</text>
          {hasBattery && <text className={'pld-scene-lbl' + on(step >= 4)} x="506" y="374" textAnchor="middle">battery</text>}
          <text className={'pld-scene-lbl' + on(step >= 5)} x="650" y="352" textAnchor="middle">{gridLabel}</text>
        </g>

        {/* the clock and the 24-step progress line */}
        <g className={'pld-scene-clock' + on(!building)}>
          {Array.from({ length: 24 }, (_, i) => (
            <rect key={i} x={(i * 800) / 24 + 1.5} y="6" width={800 / 24 - 3} height="4" rx="1" fill={i <= progressAt ? GOLD : '#ffffff'} opacity={i <= progressAt ? 0.95 : 0.22} />
          ))}
          <rect x="16" y="20" width="150" height="44" rx="10" fill="#111111" opacity="0.8" />
          <text x="91" y="52" textAnchor="middle" fontSize="32" fontWeight="700" fill="#ffffff">{clock(hour)}</text>
        </g>
      </svg>

      <div className="pld-scene-strip">
        {building ? (
          <>
            <div className="pld-scene-read"><b className="pld-scene-hour">Dawn</b> · your house, fitted out piece by piece</div>
            <p className="pld-scene-cap">Then an ordinary day, hour by hour.</p>
          </>
        ) : (
          <>
            <div className="pld-scene-read">
              <b className="pld-scene-hour">{clock(hour)}</b> · {parts.map((p, i) => (p.b ? <b key={i}>{p.t}</b> : <span key={i}>{p.t}</span>))}
            </div>
            <p className="pld-scene-cap">{cap}</p>
          </>
        )}
      </div>
      <div className="pld-scene-chips">
        <span className={'pld-scene-chip' + on(step >= 2)}><b>{panelsShown}</b> {panelWord}</span>
        <span className={'pld-scene-chip' + on(step >= 3)}>inverter</span>
        {hasBattery && <span className={'pld-scene-chip' + on(step >= 4)}>battery</span>}
        <span className={'pld-scene-chip' + on(step >= 5)}>{gridLabel}</span>
      </div>
    </div>
  )
}
