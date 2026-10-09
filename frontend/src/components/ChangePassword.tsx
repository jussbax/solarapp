import { useState, type FormEvent } from 'react'
import { api, type Me } from '../api'

export const PASSWORD_RULE = 'At least 12 characters. A short sentence you will remember works well; it must not contain your username.'

/** The person's own password: the current one (and a code when the authenticator is on) proves it is them.
 *  Used on the first sign-in with a temporary password, and under Your account. */
export default function ChangePassword({ user, onDone, temporary = false }: { user: Me; onDone: (me: Me) => void; temporary?: boolean }) {
  const [current, setCurrent] = useState('')
  const [code, setCode] = useState('')
  const [next, setNext] = useState('')
  const [again, setAgain] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const twoFactor = !!user.two_factor
  const ready = current.length > 0 && next.length > 0 && next === again && (!twoFactor || code.length > 0)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (next !== again) {
      setMsg('The two new passwords differ.')
      return
    }
    setBusy(true)
    setMsg(null)
    try {
      const me = await api.changePassword(current, code, next)
      setCurrent('')
      setCode('')
      setNext('')
      setAgain('')
      setMsg(temporary ? null : 'Password changed. Every other phone or laptop was signed out; this one stays in.')
      onDone(me)
    } catch (err) {
      setMsg((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} data-testid="change-password">
      <div className="field">
        <label>{temporary ? 'Temporary password' : 'Current password'}</label>
        <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" autoFocus={temporary} />
      </div>
      {twoFactor && (
        <div className="field">
          <label>Code from your authenticator app</label>
          <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="6 digits, or a backup code" />
        </div>
      )}
      <div className="field">
        <label>New password</label>
        <input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
        <div className="hint">{PASSWORD_RULE}</div>
      </div>
      <div className="field">
        <label>New password again</label>
        <input type="password" value={again} onChange={(e) => setAgain(e.target.value)} autoComplete="new-password" />
      </div>
      {msg && <div className={`banner ${/changed/.test(msg) ? 'info' : 'bad'}`}>{msg}</div>}
      <button className="primary" type="submit" disabled={busy || !ready}>
        {temporary ? 'Set my password and continue' : 'Change password'}
      </button>
    </form>
  )
}
