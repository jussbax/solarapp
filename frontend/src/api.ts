import type {
  ApplianceCategory, AppSettings, AssessmentDoc, AssessmentOut, AssessmentSummary, CatalogItem, DataStatus, ImportReport, Lead, LeadFunnel, LeadStatus, MaterialItem,
  MaterialSupplier, PricingConfig, PricingStatus,
} from './types'

export class ApiError extends Error {
  /** HTTP status, or 0 when the request never reached the server (no connection). */
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** What the owner reads when the phone has no signal; the assessment page adds that the edits are kept. */
export const OFFLINE_MESSAGE = 'No connection. Try again when you have signal.'

let onUnauthorized: (() => void) | null = null

/** Owner-facing labels for the field names pydantic puts in `loc`; list names get a 1-based number after them. */
const FIELD_LABELS: Record<string, string> = {
  customer_name: 'Customer name', address: 'Address', notes: 'Notes', lat: 'Latitude', lon: 'Longitude', card_next_step: 'Next step printed on the card',
  faces: 'Roof face', panels: 'Panel', reading_sets: 'Reading set', readings: 'Reading', walls: 'Wall', obstacles: 'Obstacle',
  selected_panel_id: 'The panel ticked under Use', test_panel_rating_w: 'Test panel rating', test_panel_calibration: 'Calibration factor',
  setback_m: 'Edge setback', gap_m: 'Gap between panels',
  name: 'Name', shape: 'Shape', length_m: 'Length', width_m: 'Width', ridge_m: 'Ridge length', tilt_deg: 'Tilt', azimuth_deg: 'Facing',
  panels_left_out: 'Panels left out', panel_count_override: 'Panel count (override)', edge: 'Wall edge', height_m: 'Height above roof',
  direction_deg: 'Direction', elevation_deg: 'Angle to top', width_deg: 'Width in degrees', share: 'Share',
  watt_peak: 'Wp', irradiance_wm2: 'Irradiance', power_w: 'Power', module_temp_c: 'Module temperature', ambient_temp_c: 'Air temperature',
  sky_condition: 'Sky', measured_at: 'Measured at', label: 'Label',
  audit: 'Energy audit', appliances: 'Appliance', bills: 'Bill', system: 'System settings', input_power_w: 'W (nameplate)', quantity: 'Qty',
  duty_factor: 'Duty factor', status: 'Status', windows: 'Usage window', start: 'Start', end: 'End', days: 'Days', months: 'Months',
  billing_month: 'Billing month', kwh: 'kWh', amount_php: 'Amount', utility: 'Electric company',
  pricing: 'Pricing inputs', program: 'Schedule inputs', economics: 'Savings inputs', payment: 'Payment terms', milestones: 'Milestone',
}

const labelFor = (key: string) => FIELD_LABELS[key] ?? (key.charAt(0).toUpperCase() + key.slice(1)).replace(/_/g, ' ')

/** "Roof face 2: Length" from ['body', 'faces', 1, 'length_m']. */
function describeLoc(loc: unknown[]): string {
  const parts: string[] = []
  for (const seg of loc) {
    if (seg === 'body' || seg === 'query' || seg === 'path') continue
    if (typeof seg === 'number') parts[parts.length - 1] = `${parts[parts.length - 1] ?? 'Item'} ${seg + 1}`
    else parts.push(labelFor(String(seg)))
  }
  if (parts.length === 0) return ''
  const field = parts.pop()!
  return parts.length ? `${parts.join(' › ')}: ${field}` : field
}

/** Pydantic's "Input should be greater than 0" in the owner's words; custom validator messages pass through. */
function rephrase(msg: string): { text: string; standalone: boolean } {
  if (/^Value error, /.test(msg)) return { text: msg.replace(/^Value error, /, ''), standalone: true }
  const rules: [RegExp, string][] = [
    [/^Input should be greater than or equal to (.+)$/, 'must be at least $1'],
    [/^Input should be greater than (.+)$/, 'must be greater than $1'],
    [/^Input should be less than or equal to (.+)$/, 'must be at most $1'],
    [/^Input should be less than (.+)$/, 'must be less than $1'],
    [/^Input should be a valid integer.*$/, 'must be a whole number'],
    [/^Input should be a valid number.*$/, 'must be a number'],
    [/^Input should be a valid string.*$/, 'must be text'],
    [/^Input should be a valid (date|time).*$/, 'must be a $1'],
    [/^Field required$/, 'is missing'],
    [/^String should have at most (\d+) characters?$/, 'must be at most $1 characters'],
    [/^String should have at least (\d+) characters?$/, 'must be at least $1 characters'],
    [/^List should have at (most|least) (\d+) items?.*$/, 'must have at $1 $2 items'],
    [/^Input should be (.+)$/, 'should be $1'],
  ]
  for (const [re, out] of rules) if (re.test(msg)) return { text: msg.replace(re, out), standalone: false }
  return { text: msg, standalone: false }
}

/** Pydantic returns a list of {loc, msg}; show them as "Calibration factor must be greater than 0". */
export function describeDetail(detail: unknown, status: number): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((d) => {
      const where = Array.isArray(d?.loc) ? describeLoc(d.loc) : ''
      const { text, standalone } = rephrase(String(d?.msg ?? 'is invalid'))
      if (standalone) return where ? `${where}: ${text}` : text
      return where ? `${where} ${text}` : text
    })
    return parts.length === 1 ? parts[0] : `Check these fields: ${parts.join('; ')}`
  }
  if (status >= 500) return 'Something went wrong on the server. Try again; if it keeps happening, tell the developer.'
  return detail ? JSON.stringify(detail) : `Request failed (HTTP ${status}).`
}
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

/** fetch that turns a dropped connection into an ApiError the pages can show, instead of "Failed to fetch". */
async function safeFetch(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(path, init)
  } catch {
    throw new ApiError(0, OFFLINE_MESSAGE)
  }
}

async function detailOf(res: Response): Promise<unknown> {
  try {
    return (await res.json()).detail
  } catch {
    return null // no JSON body
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await safeFetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (res.status === 401 && !/\/auth\/(login|me|passkey\/)/.test(path)) {
    onUnauthorized?.()
  }
  if (!res.ok) throw new ApiError(res.status, describeDetail(await detailOf(res), res.status))
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export type StepUp = { password: string; code: string }
export type Passkey = { id: number; name: string; transports: string[]; backed_up: boolean; created_at: string | null; last_used_at: string | null }
export type FetchedDocument = { blob: Blob; filename: string; inline: boolean }

export const api = {
  me: () => request<{ username: string | null; signed_in: boolean; two_factor?: boolean; passkeys?: boolean }>('/api/auth/me'),
  login: (username: string, password: string, code = '') =>
    request<{ username: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password, code }) }),
  logout: () => request<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),
  passkeyLoginOptions: () => request<{ challenge_id: string; options: Record<string, unknown> }>('/api/auth/passkey/options', { method: 'POST' }),
  passkeyLogin: (challenge_id: string, credential: Record<string, unknown>) =>
    request<{ username: string }>('/api/auth/passkey/login', { method: 'POST', body: JSON.stringify({ challenge_id, credential }) }),
  signOutEverywhere: () => request<{ ok: boolean }>('/api/auth/signout-everywhere', { method: 'POST' }),
  passkeys: () => request<Passkey[]>('/api/auth/passkeys'),
  // managing keys asks for the password (and the code) again, so a stolen cookie alone cannot add or remove one
  passkeyRegisterOptions: (confirm: StepUp) =>
    request<{ challenge_id: string; options: Record<string, unknown> }>('/api/auth/passkeys/options', { method: 'POST', body: JSON.stringify(confirm) }),
  passkeyRegister: (confirm: StepUp, challenge_id: string, name: string, credential: Record<string, unknown>) =>
    request<Passkey>('/api/auth/passkeys', { method: 'POST', body: JSON.stringify({ ...confirm, challenge_id, name, credential }) }),
  passkeyDelete: (id: number, confirm: StepUp) => request<void>(`/api/auth/passkeys/${id}/remove`, { method: 'POST', body: JSON.stringify(confirm) }),
  dataStatus: () => request<DataStatus>('/api/data/status'),
  settings: () => request<AppSettings>('/api/settings'),
  saveSettings: (body: Partial<AppSettings>) => request<AppSettings>('/api/settings', { method: 'PUT', body: JSON.stringify(body) }),
  listAssessments: () => request<AssessmentSummary[]>('/api/assessments'),
  createAssessment: (doc: AssessmentDoc) => request<AssessmentOut>('/api/assessments', { method: 'POST', body: JSON.stringify(doc) }),
  getAssessment: (id: number) => request<AssessmentOut>(`/api/assessments/${id}`),
  updateAssessment: (id: number, doc: AssessmentDoc) =>
    request<AssessmentOut>(`/api/assessments/${id}`, { method: 'PUT', body: JSON.stringify(doc) }),
  deleteAssessment: (id: number) => request<void>(`/api/assessments/${id}`, { method: 'DELETE' }),
  computeAssessment: (id: number, doc: AssessmentDoc) =>
    request<AssessmentOut>(`/api/assessments/${id}/compute`, { method: 'POST', body: JSON.stringify(doc) }),
  reportUrl: (id: number) => `/api/assessments/${id}/report.pdf`,
  categories: () => request<ApplianceCategory[]>('/api/appliances/categories'),
  searchAppliances: (q: string) => request<CatalogItem[]>(`/api/appliances?q=${encodeURIComponent(q)}&limit=8`),
  quotationUrl: (id: number) => `/api/assessments/${id}/quotation.pdf`,
  programUrl: (id: number) => `/api/assessments/${id}/program.pdf`,
  cardUrl: (id: number, nextStep = '') => `/api/assessments/${id}/card.png${nextStep ? `?next_step=${encodeURIComponent(nextStep)}` : ''}`,
  /** Fetch a generated document, so a 409 (stale results) or an outage becomes a message in the bar and never a raw JSON page. */
  fetchDocument: async (url: string): Promise<FetchedDocument> => {
    const res = await safeFetch(url, { credentials: 'same-origin' })
    if (res.status === 401) onUnauthorized?.()
    if (!res.ok) throw new ApiError(res.status, describeDetail(await detailOf(res), res.status))
    const cd = res.headers.get('content-disposition') ?? ''
    const star = /filename\*=UTF-8''([^;]+)/i.exec(cd)
    const plain = /filename="?([^";]+)"?/i.exec(cd)
    let filename = plain?.[1] ?? 'document'
    try {
      if (star) filename = decodeURIComponent(star[1])
    } catch {
      /* keep the ASCII name */
    }
    return { blob: await res.blob(), filename, inline: /^\s*inline/i.test(cd) }
  },
  pricingStatus: () => request<PricingStatus>('/api/pricing/status'),
  pricingConfig: () => request<PricingConfig>('/api/pricing/config'),
  savePricingConfig: (cfg: PricingConfig) => request<PricingConfig>('/api/pricing/config', { method: 'PUT', body: JSON.stringify(cfg) }),
  resetPricingConfig: () => request<PricingConfig>('/api/pricing/config/reset', { method: 'POST' }),
  materialCategories: () => request<{ name: string; count: number }[]>('/api/pricing/categories'),
  materialSuppliers: () => request<MaterialSupplier[]>('/api/pricing/suppliers'),
  materials: (params: { q?: string; category?: string; supplier?: string; include_inactive?: boolean; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params.q) qs.set('q', params.q)
    if (params.category) qs.set('category', params.category)
    if (params.supplier) qs.set('supplier', params.supplier)
    if (params.include_inactive) qs.set('include_inactive', 'true')
    if (params.limit) qs.set('limit', String(params.limit))
    return request<MaterialItem[]>(`/api/pricing/items?${qs.toString()}`)
  },
  createMaterial: (body: Omit<MaterialItem, 'updated_at'>) => request<MaterialItem>('/api/pricing/items', { method: 'POST', body: JSON.stringify(body) }),
  updateMaterial: (code: string, patch: Partial<MaterialItem>) =>
    request<MaterialItem>(`/api/pricing/items/${encodeURIComponent(code)}`, { method: 'PUT', body: JSON.stringify(patch) }),
  deleteMaterial: (code: string) => request<void>(`/api/pricing/items/${encodeURIComponent(code)}`, { method: 'DELETE' }),
  importMaterials: async (file: File, keepConfig: boolean) => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await safeFetch(`/api/pricing/import?keep_config=${keepConfig}`, { method: 'POST', body: fd, credentials: 'same-origin' })
    if (!res.ok) throw new ApiError(res.status, describeDetail(await detailOf(res), res.status))
    return (await res.json()) as ImportReport
  },
  importSeed: (keepConfig: boolean) => request<ImportReport>(`/api/pricing/import-seed?keep_config=${keepConfig}`, { method: 'POST' }),
  // the leads inbox (website bookings); a future CRM module takes these over
  listLeads: (params: { status?: LeadStatus; q?: string } = {}) => {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', params.status)
    if (params.q) qs.set('q', params.q)
    const s = qs.toString()
    return request<Lead[]>(`/api/leads${s ? `?${s}` : ''}`)
  },
  getLead: (id: number) => request<Lead>(`/api/leads/${id}`),
  updateLead: (id: number, patch: { status?: LeadStatus; notes?: string; closed_reason?: string }) =>
    request<Lead>(`/api/leads/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  deleteLead: (id: number) => request<void>(`/api/leads/${id}`, { method: 'DELETE' }),
  /** Start assessment: creates the project from the lead and returns its id. */
  convertLead: (id: number) => request<{ project_id: number; lead: Lead }>(`/api/leads/${id}/convert`, { method: 'POST' }),
  leadFunnel: (days = 30) => request<LeadFunnel>(`/api/leads/funnel?days=${days}`),
}
