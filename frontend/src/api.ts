import type {
  ApplianceCategory, AppSettings, AssessmentDoc, AssessmentOut, AssessmentSummary, CatalogItem, DataStatus, ImportReport, MaterialItem, MaterialSupplier,
  PricingConfig, PricingStatus,
} from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (res.status === 401 && !path.endsWith('/auth/login') && !path.endsWith('/auth/me')) {
    onUnauthorized?.()
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  me: () => request<{ username: string | null; signed_in: boolean }>('/api/auth/me'),
  login: (username: string, password: string) =>
    request<{ username: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => request<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),
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
    const res = await fetch(`/api/pricing/import?keep_config=${keepConfig}`, { method: 'POST', body: fd, credentials: 'same-origin' })
    if (!res.ok) {
      let detail = res.statusText
      try {
        detail = (await res.json()).detail
      } catch {
        /* ignore */
      }
      throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
    }
    return (await res.json()) as ImportReport
  },
  importSeed: (keepConfig: boolean) => request<ImportReport>(`/api/pricing/import-seed?keep_config=${keepConfig}`, { method: 'POST' }),
}
