import type { FaceGeometry } from '../types'

/** The plan of one roof face as an SVG, drawn from results.geometry (the same data the PDF plan uses): the outline,
 * the setback, the panels numbered from the eave up, wall strips hatched, trees and buildings as lettered markers on the
 * edge they shade from, a 1 m scale bar, the eave labelled at the bottom and the direction the face looks toward.
 * Pure: no fetches, no state. Legible at 344 px wide. */

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
  /** Width in px; the height follows the face's proportions, capped at maxHeight (default 0.62 × width). */
  width?: number
  maxHeight?: number
}

const lower = (s: string) => (s ? s[0].toLowerCase() + s.slice(1) : s)

export function PlanDrawing({ face, selected, width = 344, maxHeight }: PlanDrawingProps) {
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

  const narrow = width < 480
  const side = 10
  const top = 10
  const bottom = narrow ? 34 : 22
  const maxH = maxHeight ?? width * 0.62
  const s = Math.min((width - 2 * side) / eave, maxH / slope) // px per metre
  const planW = eave * s
  const planH = slope * s
  const height = top + planH + bottom
  const ox = side + (width - 2 * side - planW) / 2
  const X = (x: number) => ox + x * s
  const Y = (y: number) => top + (slope - y) * s // the eave at the bottom, the slope upwards
  const pts = (poly: [number, number][]) => poly.map(([x, y]) => `${X(x).toFixed(1)},${Y(y).toFixed(1)}`).join(' ')
  const outline: [number, number][] = face.outline?.length ? face.outline : [[0, 0], [eave, 0], [eave, slope], [0, slope]]
  const hatchId = `plan-hatch-${face.face_id}`
  const clipId = `plan-clip-${face.face_id}`
  const yb = top + planH + 13 // the line under the eave
  const bar = Math.min(s, planW)
  const looks = `looks ${face.compass ?? ''} (${face.azimuth_deg}°) · pitch ${face.tilt_deg}°`
  // with a selected count the first `selected` panels from the eave up are the system's; without one every panel is drawn the same
  const used = (n: number) => !highlight || n <= (selected ?? 0)

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
        {face.usable && face.usable.length >= 3 && (
          <polygon points={pts(face.usable)} fill="none" stroke={MUTED} strokeWidth={0.8} strokeDasharray="3 3" />
        )}
        {panels.map((p) => {
          const on = used(p.n)
          const w = p.w * s
          const h = p.h * s
          const fs = Math.max(9, Math.min(13, Math.min(w, h) * 0.36))
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
                <text x={X(p.x) + w / 2} y={Y(p.y + p.h) + h / 2} textAnchor="middle" dominantBaseline="central" fontSize={fs} fontWeight={on ? 600 : 400} fill={on ? INK : MUTED}>
                  {p.n}
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
        <line x1={X(0)} y1={yb} x2={X(0) + bar} y2={yb} stroke={INK} strokeWidth={1.5} />
        <line x1={X(0)} y1={yb - 3} x2={X(0)} y2={yb + 3} stroke={INK} strokeWidth={1} />
        <line x1={X(0) + bar} y1={yb - 3} x2={X(0) + bar} y2={yb + 3} stroke={INK} strokeWidth={1} />
        <text x={X(0) + bar + 5} y={yb + 3.5} fontSize={10} fill={GRAY}>
          {bar >= s - 1e-6 ? '1 m' : `${(bar / s).toFixed(1)} m`}
        </text>
        <text x={ox + planW / 2} y={yb + 3.5} textAnchor="middle" fontSize={10} fontWeight={600} fill={INK}>
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
