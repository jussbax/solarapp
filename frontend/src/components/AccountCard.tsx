import { useEffect, useId, useState } from 'react'
import { api, type Me, type Passkey } from '../api'
import { fmtDateShort } from '../fmt'
import { createPasskey, passkeyProblem, passkeySupported } from '../passkeys'
import ChangePassword, { PasswordInput } from './ChangePassword'
import { stepUpProblem, useToast } from '../accounts'
import { CopyBox, CopyButton, Dialog } from './Dialog'
import { useNarrow } from './responsive'
import '../accounts.css'

type Setup = { secret: string; uri: string; qr: string }
type Open = 'password' | 'totp' | 'totp-off' | 'add-key' | 'signout' | { kind: 'remove-key'; key: Passkey } | null

/** "added 9 Oct · last used today". */
function keyMeta(k: Passkey): string {
  const parts: string[] = []
  if (k.created_at) parts.push(`added ${fmtDateShort(k.created_at)}`)
  if (k.last_used_at) {
    const d = new Date(k.last_used_at)
    parts.push(d.toDateString() === new Date().toDateString() ? 'last used today' : `last used ${fmtDateShort(k.last_used_at)}`)
  } else parts.push('never used')
  return parts.join(' · ')
}

/** Settings › Your account: password, two-step verification, security keys and devices, each one row; the password
 *  (and a fresh code when two-step is on) is asked inside the dialog at the moment of the action. */
export default function AccountCard({ user, onUser, heading = true }: { user: Me; onUser: (me: Me) => void; heading?: boolean }) {
  const [keys, setKeys] = useState<Passkey[] | null>(null)
  const [open, setOpen] = useState<Open>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [keyName, setKeyName] = useState('')
  // the two-step set-up: confirm, scan, keep the backup codes
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [setup, setSetup] = useState<Setup | null>(null)
  const [setupCode, setSetupCode] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [saved, setSaved] = useState(false)
  const { toast, show } = useToast()
  const narrow = useNarrow()
  const twoFactor = !!user.two_factor
  const switchId = useId()
  const twoStepTitle = useId()

  const loadKeys = () => api.passkeys().then(setKeys).catch(() => setKeys([]))
  useEffect(() => {
    loadKeys()
  }, [])
  const refreshMe = () => api.me().then(onUser).catch(() => undefined)

  const start = (o: Open) => {
    setError(null)
    setPassword('')
    setCode('')
    setStep(1)
    setSetup(null)
    setSetupCode('')
    setBackupCodes([])
    setSaved(false)
    if (o === 'add-key') setKeyName(narrow ? 'This phone' : 'Security key')
    setOpen(o)
  }
  const close = () => {
    // Escape at the last step: the server already has two-step on, so the switch follows it
    if (open === 'totp' && step === 3) refreshMe()
    setOpen(null)
    setError(null)
    setPassword('')
    setCode('')
  }

  /** Runs one action; a refusal prints inside the dialog, which stays open. */
  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(err instanceof Error && 'status' in err ? stepUpProblem(err, twoFactor) : passkeyProblem(err))
    } finally {
      setBusy(false)
    }
  }
  const confirm = { password, code }

  // --- two-step verification
  const totpBegin = () =>
    run(async () => {
      setSetup(await api.totpBegin(confirm))
      setSetupCode('')
      setStep(2)
    })
  const totpConfirm = () =>
    run(async () => {
      const r = await api.totpConfirm(setupCode.trim())
      setBackupCodes(r.backup_codes)
      setStep(3)
    })
  // Done wakes up after Copy or Download, or after five seconds
  useEffect(() => {
    if (open !== 'totp' || step !== 3) return
    const t = window.setTimeout(() => setSaved(true), 5000)
    return () => window.clearTimeout(t)
  }, [open, step])
  const totpDone = async () => {
    await refreshMe()
    setOpen(null)
    show('Two-step verification is on.')
  }
  const totpDisable = () =>
    run(async () => {
      await api.totpDisable(confirm)
      await refreshMe()
      setOpen(null)
      show('Two-step verification is off. Your password alone signs you in.')
    })
  const downloadCodes = () => {
    const blob = new Blob([`Backup codes for ${user.username}\nEach signs you in once if the phone is lost.\n\n${backupCodes.join('\n')}\n`], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'backup-codes.txt'
    a.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    setSaved(true)
  }

  // --- security keys
  const addKey = () =>
    run(async () => {
      const { challenge_id, options } = await api.passkeyRegisterOptions(confirm)
      const credential = await createPasskey(options)
      const key = await api.passkeyRegister(challenge_id, keyName.trim() || 'Security key', credential)
      await loadKeys()
      await refreshMe()
      setOpen(null)
      show(`${key.name} added.`)
    })
  const removeKey = (k: Passkey) =>
    run(async () => {
      await api.passkeyDelete(k.id, confirm)
      await loadKeys()
      await refreshMe()
      setOpen(null)
      show(`${k.name} removed.`)
    })

  const signOutEverywhere = () =>
    run(async () => {
      await api.signOutEverywhere()
      window.location.assign('/login')
    })

  const supported = passkeySupported()
  const insecure = typeof window !== 'undefined' && !window.isSecureContext
  const keysBlocked = !supported ? 'This browser does not support security keys.' : insecure ? 'Keys need https and a real hostname.' : null
  const backupLeft = typeof user.backup_codes_left === 'number' ? user.backup_codes_left : null

  /** The password (and code) fields every step-up dialog asks for. */
  const stepUpFields = (autoFocus = true) => (
    <>
      <div className="field">
        <label htmlFor="stepup-password">Password</label>
        <PasswordInput id="stepup-password" value={password} onChange={setPassword} autoComplete="current-password" autoFocus={autoFocus} testId="stepup-password" />
      </div>
      {twoFactor && (
        <div className="field">
          <label htmlFor="stepup-code">Code from your authenticator</label>
          <input id="stepup-code" value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="6 digits or a backup code" data-testid="stepup-code" />
        </div>
      )}
    </>
  )
  const stepUpReady = password.length > 0 && (!twoFactor || code.trim().length > 0)
  const errorBox = error && (
    <div className="dlg-error" role="alert" data-testid="dialog-error">
      {error}
    </div>
  )
  const cancel = (
    <button type="button" onClick={close}>
      Cancel
    </button>
  )

  return (
    <div className="card settings-section" id="account" data-testid="section-account">
      {heading && <h2>Your account</h2>}
      <div className="acct-head" data-testid="account-head">
        {user.display_name || user.username} · {user.username} · {user.role === 'owner' ? 'Owner' : 'Engineer'}
      </div>

      <div className="acct-section">
        <div className="acct-row">
          <div className="acct-main">
            <h3>Password</h3>
            <div className="acct-line">Changing it signs out your other phones and laptops.</div>
          </div>
          <div className="acct-action">
            <button type="button" onClick={() => start('password')} data-testid="change-password-open">
              Change…
            </button>
          </div>
        </div>
      </div>

      <div className="acct-section">
        <div className="acct-row">
          <div className="acct-main">
            <h3 id={twoStepTitle}>Two-step verification</h3>
            {twoFactor ? (
              <>
                <div className="acct-line">A code from your authenticator app is asked at sign-in.</div>
                {backupLeft !== null && (
                  <div className="acct-line" data-testid="backup-left">
                    {backupLeft} backup code{backupLeft === 1 ? '' : 's'} left
                  </div>
                )}
              </>
            ) : (
              <div className="acct-line">Off. Your password alone signs you in.</div>
            )}
          </div>
          <div className="acct-action">
            <span className="switch-wrap">
              <button
                id={switchId}
                type="button"
                role="switch"
                aria-checked={twoFactor}
                aria-labelledby={twoStepTitle}
                className="switch"
                disabled={busy}
                onClick={() => start(twoFactor ? 'totp-off' : 'totp')}
                data-testid="totp-switch"
              >
                <span className="knob" />
              </button>
              <span className="switch-text" aria-hidden="true">
                {twoFactor ? 'On' : 'Off'}
              </span>
            </span>
          </div>
        </div>
      </div>

      <div className="acct-section">
        <h3>Security keys</h3>
        {keys === null ? (
          <div className="acct-line muted">Loading…</div>
        ) : keys.length === 0 ? (
          <div className="acct-line muted" data-testid="keys-empty">
            No security key yet. A key or your phone's passkey signs you in with one touch.
          </div>
        ) : (
          <ul className="acct-keys" data-testid="keys-list">
            {keys.map((k) => (
              <li key={k.id}>
                <div>
                  <div className="key-name">{k.name}</div>
                  <div className="key-meta">{keyMeta(k)}</div>
                </div>
                <button type="button" className="danger" onClick={() => start({ kind: 'remove-key', key: k })} aria-label={`Remove ${k.name}`}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="acct-add">
          <div style={{ flex: '1 1 auto' }} className="acct-line">
            {keysBlocked}
          </div>
          <button type="button" disabled={!!keysBlocked} onClick={() => start('add-key')} data-testid="add-passkey">
            Add a key…
          </button>
        </div>
      </div>

      <div className="acct-section">
        <div className="acct-row">
          <div className="acct-main">
            <h3>Devices</h3>
            <div className="acct-line">Signed in on this device.</div>
          </div>
          <div className="acct-action">
            <button type="button" className="danger" onClick={() => start('signout')} data-testid="signout-everywhere">
              Sign out everywhere…
            </button>
          </div>
        </div>
      </div>
      {toast}

      {/* Password › Change… */}
      <Dialog open={open === 'password'} title="Change your password" onClose={close} testId="dialog-password">
        <ChangePassword
          user={user}
          formId="change-password-form"
          onDone={(me) => {
            onUser(me)
            setOpen(null)
            show('Password changed. Other phones and laptops were signed out.')
          }}
          actions={({ busy: b, ready }) => (
            <div className="dlg-foot inline">
              {cancel}
              <button type="submit" className="primary" disabled={b || !ready} data-testid="change-password-submit">
                Change password
              </button>
            </div>
          )}
        />
      </Dialog>

      {/* Two-step verification: off → on, three steps in one dialog */}
      <Dialog
        open={open === 'totp'}
        title={step === 1 ? "Confirm it's you" : step === 2 ? 'Scan this with your authenticator app' : 'Two-step verification is on'}
        onClose={close}
        wide={step === 2}
        testId="dialog-totp"
        footer={
          step === 1 ? (
            <>
              {cancel}
              <button type="submit" form="totp-step1" className="primary" disabled={busy || password.length === 0} data-testid="totp-continue">
                Continue
              </button>
            </>
          ) : step === 2 ? (
            <>
              <button type="button" onClick={() => setStep(1)} disabled={busy}>
                Back
              </button>
              <button type="submit" form="totp-step2" className="primary" disabled={busy || setupCode.trim().length < 6} data-testid="totp-confirm">
                Turn on
              </button>
            </>
          ) : (
            <button type="button" className="primary" disabled={!saved} onClick={totpDone} data-testid="totp-done">
              Done
            </button>
          )
        }
      >
        {step === 1 && (
          <form
            id="totp-step1"
            onSubmit={(e) => {
              e.preventDefault()
              if (password) totpBegin()
            }}
          >
            <p className="muted">Your password first, so a stolen session cannot change how you sign in.</p>
            {stepUpFields()}
            {errorBox}
          </form>
        )}
        {step === 2 && setup && (
          <form
            id="totp-step2"
            onSubmit={(e) => {
              e.preventDefault()
              if (setupCode.trim().length >= 6) totpConfirm()
            }}
          >
            <div className="qr-row">
              <img src={setup.qr} alt="QR code for the authenticator app" width={168} height={168} />
              <div className="qr-side">
                <div className="muted">Google Authenticator, Microsoft Authenticator, Aegis or 1Password.</div>
                <div style={{ marginTop: 8 }}>Can't scan? Type this key</div>
                <CopyBox value={setup.secret} small label="Authenticator key" />
              </div>
            </div>
            <div className="field dlg-code">
              <label htmlFor="totp-code">Code it shows now</label>
              <input id="totp-code" value={setupCode} onChange={(e) => setSetupCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="6 digits" maxLength={8} autoFocus data-testid="totp-setup-code" />
            </div>
            {errorBox}
          </form>
        )}
        {step === 3 && (
          <div data-testid="backup-codes">
            <p>These eight backup codes are shown once.</p>
            <div className="codes-grid">
              {backupCodes.map((c) => (
                <code key={c}>{c}</code>
              ))}
            </div>
            <div className="codes-actions">
              <CopyButton value={backupCodes.join('\n')} label="Copy all" onCopied={() => setSaved(true)} />
              <button type="button" onClick={downloadCodes} data-testid="download-codes">
                Download
              </button>
            </div>
            <p className="muted">Each code signs you in once if the phone is lost. Keep them outside the phone.</p>
          </div>
        )}
      </Dialog>

      {/* Two-step verification: on → off */}
      <Dialog
        open={open === 'totp-off'}
        title="Turn off two-step verification?"
        onClose={close}
        testId="dialog-totp-off"
        footer={
          <>
            {cancel}
            <button type="submit" form="totp-off-form" className="danger-fill" disabled={busy || !stepUpReady} data-testid="totp-off-confirm">
              Turn off
            </button>
          </>
        }
      >
        <form
          id="totp-off-form"
          onSubmit={(e) => {
            e.preventDefault()
            if (stepUpReady) totpDisable()
          }}
        >
          <p>Your password alone will sign you in.</p>
          {stepUpFields()}
          {errorBox}
        </form>
      </Dialog>

      {/* Security keys › Add a key… */}
      <Dialog
        open={open === 'add-key'}
        title="Add a security key"
        onClose={close}
        testId="dialog-add-key"
        footer={
          <>
            {cancel}
            <button type="submit" form="add-key-form" className="primary" disabled={busy || !stepUpReady} data-testid="add-key-confirm">
              Add
            </button>
          </>
        }
      >
        <form
          id="add-key-form"
          onSubmit={(e) => {
            e.preventDefault()
            if (stepUpReady) addKey()
          }}
        >
          <div className="field">
            <label htmlFor="key-name">Name</label>
            <input id="key-name" value={keyName} onChange={(e) => setKeyName(e.target.value)} maxLength={60} autoFocus data-testid="key-name" />
            <div className="help">So you know which one to remove if it is lost.</div>
          </div>
          {stepUpFields(false)}
          <p className="muted">Then the browser asks for the key's PIN or your fingerprint and a touch.</p>
          {errorBox}
        </form>
      </Dialog>

      {/* Security keys › Remove */}
      {open !== null && typeof open === 'object' && open.kind === 'remove-key' && (
        <Dialog
          open
          title={`Remove '${open.key.name}'?`}
          onClose={close}
          testId="dialog-remove-key"
          footer={
            <>
              {cancel}
              <button type="submit" form="remove-key-form" className="danger-fill" disabled={busy || !stepUpReady} data-testid="remove-key-confirm">
                Remove
              </button>
            </>
          }
        >
          <form
            id="remove-key-form"
            onSubmit={(e) => {
              e.preventDefault()
              if (stepUpReady) removeKey(open.key)
            }}
          >
            <p>It will no longer sign you in.</p>
            {stepUpFields()}
            {errorBox}
          </form>
        </Dialog>
      )}

      {/* Devices › Sign out everywhere… */}
      <Dialog
        open={open === 'signout'}
        title="Sign out every phone and laptop, including this one?"
        onClose={close}
        testId="dialog-signout"
        footer={
          <>
            {cancel}
            <button type="button" className="danger-fill" disabled={busy} onClick={signOutEverywhere} data-testid="signout-confirm">
              Sign out everywhere
            </button>
          </>
        }
      >
        <p>You sign in again afterwards. If a phone with the authenticator is lost and you have no backup code, the owner can turn two-step off under People.</p>
        {errorBox}
      </Dialog>
    </div>
  )
}
