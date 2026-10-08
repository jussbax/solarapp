import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { getPasskey, passkeyProblem, passkeySupported } from '../passkeys'

export default function LoginPage({ onLogin }: { onLogin: (user: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [twoFactor, setTwoFactor] = useState(false)
  const [passkeys, setPasskeys] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

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
      onLogin(r.username)
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
      onLogin(r.username)
    } catch (err) {
      setError(err instanceof Error && 'status' in err ? err.message : passkeyProblem(err))
    } finally {
      setBusy(false)
    }
  }

  const passwordForm = !passkeys || showPassword

  return (
    <form className="card login" onSubmit={submit}>
      <div className="logo">
        <img src="/brand/logo-mark.png" alt="PL Development" />
        <span className="name">PL Development</span>
        <span className="tag">Solar assessment</span>
      </div>
      <h2>Sign in</h2>
      {passkeys && (
        <div className={passwordForm ? "passkey-box" : "passkey-box alone"}>
          <button className="primary" type="button" disabled={busy} onClick={withKey} data-testid="passkey-login">
            Sign in with your security key
          </button>
          <div className="hint">Plug in the key or hold it to the phone, then touch it and enter its PIN.</div>
          {!showPassword && (
            <button className="toggle link" type="button" onClick={() => setShowPassword(true)}>
              Use the password instead
            </button>
          )}
        </div>
      )}
      {passwordForm && (
        <>
          <div className="field">
            <label>Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus={!passkeys} autoComplete="username" />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </div>
          {twoFactor && (
            <div className="field">
              <label>Code from your authenticator app</label>
              <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="6 digits, or a backup code" />
            </div>
          )}
        </>
      )}
      {error && <div className="banner bad">{error}</div>}
      {passwordForm && (
        <button className="primary" disabled={busy} type="submit">
          Sign in
        </button>
      )}
    </form>
  )
}
