import type { EstimateRequest, EstimateResult, EstimateStatus, LeadRequest, LeadSource } from './types'

/** A random id per browser so the rate limit tells visitors apart behind one shared mobile address. */
function visitorId(): string {
  try {
    let v = localStorage.getItem('pld:visitor')
    if (!v) {
      v = Math.random().toString(36).slice(2) + Date.now().toString(36)
      localStorage.setItem('pld:visitor', v)
    }
    return v
  } catch {
    return 'anon'
  }
}

/** UTM tags and the referrer of the page the estimate sits on. */
export function readSource(): LeadSource {
  const q = new URLSearchParams(typeof window === 'undefined' ? '' : window.location.search)
  const pick = (k: string) => (q.get(k) || '').slice(0, 100)
  return {
    utm_source: pick('utm_source'),
    utm_medium: pick('utm_medium'),
    utm_campaign: pick('utm_campaign'),
    utm_content: pick('utm_content'),
    fbclid: (q.get('fbclid') || '').slice(0, 200),
    referrer: (typeof document === 'undefined' ? '' : document.referrer).slice(0, 300),
    page: (typeof window === 'undefined' ? '' : window.location.href.split('#')[0]).slice(0, 300),
  }
}

export class EstimateError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const UNAVAILABLE = "The estimate isn't available right now. Please try again later or message us on Facebook."

function describe(detail: unknown, status: number): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return 'Please check your answers: ' + detail.map((d) => String(d?.msg ?? 'invalid')).join('; ')
  if (status >= 500 || status === 0) return UNAVAILABLE
  return `Something went wrong (HTTP ${status}).`
}

export function makeApi(base: string, source: LeadSource) {
  const root = base.replace(/\/$/, '')
  const sourceTag = source.utm_source ? `${source.utm_source}/${source.utm_campaign}`.slice(0, 100) : source.referrer ? 'referral' : ''
  async function call<T>(path: string, init?: RequestInit): Promise<T> {
    let res: Response
    try {
      res = await fetch(root + path, {
        ...init,
        headers: { 'Content-Type': 'application/json', 'X-Visitor': visitorId(), ...(sourceTag ? { 'X-Source': sourceTag } : {}), ...(init?.headers || {}) },
      })
    } catch {
      throw new EstimateError(0, UNAVAILABLE)
    }
    if (!res.ok) {
      let detail: unknown = null
      try {
        detail = (await res.json()).detail
      } catch {
        /* no body */
      }
      throw new EstimateError(res.status, describe(detail, res.status))
    }
    return (await res.json()) as T
  }
  return {
    status: () => call<EstimateStatus>('/api/quick/status'),
    estimate: (body: EstimateRequest) => call<EstimateResult>('/api/quick/estimate', { method: 'POST', body: JSON.stringify(body) }),
    lead: (body: LeadRequest) => call<{ ok: boolean; id?: number }>('/api/quick/lead', { method: 'POST', body: JSON.stringify(body) }),
  }
}

/** Tell the host page what happened, for its analytics (Pixel, GTM) to pick up. */
export function emit(event: string, detail: Record<string, unknown> = {}) {
  try {
    window.dispatchEvent(new CustomEvent('pld-estimate', { detail: { event, ...detail } }))
    const w = window as unknown as { dataLayer?: unknown[] }
    if (Array.isArray(w.dataLayer)) w.dataLayer.push({ event: `pld_${event}`, ...detail })
  } catch {
    /* ignore */
  }
}
