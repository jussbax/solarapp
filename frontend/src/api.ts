import type {
  ApplianceCategory, AppSettings, AssessmentDoc, AssessmentOut, AssessmentSummary, CatalogItem, DatasheetPage, DatasheetReport, DataStatus, ImportReport, Lead, MaterialItem,
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
  faces: 'Roof face', panel_code: 'Panel', reading_sets: 'Reading set', readings: 'Reading', walls: 'Wall', obstacles: 'Obstacle',
  test_panel_rating_w: 'Test panel rating', test_panel_calibration: 'Calibration factor',
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
/** Who is signed in. Before sign-in only `passkeys` is filled (whether any key exists, so the login page can offer the button). */
export type Me = {
  username: string | null
  signed_in: boolean
  display_name?: string
  role?: 'owner' | 'engineer'
  must_change_password?: boolean
  two_factor?: boolean
  backup_codes_left?: number
  passkeys?: boolean
}
export type Person = {
  id: number
  username: string
  display_name: string
  role: 'owner' | 'engineer'
  active: boolean
  must_change_password: boolean
  two_factor: boolean
  passkeys: number
  created_at: string | null
  last_login_at: string | null
}
export type Passkey = { id: number; name: string; transports: string[]; backed_up: boolean; created_at: string | null; last_used_at: string | null }
export type FetchedDocument = { blob: Blob; filename: string; inline: boolean }

export const api = {
  me: () => request<Me>('/api/auth/me'),
  login: (username: string, password: string, code = '') => request<Me>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password, code }) }),
  logout: () => request<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),
  passkeyLoginOptions: () => request<{ challenge_id: string; options: Record<string, unknown> }>('/api/auth/passkey/options', { method: 'POST' }),
  passkeyLogin: (challenge_id: string, credential: Record<string, unknown>) =>
    request<Me>('/api/auth/passkey/login', { method: 'POST', body: JSON.stringify({ challenge_id, credential }) }),
  signOutEverywhere: () => request<{ ok: boolean }>('/api/auth/signout-everywhere', { method: 'POST' }),
  // the person's own password and authenticator app; each asks for the current password (and a code) again
  changePassword: (current_password: string, code: string, new_password: string) =>
    request<Me>('/api/auth/password', { method: 'POST', body: JSON.stringify({ current_password, code, new_password }) }),
  totpBegin: (confirm: StepUp) => request<{ secret: string; uri: string; qr: string }>('/api/auth/totp/begin', { method: 'POST', body: JSON.stringify(confirm) }),
  totpConfirm: (code: string) => request<{ ok: boolean; backup_codes: string[] }>('/api/auth/totp/confirm', { method: 'POST', body: JSON.stringify({ code }) }),
  totpDisable: (confirm: StepUp) => request<{ ok: boolean }>('/api/auth/totp/disable', { method: 'POST', body: JSON.stringify(confirm) }),
  // people (owner only)
  users: () => request<Person[]>('/api/users'),
  createUser: (username: string, display_name: string, role: Person['role']) =>
    request<Person & { temporary_password: string }>('/api/users', { method: 'POST', body: JSON.stringify({ username, display_name, role }) }),
  patchUser: (id: number, patch: Partial<Pick<Person, 'display_name' | 'role' | 'active'>>) =>
    request<Person>(`/api/users/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  resetUserPassword: (id: number) => request<Person & { temporary_password: string }>(`/api/users/${id}/reset-password`, { method: 'POST' }),
  resetUserAuthenticator: (id: number) => request<Person>(`/api/users/${id}/reset-authenticator`, { method: 'POST' }),
  passkeys: () => request<Passkey[]>('/api/auth/passkeys'),
  // managing keys asks for the password (and the code) again, so a stolen cookie alone cannot add or remove one
  passkeyRegisterOptions: (confirm: StepUp) =>
    request<{ challenge_id: string; options: Record<string, unknown> }>('/api/auth/passkeys/options', { method: 'POST', body: JSON.stringify(confirm) }),
  passkeyRegister: (challenge_id: string, name: string, credential: Record<string, unknown>) =>
    request<Passkey>('/api/auth/passkeys', { method: 'POST', body: JSON.stringify({ challenge_id, name, credential }) }),
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
  /** `confirmReprice` re-prices a quoted job after the pricing settings changed; without it the server answers 409. */
  computeAssessment: (id: number, doc: AssessmentDoc, confirmReprice = false) =>
    request<AssessmentOut>(`/api/assessments/${id}/compute${confirmReprice ? '?confirm_reprice=true' : ''}`, { method: 'POST', body: JSON.stringify(doc) }),
  reportUrl: (id: number) => `/api/assessments/${id}/report.pdf`,
  categories: () => request<ApplianceCategory[]>('/api/appliances/categories'),
  searchAppliances: (q: string) => request<CatalogItem[]>(`/api/appliances?q=${encodeURIComponent(q)}&limit=8`),
  quotationUrl: (id: number) => `/api/assessments/${id}/quotation.pdf`,
  /** "Reopen design": the proposal issued for the record is no longer the standing one; the status falls back to the facts and Calculate re-prices freely. */
  reopenDesign: (id: number) => request<AssessmentOut>(`/api/assessments/${id}/reopen`, { method: 'POST' }),
  programUrl: (id: number) => `/api/assessments/${id}/program.pdf`,
  /** The plans for the PEE (A3 drawing set); refused like the proposal on stale or design-blocked results. */
  plansUrl: (id: number) => `/api/assessments/${id}/plans.pdf`,
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
  // round 12: the maker's datasheet workbooks; the specs rows and where each item's electrical figure came from
  datasheets: (category?: string) => request<DatasheetPage>(`/api/pricing/datasheets${category ? `?category=${encodeURIComponent(category)}` : ''}`),
  importDatasheet: async (file: File, applyHeld: boolean, dryRun = false) => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await safeFetch(`/api/pricing/datasheets?apply_held=${applyHeld}&dry_run=${dryRun}`, { method: 'POST', body: fd, credentials: 'same-origin' })
    if (!res.ok) throw new ApiError(res.status, describeDetail(await detailOf(res), res.status))
    return (await res.json()) as DatasheetReport
  },
  linkDatasheet: (id: number, code: string) => request<{ code: string; changes: string[]; notes: string[] }>(`/api/pricing/datasheets/${id}/link`, { method: 'POST', body: JSON.stringify({ code }) }),
  addDatasheetItem: (id: number, code: string, supplier = '') => request<MaterialItem>(`/api/pricing/datasheets/${id}/add-item`, { method: 'POST', body: JSON.stringify({ code, supplier }) }),
  /** The owner confirms one held row (the brief's 6.4 and 6.8 have different answers), or takes it back. */
  applyHeld: (id: number) => request<{ code: string | null; changes: string[]; held_applied_at: string }>(`/api/pricing/datasheets/${id}/apply-held`, { method: 'POST' }),
  withdrawHeld: (id: number) => request<{ code: string | null; changes: string[] }>(`/api/pricing/datasheets/${id}/withdraw-held`, { method: 'POST' }),
  // website bookings are the CRM's data (the inbox, statuses, notes and funnel live behind /api/leads for it);
  // the engineering app only lists them and starts a project from one
  bookings: () => request<Lead[]>('/api/leads/open'),
  /** Start a project from a booking: the customer reference, the pin or town and the bill are copied; the booking stays with the website's records. */
  convertLead: (id: number) => request<{ project_id: number; lead: Lead }>(`/api/leads/${id}/convert`, { method: 'POST' }),
  /** Bill of materials export (the generated list with the owner's edits); fetch through fetchDocument so a stale record shows its message. */
  bomCsvUrl: (id: number) => `/api/assessments/${id}/bom.csv`,
  bomXlsxUrl: (id: number) => `/api/assessments/${id}/bom.xlsx`,
}
