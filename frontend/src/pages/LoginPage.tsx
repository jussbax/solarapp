import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'

export default function LoginPage({ onLogin }: { onLogin: (user: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [twoFactor, setTwoFactor] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .me()
      .then((m) => setTwoFactor(!!m.two_factor))
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

  return (
    <form className="card login" onSubmit={submit}>
      <div className="logo">
        <img src="/brand/logo-mark.png" alt="PL Development" />
        <span className="name">PL Development</span>
        <span className="tag">Solar assessment</span>
      </div>
      <h2>Sign in</h2>
      <div className="field">
        <label>Username</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus autoComplete="username" />
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
      {error && <div className="banner bad">{error}</div>}
      <button className="primary" disabled={busy} type="submit">
        Sign in
      </button>
    </form>
  )
}
