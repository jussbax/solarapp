import type { AssessmentDoc } from './types'

/**
 * Unsaved edits are kept on the device so a reload or a dropped tab on the roof
 * does not throw away the measurements. One draft per assessment.
 */
const key = (id: number) => `solarapp:draft:${id}`

export interface Draft {
  doc: AssessmentDoc
  saved_at: string
  base_updated_at: string
}

export function readDraft(id: number): Draft | null {
  try {
    const raw = localStorage.getItem(key(id))
    if (!raw) return null
    const d = JSON.parse(raw) as Draft
    return d && d.doc && d.saved_at ? d : null
  } catch {
    return null
  }
}

export function writeDraft(id: number, doc: AssessmentDoc, baseUpdatedAt: string) {
  try {
    localStorage.setItem(key(id), JSON.stringify({ doc, saved_at: new Date().toISOString(), base_updated_at: baseUpdatedAt } satisfies Draft))
  } catch {
    /* storage may be unavailable in private mode; the beforeunload guard still applies */
  }
}

export function clearDraft(id: number) {
  try {
    localStorage.removeItem(key(id))
  } catch {
    /* ignore */
  }
}
