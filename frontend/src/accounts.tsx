import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { ApiError } from './api'

/* Helpers the account screens share (no components here, so the component files export only components). */

/* The temporary password the person just signed in with, kept in memory only (never in storage) so the first-sign-in
 * gate does not ask them to type it again. The login form sets it; the gate spends it; a reload loses it, and the gate
 * then asks for it once more. */
let temporaryPassword = ''
export function rememberTemporaryPassword(password: string) {
  temporaryPassword = password
}
export function forgetTemporaryPassword() {
  temporaryPassword = ''
}
export const temporaryPasswordInMemory = () => temporaryPassword

/** One line at the foot of the screen for four seconds: "Password changed." */
export function useToast(): { toast: ReactNode; show: (text: string) => void } {
  const [text, setText] = useState<string | null>(null)
  const timer = useRef<number>(0)
  const show = useCallback((t: string) => {
    setText(t)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setText(null), 4000)
  }, [])
  useEffect(() => () => window.clearTimeout(timer.current), [])
  const toast = text ? (
    <div className="toast" role="status" data-testid="toast">
      {text}
    </div>
  ) : null
  return { toast, show }
}

/** The server's step-up refusal (403) in the dialog's own words; anything else keeps the server's text. */
export function stepUpProblem(err: unknown, twoFactor: boolean): string {
  if (err instanceof ApiError && err.status === 403) return twoFactor ? 'The password or the code is wrong. Try again.' : 'That password is wrong. Try again.'
  return err instanceof Error ? err.message : String(err)
}

/** The username the app suggests from the name: lowercase, accents stripped, the first name, a dot, the rest joined
 *  ("Juan dela Cruz" → juan.delacruz, "Pedro Santos" → pedro.santos); anything else becomes a dash. */
export function suggestUsername(name: string): string {
  const plain = name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
  const words = plain
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w.replace(/[^a-z0-9._-]+/g, '-').replace(/^[._-]+|[._-]+$/g, ''))
  const joined = words.length <= 1 ? words.join('') : `${words[0]}.${words.slice(1).join('')}`
  return joined
    .replace(/[._-]{2,}/g, (m) => m[0])
    .replace(/^[^a-z0-9]+/, '')
    .slice(0, 40)
}
