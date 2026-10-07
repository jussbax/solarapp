export const COMPASS: { label: string; deg: number }[] = [
  { label: 'N', deg: 0 }, { label: 'NNE', deg: 22.5 }, { label: 'NE', deg: 45 }, { label: 'ENE', deg: 67.5 },
  { label: 'E', deg: 90 }, { label: 'ESE', deg: 112.5 }, { label: 'SE', deg: 135 }, { label: 'SSE', deg: 157.5 },
  { label: 'S', deg: 180 }, { label: 'SSW', deg: 202.5 }, { label: 'SW', deg: 225 }, { label: 'WSW', deg: 247.5 },
  { label: 'W', deg: 270 }, { label: 'WNW', deg: 292.5 }, { label: 'NW', deg: 315 }, { label: 'NNW', deg: 337.5 },
]

export function compassLabel(deg: number): string {
  const i = Math.round((((deg % 360) + 360) % 360) / 22.5) % 16
  return COMPASS[i].label
}
