import type { AppSettings, AssessmentDoc, AssessmentOut, AssessmentSummary, DataStatus } from './types'

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
}
