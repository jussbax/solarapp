import type { FaceGeometry } from '../types'

/** The plan of one roof face as an SVG, drawn from results.geometry (the same data the PDF plan uses): the outline,
 * the setback, the panels numbered from the eave up (their string under the number when asked), wall strips hatched,
 * trees and buildings as lettered markers on the edge they shade from, dimension lines in metres (the eave, the slope,
 * a hip's ridge, and the strips that hold no panels as a near chain), a 1 m scale bar, the eave labelled at the bottom,
 * the direction the face looks toward and a north arrow. Pure: no fetches, no state. Legible at 344 px wide; a tall,
 * narrow face keeps its scale up to maxHeight (600 px by default) instead of shrinking into a thumbnail. */

const INK = '#111111'
const GRAY = '#2D2D2D'
const MUTED = '#6b6b66'
const GOLD_DARK = '#a4841c'
const OFF_WHITE = '#F5F5F3'
const PANEL_FILL = '#E9DAA9'
const STRIP_FILL = '#F1EBDD'

export interface PlanDrawingProps {
  face: FaceGeometry
  /** Panels the sized system uses on this face, counted from the eave up (results.geometry[i].used). Leave it out to
   * draw every panel the same, as the roof check does. */
  selected?: number | null
  /** Width in px; the height follows the face's proportions, capped at maxHeight. */
  width?: number
  /** The height cap of the whole drawing in px (default 600), so a face taller than wide is drawn at a scale that can be read. */
  maxHeight?: number
  /** Dimension lines with their metres (default on): the eave, the slope, a hip's ridge and the no-panel strips. */
  dimensions?: boolean
  /** S1, S2 ... under the panel number, as the current rule numbers the strings (default on). */
  stringLabels?: boolean
  /** The north arrow at the top right, from the face azimuth (default on). */
  northArrow?: boolean
}

const lower = (s: string) => (s ? s[0].toLowerCase() + s.slice(1) : s)
const m2 = (v: number) => v.toFixed(2)

/** Where north points on a plan whose eave is at the bottom: the drawing's "up" is the direction the ridge lies in
 * (azimuth + 180), so north sits 180 - azimuth degrees clockwise from up. South face: north up; east face: north right.
 * The same rule as the PDF plan (drawings.north_angle_deg). */
const northAngleDeg = (azimuthDeg: number): number => (((180 - azimuthDeg) % 360) + 360) % 360

/** Rough width of a label in px, enough to decide whether it fits inside a dimension segment. */
const textWidth = (s: string, fs: number) => s.length * fs * 0.58

export function PlanDrawing({ face, selected, width = 344, maxHeight = 600, dimensions = true, stringLabels = true, northArrow = true }: PlanDrawingProps) {
  const eave = Math.max(face.eave_m, 0.1)
  const slope = Math.max(face.slope_m, 0.1)
  const panels = face.panels ?? []
  const markers = (face.obstacles ?? []).filter((o) => o.kind === 'shade')
  const walls = (face.obstacles ?? []).filter((o) => o.kind === 'wall')
  const highlight = selected != null
  const legend = [
    ...markers.map((o, i) => `${String.fromCharCode(65 + i)}: ${o.label}`),
    ...walls.map((o) => `Hatched: ${lower(o.label)}`),
  ]
  if (highlight && (selected ?? 0) < panels.length) legend.push('Dashed: positions the roof can still hold')
  if (dimensions) legend.push('Dimensions in metres: the outer figures are the face, the near ones the strips that hold no panels (the setback, or a wall strip)')

  const narrow = width < 480
  const fs = narrow ? 10 : 11 // the dimension text
  const ridge = face.ridge_m ?? 0
  const ridgeDim = dimensions && face.shape === 'hip' && ridge > 0 && ridge < eave - 1e-6
  const t = 4 // the tick half-length
  const row1 = 14 // the near chain (the strips)
  const row2 = 32 // the overall figure
  const arrowR = 14
  const side = 10
  let left = dimensions ? row2 + fs + 6 : side
  let right = side
  let top = ridgeDim ? row1 + fs + 8 : 10
  if (northArrow) {
    top = Math.max(top, 2 * arrowR + fs * 1.4 + 8)
    right = Math.max(right, 2 * arrowR + fs + 6)
  }
  const bottomLine = narrow ? 34 : 22
  const bottom = (dimensions ? row2 + 6 : 0) + bottomLine
  const availW = width - left - right
  const availH = Math.max(maxHeight - top - bottom, 120) // the cap is on the whole drawing, margins included
  const s = Math.min(availW / eave, availH / slope) // px per metre
  const planW = eave * s
  const planH = slope * s
  const height = top + planH + bottom
  const ox = left + (availW - planW) / 2
  const X = (x: number) => ox + x * s
  const Y = (y: number) => top + (slope - y) * s // the eave at the bottom, the slope upwards
  const pts = (poly: [number, number][]) => poly.map(([x, y]) => `${X(x).toFixed(1)},${Y(y).toFixed(1)}`).join(' ')
  const outline: [number, number][] = face.outline?.length ? face.outline : [[0, 0], [eave, 0], [eave, slope], [0, slope]]
  const usable: [number, number][] = face.usable && face.usable.length >= 3 ? face.usable : []
  const hatchId = `plan-hatch-${face.face_id}`
  const clipId = `plan-clip-${face.face_id}`
  const yb = top + planH + (dimensions ? row2 + 6 : 0) + 13 // the line under the eave (and under the dimension rows)
  const bar = Math.min(s, planW)
  const looks = `looks ${face.compass ?? ''} (${face.azimuth_deg}°) · pitch ${face.tilt_deg}°`
  // with a selected count the first `selected` panels from the eave up are the system's; without one every panel is drawn the same
  const used = (n: number) => !highlight || n <= (selected ?? 0)

  // the strips that hold no panels: a wall strip when there is one on that side, else the setback line's inset
  const inset = Math.max(face.setback_m ?? 0, 0) / 2
  let yLo = inset
  let yHi = slope - inset
  let xLo = inset
  let xHi = eave - inset
  if (usable.length) {
    yLo = Math.min(...usable.map((p) => p[1]))
    yHi = Math.max(...usable.map((p) => p[1]))
    const bottomPts = usable.filter((p) => Math.abs(p[1] - yLo) < 1e-6).map((p) => p[0])
    xLo = Math.min(...bottomPts)
    xHi = Math.max(...bottomPts)
  }
  const strips: Partial<Record<string, number>> = {}
  for (const w of walls) strips[w.edge] = w.edge === 'left' || w.edge === 'right' ? w.w : w.h
  const leftW = strips.left ?? xLo
  const rightW = strips.right ?? eave - xHi
  const botH = strips.eave ?? yLo
  const topH = strips.ridge ?? slope - yHi
  const ridgeXs = ridgeDim ? outline.filter((p) => Math.abs(p[1] - slope) < 1e-6).map((p) => p[0]).sort((a, b) => a - b) : []

  const tick = (x: number, y: number, key: string) => <line key={key} x1={x - t} y1={y + t} x2={x + t} y2={y - t} stroke={GRAY} strokeWidth={1} />
  /** A horizontal dimension on the line yLine, its extension lines from the face edge yEdge; the text above the line,
   * or at the segment's inner end when it is wider than the segment ("right": it starts at x2; "left": it ends at x1). */
  const dimH = (x1: number, x2: number, yLine: number, yEdge: number, text: string, strong: boolean, anchor: 'centre' | 'left' | 'right', key: string) => {
    const ext = yLine > yEdge ? yLine + 0.9 * t : yLine - 0.9 * t
    const fits = textWidth(text, fs) <= Math.abs(x2 - x1) - 2 * t
    const tx = fits || anchor === 'centre' ? (x1 + x2) / 2 : anchor === 'right' ? x2 + 0.9 * t + 1 : x1 - 0.9 * t - 1
    const ta = fits || anchor === 'centre' ? 'middle' : anchor === 'right' ? 'start' : 'end'
    return (
      <g key={key} fill="none" stroke={GRAY}>
        <line x1={x1} y1={yLine} x2={x2} y2={yLine} strokeWidth={0.8} />
        <line x1={x1} y1={yEdge} x2={x1} y2={ext} strokeWidth={0.6} />
        <line x1={x2} y1={yEdge} x2={x2} y2={ext} strokeWidth={0.6} />
        {tick(x1, yLine, 'a')}
        {tick(x2, yLine, 'b')}
        <text x={tx} y={yLine - 3} textAnchor={ta} fontSize={fs} fontWeight={strong ? 600 : 400} fill={strong ? INK : GRAY} stroke="none">
          {text}
        </text>
      </g>
    )
  }
  /** A vertical dimension on the line xLine, left of the face; the text reads from the bottom up and sits left of the line. */
  const dimV = (y1: number, y2: number, xLine: number, xEdge: number, text: string, strong: boolean, anchor: 'centre' | 'up' | 'down', key: string) => {
    const ext = xLine - 0.9 * t
    const fits = textWidth(text, fs) <= Math.abs(y2 - y1) - 2 * t
    // in screen coordinates y1 (the eave) is below y2 (the ridge): "up" starts at the top end and reads on upwards
    const cy = fits || anchor === 'centre' ? (y1 + y2) / 2 : anchor === 'up' ? Math.min(y1, y2) - 0.9 * t - 1 : Math.max(y1, y2) + 0.9 * t + 1
    const ta = fits || anchor === 'centre' ? 'middle' : anchor === 'up' ? 'start' : 'end'
    return (
      <g key={key} fill="none" stroke={GRAY}>
        <line x1={xLine} y1={y1} x2={xLine} y2={y2} strokeWidth={0.8} />
        <line x1={xEdge} y1={y1} x2={ext} y2={y1} strokeWidth={0.6} />
        <line x1={xEdge} y1={y2} x2={ext} y2={y2} strokeWidth={0.6} />
        {tick(xLine, y1, 'a')}
        {tick(xLine, y2, 'b')}
        <text transform={`translate(${(xLine - 3).toFixed(1)} ${cy.toFixed(1)}) rotate(-90)`} textAnchor={ta} fontSize={fs} fontWeight={strong ? 600 : 400} fill={strong ? INK : GRAY} stroke="none">
          {text}
        </text>
      </g>
    )
  }

  // the north arrow: a circle at the top right, the arrow turned to north, the N beyond its tip
  const na = (northAngleDeg(face.azimuth_deg) * Math.PI) / 180
  const ndx = Math.sin(na)
  const ndy = -Math.cos(na) // screen y runs down
  const ncx = width - side - arrowR - fs * 0.7
  const ncy = fs * 1.4 + arrowR + 2
  const tip = [ncx + ndx * arrowR * 0.82, ncy + ndy * arrowR * 0.82]
  const tail = [ncx - ndx * arrowR * 0.7, ncy - ndy * arrowR * 0.7]
  const hw = arrowR * 0.22
  const hl = arrowR * 0.4
  const base = [tip[0] - ndx * hl, tip[1] - ndy * hl]

  // the eave label steps right of the scale text when a narrow face leaves no room under it
  const barText = bar >= s - 1e-6 ? '1 m' : `${(bar / s).toFixed(1)} m`
  const barRight = X(0) + bar + 5 + textWidth(barText, 10)
  const eaveX = Math.max(ox + planW / 2, barRight + 8 + textWidth('Eave (lower edge)', 10) / 2)

  return (
    <figure style={{ margin: 0, maxWidth: width }}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`Plan of ${face.name}: ${eave} m along the eave by ${slope} m up the slope, ${panels.length} panels`}
        style={{ display: 'block', fontFamily: 'inherit' }}
      >
        <defs>
          <pattern id={hatchId} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" fill={STRIP_FILL} />
            <line x1="0" y1="0" x2="0" y2="6" stroke={GOLD_DARK} strokeWidth="0.8" />
          </pattern>
          <clipPath id={clipId}>
            <polygon points={pts(outline)} />
          </clipPath>
        </defs>
        <polygon points={pts(outline)} fill={OFF_WHITE} stroke={INK} strokeWidth={1.2} />
        <g clipPath={`url(#${clipId})`}>
          {walls.map((o, i) => (
            <rect key={`w${i}`} x={X(o.x)} y={Y(o.y + o.h)} width={o.w * s} height={o.h * s} fill={`url(#${hatchId})`}>
              <title>{o.label}</title>
            </rect>
          ))}
        </g>
        {usable.length >= 3 && <polygon points={pts(usable)} fill="none" stroke={MUTED} strokeWidth={0.8} strokeDasharray="3 3" />}
        {panels.map((p) => {
          const on = used(p.n)
          const w = p.w * s
          const h = p.h * s
          const size = Math.max(9, Math.min(14, Math.min(w, h) * 0.36))
          const sub = stringLabels && on && p.string ? `S${p.string}` : ''
          const twoLines = sub !== '' && Math.min(w, h) >= 30
          const cx = X(p.x) + w / 2
          const cy = Y(p.y + p.h) + h / 2
          return (
            <g key={p.n}>
              <rect
                x={X(p.x)}
                y={Y(p.y + p.h)}
                width={w}
                height={h}
                fill={on ? PANEL_FILL : '#ffffff'}
                stroke={on ? GOLD_DARK : MUTED}
                strokeWidth={on ? 1 : 0.8}
                strokeDasharray={on ? undefined : '3 2'}
              >
                <title>{`Panel ${p.n}, row ${p.row}${p.string ? `, string ${p.string}` : ''}${on ? '' : ' (not used by the sized system)'}`}</title>
              </rect>
              {Math.min(w, h) >= 14 && (
                <text x={cx} y={twoLines ? cy - size * 0.1 : cy} textAnchor="middle" dominantBaseline="central" fontSize={size} fontWeight={on ? 600 : 400} fill={on ? INK : MUTED}>
                  {p.n}
                </text>
              )}
              {twoLines && (
                <text x={cx} y={cy + size * 0.95} textAnchor="middle" dominantBaseline="central" fontSize={size * 0.72} fill={GRAY}>
                  {sub}
                </text>
              )}
            </g>
          )
        })}
        {markers.map((o, i) => (
          <g key={`m${i}`}>
            <circle cx={X(o.x)} cy={Y(o.y)} r={8} fill={INK} stroke="#ffffff" strokeWidth={1.5}>
              <title>{o.label}</title>
            </circle>
            <text x={X(o.x)} y={Y(o.y)} textAnchor="middle" dominantBaseline="central" fontSize={10} fontWeight={700} fill="#ffffff">
              {String.fromCharCode(65 + i)}
            </text>
          </g>
        ))}
        {dimensions && (
          <g data-testid="plan-dimensions">
            {leftW > 1e-6 && dimH(X(0), X(leftW), Y(0) + row1, Y(0), m2(leftW), false, 'right', 'dl')}
            {rightW > 1e-6 && dimH(X(eave - rightW), X(eave), Y(0) + row1, Y(0), m2(rightW), false, 'left', 'dr')}
            {dimH(X(0), X(eave), Y(0) + row2, Y(0), `${m2(eave)} m`, true, 'centre', 'de')}
            {botH > 1e-6 && dimV(Y(0), Y(botH), X(0) - row1, X(0), m2(botH), false, 'up', 'db')}
            {topH > 1e-6 && dimV(Y(slope - topH), Y(slope), X(0) - row1, X(0), m2(topH), false, 'down', 'dt')}
            {dimV(Y(0), Y(slope), X(0) - row2, X(0), `${m2(slope)} m`, true, 'centre', 'ds')}
            {ridgeXs.length >= 2 && dimH(X(ridgeXs[0]), X(ridgeXs[ridgeXs.length - 1]), Y(slope) - row1, Y(slope), `ridge ${m2(ridgeXs[ridgeXs.length - 1] - ridgeXs[0])} m`, true, 'centre', 'dg')}
          </g>
        )}
        {northArrow && (
          <g data-testid="plan-north">
            <circle cx={ncx} cy={ncy} r={arrowR} fill="#ffffff" stroke={GRAY} strokeWidth={0.8} />
            <line x1={tail[0]} y1={tail[1]} x2={tip[0]} y2={tip[1]} stroke={INK} strokeWidth={1.2} />
            <polygon points={`${tip[0]},${tip[1]} ${base[0] - ndy * hw},${base[1] + ndx * hw} ${base[0] + ndy * hw},${base[1] - ndx * hw}`} fill={INK} />
            <text x={ncx + ndx * (arrowR + fs * 0.6)} y={ncy + ndy * (arrowR + fs * 0.6)} textAnchor="middle" dominantBaseline="central" fontSize={fs} fontWeight={700} fill={INK}>
              N
            </text>
          </g>
        )}
        <line x1={X(0)} y1={yb} x2={X(0) + bar} y2={yb} stroke={INK} strokeWidth={1.5} />
        <line x1={X(0)} y1={yb - 3} x2={X(0)} y2={yb + 3} stroke={INK} strokeWidth={1} />
        <line x1={X(0) + bar} y1={yb - 3} x2={X(0) + bar} y2={yb + 3} stroke={INK} strokeWidth={1} />
        <text x={X(0) + bar + 5} y={yb + 3.5} fontSize={10} fill={GRAY}>
          {barText}
        </text>
        <text x={eaveX} y={yb + 3.5} textAnchor="middle" fontSize={10} fontWeight={600} fill={INK}>
          Eave (lower edge)
        </text>
        {narrow ? (
          <text x={width - side} y={yb + 16} textAnchor="end" fontSize={10} fill={GRAY}>
            {looks}
          </text>
        ) : (
          <text x={width - side} y={yb + 3.5} textAnchor="end" fontSize={10} fill={GRAY}>
            {looks}
          </text>
        )}
      </svg>
      {legend.length > 0 && (
        <figcaption style={{ fontSize: 12, lineHeight: 1.35, color: MUTED, marginTop: 2 }}>
          {legend.map((l, i) => (
            <div key={i}>{l}</div>
          ))}
        </figcaption>
      )}
    </figure>
  )
}
