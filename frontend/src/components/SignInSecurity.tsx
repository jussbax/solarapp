import { useEffect, useState } from 'react'
import { api, type Passkey } from '../api'
import { fmtDateTime } from '../fmt'
import { createPasskey, passkeyProblem, passkeySupported } from '../passkeys'

/** Settings card: the authenticator code status and the registered security keys. */
export default function SignInSecurity() {
  const [keys, setKeys] = useState<Passkey[] | null>(null)
  const [twoFactor, setTwoFactor] = useState<boolean | null>(null)
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const confirm = { password, code }
  const confirmed = password.length > 0 && (!twoFactor || code.length > 0)

  const load = () => {
    api.passkeys().then(setKeys).catch(() => setKeys([]))
    api.me().then((m) => setTwoFactor(!!m.two_factor)).catch(() => setTwoFactor(null))
  }
  useEffect(load, [])

  const add = async () => {
    setBusy(true)
    setMsg(null)
    try {
      const { challenge_id, options } = await api.passkeyRegisterOptions(confirm)
      const credential = await createPasskey(options)
      const key = await api.passkeyRegister(confirm, challenge_id, name || 'Security key', credential)
      setName('')
      setCode('')
      setMsg(`"${key.name}" added. It can sign you in from now on.`)
      load()
    } catch (err) {
      setMsg(err instanceof Error && 'status' in err ? err.message : passkeyProblem(err))
    } finally {
      setBusy(false)
    }
  }

  const remove = async (k: Passkey) => {
    if (!confirmed) {
      setMsg('Enter your password' + (twoFactor ? ' and a fresh code' : '') + ' below first, then press Remove.')
      return
    }
    if (!window.confirm(`Remove "${k.name}"? It will no longer sign you in.`)) return
    try {
      await api.passkeyDelete(k.id, confirm)
      setCode('')
      setMsg(`"${k.name}" removed.`)
      load()
    } catch (err) {
      setMsg((err as Error).message)
    }
  }

  const signOutEverywhere = async () => {
    if (!window.confirm('Sign out every phone and laptop, including this one? You sign in again afterwards.')) return
    try {
      await api.signOutEverywhere()
      window.location.assign('/login')
    } catch (err) {
      setMsg((err as Error).message)
    }
  }

  const insecure = typeof window !== 'undefined' && !window.isSecureContext

  return (
    <div className="card">
      <h2>Sign-in security</h2>
      <h3>Authenticator code</h3>
      {twoFactor === null ? (
        <div className="muted">Can't read the status right now.</div>
      ) : twoFactor ? (
        <div className="muted">On. The password alone no longer opens the back office; a 6-digit code or a backup code is needed too.</div>
      ) : (
        <div className="banner warn">
          Off. On the server run <code>python -m solarapp.twofactor setup</code> and scan the QR code with an authenticator app.
        </div>
      )}
      <h3>Security keys and passkeys</h3>
      <div className="muted" style={{ marginBottom: 8 }}>
        A hardware key (YubiKey or similar) or a passkey on your phone signs you in with one touch, no password and no code. Its PIN or
        fingerprint is the second factor, and it only works on this exact address, so a look-alike site gets nothing.
      </div>
      {keys === null ? (
        <div className="muted">Loading…</div>
      ) : keys.length === 0 ? (
        <div className="muted">No key registered yet.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Added</th>
              <th>Last used</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k.id}>
                <td>
                  {k.name}
                  {k.backed_up && <span className="muted"> (synced passkey)</span>}
                </td>
                <td>{k.created_at ? fmtDateTime(k.created_at) : '-'}</td>
                <td>{k.last_used_at ? fmtDateTime(k.last_used_at) : 'never'}</td>
                <td>
                  <button className="danger" type="button" onClick={() => remove(k)}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!passkeySupported() ? (
        <div className="muted">This browser does not support passkeys.</div>
      ) : insecure ? (
        <div className="muted">Passkeys need https and a real hostname. Open the back office by its name to add one.</div>
      ) : (
        <>
          <h3>Confirm it's you</h3>
          <div className="muted" style={{ marginBottom: 6 }}>
            Adding or removing a key asks for your password{twoFactor ? ' and a fresh code' : ''} again, so a stolen session cannot do it.
          </div>
          <div className="row">
            <div className="field">
              <label>Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </div>
            {twoFactor && (
              <div className="field">
                <label>Authenticator code</label>
                <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="6 digits" />
              </div>
            )}
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <div className="field">
              <label>Name for the new key</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. YubiKey on the keyring, or My phone" maxLength={60} />
            </div>
            <button className="primary narrow" type="button" disabled={busy || !confirmed} onClick={add} data-testid="add-passkey">
              Add a security key
            </button>
          </div>
        </>
      )}
      {msg && <div className="banner info" style={{ marginTop: 10 }}>{msg}</div>}
      <h3>Lost a phone or laptop?</h3>
      <div className="muted" style={{ marginBottom: 8 }}>
        Signing out everywhere ends every session at once. Then check the key list above and remove any key you do not recognise.
      </div>
      <button className="danger" type="button" onClick={signOutEverywhere} data-testid="signout-everywhere">
        Sign out everywhere
      </button>
    </div>
  )
}
