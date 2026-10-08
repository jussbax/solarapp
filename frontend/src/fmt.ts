/** Shared number, money and date formats so every page writes them the same way. */

export const php0 = (v: number | null | undefined) => {
  if (v == null || !Number.isFinite(v)) return '-'
  const r = Math.round(v)
  return `${r < 0 ? '-' : ''}₱${Math.abs(r).toLocaleString()}`
}

export const php2 = (v: number | null | undefined) => {
  if (v == null || !Number.isFinite(v)) return '-'
  return `${v < 0 ? '-' : ''}₱${Math.abs(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export const n0 = (v: number | null | undefined) => (v == null || !Number.isFinite(v) ? '-' : Math.round(v).toLocaleString())

const DATE: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' }

/** "8 Oct 2026" from an ISO date or date-time string. */
export const fmtDate = (s: string | null | undefined) => {
  if (!s) return ''
  const d = s.length === 10 ? new Date(s + 'T00:00:00') : new Date(s)
  return Number.isNaN(d.getTime()) ? s : d.toLocaleDateString('en-PH', DATE)
}

/** "8 Oct 2026, 3:04 PM" from an ISO date-time string. */
export const fmtDateTime = (s: string | null | undefined) => {
  if (!s) return ''
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? s : `${d.toLocaleDateString('en-PH', DATE)}, ${d.toLocaleTimeString('en-PH', { hour: 'numeric', minute: '2-digit' })}`
}

/** Pluralise without the "(s)" habit: plural(1, 'day') -> "1 day", plural(2, 'day') -> "2 days". */
export const plural = (n: number, word: string, pluralWord?: string) => `${n} ${n === 1 ? word : pluralWord ?? word + 's'}`
