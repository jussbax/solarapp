import { useState, type FormEvent, type ReactNode } from 'react'
import { api, ApiError, type Me } from '../api'
import { forgetTemporaryPassword, temporaryPasswordInMemory } from '../accounts'
import '../accounts.css'

export const PASSWORD_RULE = 'At least 12 characters. A short sentence you will remember works well; it must not contain your username.'

/** The three rules the server enforces, ticked live as the person types. */
export function PasswordChecks({ value, username }: { value: string; username: string }) {
  const typed = value.length > 0
  const rules: [boolean, string][] = [
    [typed && value.length >= 12, '12 characters or more'],
    [typed && (!username || !value.toLowerCase().includes(username.toLowerCase())), 'not your username'],
    [typed && new Set(value).size >= 5, '5 different characters'],
  ]
  return (
    <ul className="checks" aria-live="polite" data-testid="password-checks">
      {rules.map(([ok, text]) => (
        <li key={text} className={ok ? 'ok' : ''}>
          <span className="mark" aria-hidden="true">
            {ok ? '✓' : '○'}
          </span>
          {text}
        </li>
      ))}
    </ul>
  )
}

/** A password field with a show/hide eye. */
export function PasswordInput({ id, value, onChange, autoComplete, autoFocus, placeholder, testId }: { id?: string; value: string; onChange: (v: string) => void; autoComplete: string; autoFocus?: boolean; placeholder?: string; testId?: string }) {
  const [show, setShow] = useState(false)
  return (
    <div className="pw-wrap">
      <input id={id} type={show ? 'text' : 'password'} value={value} onChange={(e) => onChange(e.target.value)} autoComplete={autoComplete} autoFocus={autoFocus} placeholder={placeholder} data-testid={testId} />
      <button type="button" className="eye" aria-pressed={show} aria-label={show ? 'Hide the password' : 'Show the password'} onClick={() => setShow((s) => !s)}>
        {show ? 'Hide' : 'Show'}
      </button>
    </div>
  )
}

/** The person's own password: the current one (and a code when two-step verification is on) proves it is them.
 *  Used on the first sign-in with a temporary password (`temporary`), and inside the "Change your password" dialog
 *  under Your account, where the dialog's footer holds the buttons (`formId` + `actions`). */
export default function ChangePassword({
  user,
  onDone,
  temporary = false,
  formId,
  actions,
}: {
  user: Me
  onDone: (me: Me) => void
  temporary?: boolean
  /** The form's id, so buttons outside it (a dialog footer) can submit it with `form={formId}`. */
  formId?: string
  /** Replaces the built-in submit button, given whether the form may be submitted now. */
  actions?: (state: { busy: boolean; ready: boolean }) => ReactNode
}) {
  // the gate sends the remembered temporary password silently; after a reload it must be typed once more
  const [remembered, setRemembered] = useState(() => temporary && temporaryPasswordInMemory().length > 0)
  const [current, setCurrent] = useState('')
  const [code, setCode] = useState('')
  const [next, setNext] = useState('')
  const [again, setAgain] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const twoFactor = !!user.two_factor
  const username = user.username ?? ''
  const askCurrent = !remembered
  const okRules = next.length >= 12 && (!username || !next.toLowerCase().includes(username.toLowerCase())) && new Set(next).size >= 5
  const ready = (!askCurrent || current.length > 0) && okRules && next === again && (!twoFactor || code.length > 0)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (next !== again) {
      setMsg('The two new passwords differ.')
      return
    }
    setBusy(true)
    setMsg(null)
    try {
      const me = await api.changePassword(remembered ? temporaryPasswordInMemory() : current, code, next)
      forgetTemporaryPassword()
      setCurrent('')
      setCode('')
      setNext('')
      setAgain('')
      onDone(me)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        if (remembered) {
          // the remembered one no longer opens (the owner reset it meanwhile): ask for it once more
          forgetTemporaryPassword()
          setRemembered(false)
          setMsg('That temporary password no longer works. Type the one you were given once more.')
        } else if (temporary) {
          setMsg(twoFactor ? 'The temporary password or the code is wrong. Try again.' : 'That is not the temporary password you were given. Try again.')
        } else {
          setMsg(twoFactor ? 'The current password or the code is wrong. Try again.' : 'That is not your current password. Try again.')
        }
      } else {
        setMsg((err as Error).message)
      }
    } finally {
      setBusy(false)
    }
  }

  const base = formId ?? 'change-password'
  return (
    <form id={formId} onSubmit={submit} data-testid="change-password">
      {askCurrent && (
        <div className="field">
          <label htmlFor={`${base}-current`}>{temporary ? 'Temporary password' : 'Current password'}</label>
          <PasswordInput id={`${base}-current`} value={current} onChange={setCurrent} autoComplete="current-password" autoFocus testId="current-password" />
          {temporary && <div className="help">Type the temporary password you were given once more.</div>}
        </div>
      )}
      {twoFactor && (
        <div className="field">
          <label htmlFor={`${base}-code`}>Code from your authenticator</label>
          <input id={`${base}-code`} value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="6 digits or a backup code" data-testid="password-code" />
        </div>
      )}
      <div className="field">
        <label htmlFor={`${base}-new`}>New password</label>
        <PasswordInput id={`${base}-new`} value={next} onChange={setNext} autoComplete="new-password" autoFocus={!askCurrent} testId="new-password" />
        <PasswordChecks value={next} username={username} />
      </div>
      <div className="field">
        <label htmlFor={`${base}-again`}>New password again</label>
        <PasswordInput id={`${base}-again`} value={again} onChange={setAgain} autoComplete="new-password" testId="new-password-again" />
        {again.length > 0 && again !== next && <div className="help">Not the same yet.</div>}
      </div>
      {msg && (
        <div className="dlg-error" role="alert" data-testid="password-error">
          {msg}
        </div>
      )}
      {actions ? (
        actions({ busy, ready })
      ) : (
        <button className="primary" type="submit" disabled={busy || !ready}>
          {temporary ? 'Set my password and continue' : 'Change password'}
        </button>
      )}
    </form>
  )
}
