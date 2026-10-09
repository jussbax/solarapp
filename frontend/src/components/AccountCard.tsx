import { useEffect, useState } from 'react'
import { api, type Me, type Passkey } from '../api'
import { fmtDateTime } from '../fmt'
import { createPasskey, passkeyProblem, passkeySupported } from '../passkeys'
import ChangePassword from './ChangePassword'

type Setup = { secret: string; uri: string; qr: string }

/** Settings card: the signed-in person's password, authenticator app, security keys and sessions. */
export default function AccountCard({ user, onUser }: { user: Me; onUser: (me: Me) => void }) {
  const [keys, setKeys] = useState<Passkey[] | null>(null)
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [setup, setSetup] = useState<Setup | null>(null)
  const [setupCode, setSetupCode] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const twoFactor = !!user.two_factor
  const confirm = { password, code }
  const confirmed = password.length > 0 && (!twoFactor || code.length > 0)

  const load = () => {
    api.passkeys().then(setKeys).catch(() => setKeys([]))
  }
  useEffect(load, [])
  const refreshMe = () => api.me().then(onUser).catch(() => undefined)

  const needConfirm = () => {
    setMsg('Enter your password' + (twoFactor ? ' and a fresh code' : '') + ' under "Confirm it\'s you" first.')
  }

  const fail = (err: unknown) => setMsg(err instanceof Error && 'status' in err ? err.message : passkeyProblem(err))

  // --- authenticator app
  const beginTotp = async () => {
    if (!confirmed) return needConfirm()
    setBusy(true)
    setMsg(null)
    try {
      setSetup(await api.totpBegin(confirm))
      setSetupCode('')
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
    }
  }
  const confirmTotp = async () => {
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.totpConfirm(setupCode)
      setSetup(null)
      setSetupCode('')
      setCode('')
      setBackupCodes(r.backup_codes)
      await refreshMe()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
    }
  }
  const disableTotp = async () => {
    if (!confirmed) return needConfirm()
    if (!window.confirm('Turn the authenticator off? Your password alone will open the back office again until you turn it back on.')) return
    setBusy(true)
    setMsg(null)
    try {
      await api.totpDisable(confirm)
      setCode('')
      setBackupCodes(null)
      setMsg('Authenticator turned off.')
      await refreshMe()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
    }
  }

  // --- security keys
  const add = async () => {
    if (!confirmed) return needConfirm()
    setBusy(true)
    setMsg(null)
    try {
      const { challenge_id, options } = await api.passkeyRegisterOptions(confirm)
      const credential = await createPasskey(options)
      const key = await api.passkeyRegister(challenge_id, name || 'Security key', credential)
      setName('')
      setCode('')
      setMsg(`"${key.name}" added. It can sign you in from now on. Add a second key, or keep your backup codes somewhere safe.`)
      load()
      await refreshMe()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
    }
  }
  const remove = async (k: Passkey) => {
    if (!confirmed) return needConfirm()
    if (!window.confirm(`Remove "${k.name}"? It will no longer sign you in.`)) return
    try {
      await api.passkeyDelete(k.id, confirm)
      setCode('')
      setMsg(`"${k.name}" removed.`)
      load()
      await refreshMe()
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
    <div className="card" id="account">
      <h2>Your account</h2>
      <div className="muted" style={{ marginBottom: 8 }}>
        Signed in as <strong>{user.display_name || user.username}</strong> ({user.username}, {user.role === 'owner' ? 'owner' : 'engineer'}).
        {user.role === 'owner' ? ' An owner also manages people, the company profile and pricing.' : ' The owner manages people, the company profile and pricing.'}
      </div>

      <h3>Confirm it's you</h3>
      <div className="muted" style={{ marginBottom: 6 }}>
        Turning the authenticator on or off and adding or removing a key ask for your password{twoFactor ? ' and a fresh code' : ''} again, so a stolen
        session cannot do it.
      </div>
      <div className="row">
        <div className="field">
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" data-testid="confirm-password" />
        </div>
        {twoFactor && (
          <div className="field">
            <label>Authenticator code</label>
            <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="6 digits" data-testid="confirm-code" />
          </div>
        )}
      </div>

      <h3>Authenticator app</h3>
      {twoFactor ? (
        <>
          <div className="muted">
            On. The password alone no longer opens the back office; a 6-digit code or a backup code is needed too.
            {typeof user.backup_codes_left === 'number' && ` ${user.backup_codes_left} backup code${user.backup_codes_left === 1 ? '' : 's'} left.`}
          </div>
          <div style={{ marginTop: 8 }}>
            <button className="danger" type="button" disabled={busy} onClick={disableTotp} data-testid="totp-disable">
              Turn the authenticator off
            </button>
          </div>
        </>
      ) : setup ? (
        <div className="banner info" data-testid="totp-setup">
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <img src={setup.qr} alt="QR code for the authenticator app" width={168} height={168} style={{ background: '#fff', borderRadius: 6 }} />
            <div style={{ flex: '1 1 220px' }}>
              <div>
                Scan this with Google Authenticator, Microsoft Authenticator, Aegis or 1Password. If scanning is not possible, enter the key by hand:
              </div>
              <code style={{ display: 'block', margin: '6px 0', wordBreak: 'break-all' }}>{setup.secret}</code>
              <div className="field" style={{ marginTop: 8 }}>
                <label>Then the 6-digit code it shows</label>
                <input value={setupCode} onChange={(e) => setSetupCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="6 digits" data-testid="totp-setup-code" />
              </div>
              <div className="row">
                <button className="primary narrow" type="button" disabled={busy || setupCode.trim().length < 6} onClick={confirmTotp} data-testid="totp-confirm">
                  Turn the authenticator on
                </button>
                <button className="narrow" type="button" disabled={busy} onClick={() => setSetup(null)}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="banner warn">Off. Your password alone opens the back office. Turn it on: an authenticator app on your phone adds a code that changes every 30 seconds.</div>
          <div style={{ marginTop: 8 }}>
            <button className="primary" type="button" disabled={busy} onClick={beginTotp} data-testid="totp-begin">
              Set up the authenticator app
            </button>
          </div>
        </>
      )}
      {backupCodes && (
        <div className="banner info" style={{ marginTop: 10 }} data-testid="backup-codes">
          <strong>Authenticator on. These backup codes are shown once.</strong> Write them down or keep them in a password manager; each signs you in one time if the
          phone is lost.
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 4, margin: '8px 0' }}>
            {backupCodes.map((c) => (
              <code key={c}>{c}</code>
            ))}
          </div>
          <button type="button" className="small" onClick={() => setBackupCodes(null)}>
            I have saved them
          </button>
        </div>
      )}

      <h3>Security keys and passkeys</h3>
      <div className="muted" style={{ marginBottom: 8 }}>
        A hardware key (YubiKey or similar) or a passkey on your phone signs you in with one touch, no password and no code. Its PIN or fingerprint is
        the second factor, and it only works on this exact address, so a look-alike site gets nothing.
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
        <div className="row" style={{ marginTop: 8 }}>
          <div className="field">
            <label>Name for the new key</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. YubiKey on the keyring, or My phone" maxLength={60} />
          </div>
          <button className="primary narrow" type="button" disabled={busy} onClick={add} data-testid="add-passkey">
            Add a security key
          </button>
        </div>
      )}
      {msg && (
        <div className="banner info" style={{ marginTop: 10 }} data-testid="account-msg">
          {msg}
        </div>
      )}

      <h3>Password</h3>
      <ChangePassword user={user} onDone={onUser} />

      <h3>Lost a phone or laptop?</h3>
      <div className="muted" style={{ marginBottom: 8 }}>
        Signing out everywhere ends every session of yours at once. Then check the key list above and remove any key you do not recognize. If the phone
        with the authenticator is gone and you have no backup code, the owner resets your authenticator under People.
      </div>
      <button className="danger" type="button" onClick={signOutEverywhere} data-testid="signout-everywhere">
        Sign out everywhere
      </button>
    </div>
  )
}
