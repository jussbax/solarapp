import { fmtDate, fmtDateShort } from '../fmt'
import type { GanttEvent } from '../types'

/** The program of works as a bar chart: one row per schedule event, a bar from its date to its end, milestones as black
 * diamonds and payments as hollow gold diamonds, weeks ticked on the top axis, today marked when it falls in the range.
 * Under 640 px the chart keeps its width and scrolls sideways, with a hint. Pure: no fetches, no state. */

const INK = '#111111'
const GRAY = '#2D2D2D'
const MUTED = '#6b6b66'
const LINE = '#e2e2dc'
const GOLD_DARK = '#a4841c'
const OFF_WHITE = '#F5F5F3'
const PANEL_FILL = '#E9DAA9'
const MIN_WIDTH = 640

export interface GanttProps {
  events: GanttEvent[]
  /** ISO date; marked when it falls inside the schedule. */
  today?: string | null
  /** Width in px of the space available; under 640 the chart is 640 wide and scrolls. */
  width?: number
}

const dayIndex = (iso: string) => {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return Math.floor(Date.UTC(y, m - 1, d) / 86400000)
}
const isoDay = (i: number) => new Date(i * 86400000).toISOString().slice(0, 10)
const fmtDay = (i: number) => fmtDateShort(isoDay(i))
const fmtDayYear = (i: number) => fmtDate(isoDay(i))
/** 0 = Monday (day index 0 is Thursday, 1 January 1970). */
const weekday = (i: number) => (((i + 3) % 7) + 7) % 7
const php0 = (v: number) => `₱${Math.round(v).toLocaleString()}`

function Diamond({ cx, cy, r, hollow }: { cx: number; cy: number; r: number; hollow?: boolean }) {
  const d = `${cx - r},${cy} ${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r}`
  return hollow ? <polygon points={d} fill="#ffffff" stroke={GOLD_DARK} strokeWidth={2} /> : <polygon points={d} fill={INK} stroke="#ffffff" strokeWidth={1} />
}

export function Gantt({ events, today, width = 900 }: GanttProps) {
  const evs = (events ?? []).filter((e) => e.date)
  if (evs.length === 0) return <div className="muted">No schedule yet.</div>
  const narrow = width < MIN_WIDTH
  const W = narrow ? MIN_WIDTH : width
  const labelW = narrow ? Math.min(250, Math.round(W * 0.34)) : Math.min(320, Math.round(W * 0.4))
  const axisH = 32
  const legendH = 28
  const starts = evs.map((e) => dayIndex(e.date))
  const ends = evs.map((e, i) => (e.end ? Math.max(dayIndex(e.end), starts[i]) : starts[i]))
  let d0 = Math.min(...starts)
  d0 -= weekday(d0) // the Monday on or before the first event
  let d1 = Math.max(...ends) + 1
  d1 += (7 - weekday(d1)) % 7 // the Monday after the last event
  const days = Math.max(d1 - d0, 7)
  const x0 = labelW + 10
  const x1 = W - 10
  const px = (x1 - x0) / days
  const X = (i: number) => x0 + (i - d0) * px
  const weeks: number[] = []
  for (let k = 0; k <= days; k += 7) weeks.push(d0 + k)
  const every = px * 7 >= 48 ? 1 : 2
  const maxChars = Math.max(12, Math.floor((labelW - 8) / 6.6))
  // a label that does not fit wraps onto a second line (never cut with an ellipsis); its row grows to hold both
  const wrap = (text: string): string[] => {
    if (text.length <= maxChars) return [text]
    const words = text.split(' ')
    const first: string[] = []
    while (words.length && (first.join(' ') + ' ' + words[0]).trim().length <= maxChars) first.push(words.shift()!)
    if (first.length === 0) first.push(words.shift()!)
    return [first.join(' '), words.join(' ')].filter(Boolean)
  }
  const labels = evs.map((e) => wrap(e.label + (e.amount ? ` ${php0(e.amount)}` : '')))
  const rowHs = labels.map((l) => (l.length > 1 ? 38 : 26))
  const rowTops: number[] = []
  let yAcc = axisH
  for (const h of rowHs) {
    rowTops.push(yAcc)
    yAcc += h
  }
  const H = yAcc + legendH
  const t = today ? dayIndex(today) : null
  const todayIn = t != null && t >= d0 && t < d1

  const chart = (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Schedule: ${evs.length} events from ${fmtDayYear(starts[0])}`} style={{ display: 'block', fontFamily: 'inherit' }}>
      <text x={6} y={12} fontSize={11} fill={MUTED}>
        Weeks from {fmtDayYear(d0)}
      </text>
      <line x1={x0} y1={axisH} x2={x1} y2={axisH} stroke={LINE} strokeWidth={1} />
      {weeks.map((wk, k) => (
        <g key={wk}>
          <line x1={X(wk)} y1={axisH} x2={X(wk)} y2={H - legendH} stroke={LINE} strokeWidth={1} />
          {k % every === 0 && wk < d1 && (
            <text x={X(wk) + 3} y={axisH - 5} fontSize={11} fill={MUTED}>
              {fmtDay(wk)}
            </text>
          )}
        </g>
      ))}
      {evs.map((e, i) => {
        const rowH = rowHs[i]
        const yTop = rowTops[i]
        const yMid = yTop + rowH / 2
        const s = starts[i]
        const en = ends[i]
        const kind = e.kind ?? 'task'
        const label = labels[i].join(' ')
        let when: string
        let right: number
        let mark
        if (kind === 'task') {
          const xa = X(s)
          const xb = Math.max(X(en + 1), xa + 4)
          mark = <rect x={xa} y={yMid - 7} width={xb - xa} height={14} rx={3} fill={PANEL_FILL} stroke={GOLD_DARK} strokeWidth={1} />
          when = en === s ? fmtDay(s) : `${fmtDay(s)} to ${fmtDay(en)}`
          right = xb
        } else {
          const cx = X(s) + px / 2
          mark = <Diamond cx={cx} cy={yMid} r={7} hollow={kind === 'payment_in'} />
          when = fmtDay(s)
          right = cx + 7
        }
        const whenW = when.length * 6.2
        const fits = right + 6 + whenW <= x1
        const title = `${label}: ${when}${kind === 'milestone' ? ' (milestone)' : kind === 'payment_in' ? ' (payment from the customer)' : ''}`
        return (
          <g key={`${e.key ?? ''}-${i}`}>
            {i % 2 === 1 && <rect x={0} y={yTop} width={W} height={rowH} fill={OFF_WHITE} />}
            <text x={6} y={yMid} dominantBaseline="central" fontSize={12} fontWeight={kind === 'milestone' ? 600 : 400} fill={GRAY}>
              {labels[i].length === 1 ? (
                labels[i][0]
              ) : (
                <>
                  <tspan x={6} dy={-7}>
                    {labels[i][0]}
                  </tspan>
                  <tspan x={6} dy={14}>
                    {labels[i][1]}
                  </tspan>
                </>
              )}
              <title>{title}</title>
            </text>
            <g>
              <title>{title}</title>
              {mark}
            </g>
            <text x={fits ? right + 6 : (kind === 'task' ? X(s) : X(s) + px / 2 - 7) - 6} y={yMid} dominantBaseline="central" textAnchor={fits ? 'start' : 'end'} fontSize={11} fill={MUTED}>
              {when}
            </text>
          </g>
        )
      })}
      {todayIn && t != null && (
        <g>
          <line x1={X(t) + px / 2} y1={16} x2={X(t) + px / 2} y2={H - legendH} stroke={GOLD_DARK} strokeWidth={1.5} strokeDasharray="5 3" />
          <text x={X(t) + px / 2} y={12} textAnchor="middle" fontSize={11} fontWeight={700} fill={GOLD_DARK}>
            today
          </text>
        </g>
      )}
      <g transform={`translate(${x0}, ${H - legendH / 2})`}>
        <rect x={0} y={-6} width={22} height={12} rx={3} fill={PANEL_FILL} stroke={GOLD_DARK} strokeWidth={1} />
        <text x={28} y={0} dominantBaseline="central" fontSize={11} fill={MUTED}>
          task, from its start to its end
        </text>
        <Diamond cx={200} cy={0} r={6} />
        <text x={212} y={0} dominantBaseline="central" fontSize={11} fill={MUTED}>
          milestone
        </text>
        <Diamond cx={290} cy={0} r={6} hollow />
        <text x={302} y={0} dominantBaseline="central" fontSize={11} fill={MUTED}>
          payment from the customer
        </text>
      </g>
    </svg>
  )

  if (!narrow) return chart
  return (
    <div>
      <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
        Scroll sideways to see the whole schedule.
      </div>
      <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch', maxWidth: '100%' }}>{chart}</div>
    </div>
  )
}
