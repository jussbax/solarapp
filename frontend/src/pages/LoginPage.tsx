import { useEffect, useState, type FormEvent } from 'react'
import { api, type Me } from '../api'
import { getPasskey, passkeyProblem, passkeySupported } from '../passkeys'
import Field from '../components/Field'
import { rememberTemporaryPassword } from '../accounts'

type Method = 'key' | 'password'
const METHOD_KEY = 'login-method'

/** The method that last signed in on this device, so a laptop without a key opens on the password form. */
function rememberedMethod(): Method | null {
  try {
    const v = localStorage.getItem(METHOD_KEY)
    return v === 'key' || v === 'password' ? v : null
  } catch {
    return null
  }
}
function rememberMethod(m: Method) {
  try {
    localStorage.setItem(METHOD_KEY, m)
  } catch {
    /* private window or storage blocked: the next visit just opens on the default */
  }
}

export default function LoginPage({ onLogin }: { onLogin: (me: Me) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [twoFactor, setTwoFactor] = useState(false)
  const [passkeys, setPasskeys] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [method, setMethod] = useState<Method>(() => rememberedMethod() ?? 'key')

  useEffect(() => {
    api
      .me()
      .then((m) => {
        setTwoFactor(!!m.two_factor)
        setPasskeys(!!m.passkeys && passkeySupported())
      })
      .catch(() => setTwoFactor(false))
  }, [])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const r = await api.login(username, password, code)
      // a temporary password is kept in memory for the first-sign-in gate, so the person is not asked to type it again
      if (r.must_change_password) rememberTemporaryPassword(password)
      rememberMethod('password')
      onLogin(r)
    } catch (err) {
      const msg = (err as Error).message
      setError(msg)
      if (/code/i.test(msg)) setTwoFactor(true)
    } finally {
      setBusy(false)
    }
  }

  const withKey = async () => {
    setBusy(true)
    setError(null)
    try {
      const { challenge_id, options } = await api.passkeyLoginOptions()
      const credential = await getPasskey(options)
      const r = await api.passkeyLogin(challenge_id, credential)
      rememberMethod('key')
      onLogin(r)
    } catch (err) {
      setError(err instanceof Error && 'status' in err ? err.message : passkeyProblem(err))
    } finally {
      setBusy(false)
    }
  }

  // no key registered (or no support here): the password form is the only way in
  const passwordForm = !passkeys || method === 'password'

  return (
    <form className="card login" onSubmit={submit}>
      <div className="logo">
        <img src="/brand/logo-mark.png" alt="PL Development" />
        <span className="name">PL Development</span>
        <span className="tag">Solar engineering</span>
      </div>
      <h2>Sign in</h2>
      {passkeys && !passwordForm && (
        <div className="passkey-box alone">
          <button className="primary" type="button" disabled={busy} onClick={withKey} data-testid="passkey-login">
            Sign in with your security key
          </button>
          <div className="hint">Plug in the key or hold it to the phone, then touch it and enter its PIN.</div>
          <button className="alt" type="button" disabled={busy} onClick={() => setMethod('password')} data-testid="use-password">
            Use the password instead
          </button>
        </div>
      )}
      {passwordForm && (
        <>
          <Field label="Username">{(id) => <input id={id} value={username} onChange={(e) => setUsername(e.target.value)} autoFocus autoComplete="username" />}</Field>
          <Field label="Password">{(id) => <input id={id} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />}</Field>
          {twoFactor && (
            <Field label="Code from your authenticator app">
              {(id) => <input id={id} value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="6 digits, or a backup code" />}
            </Field>
          )}
        </>
      )}
      {error && <div className="banner bad">{error}</div>}
      {passwordForm && (
        <button className="primary" disabled={busy} type="submit">
          Sign in
        </button>
      )}
      {passwordForm && passkeys && (
        <button className="alt" type="button" disabled={busy} onClick={() => setMethod('key')} data-testid="use-passkey">
          Sign in with a security key instead
        </button>
      )}
    </form>
  )
}
