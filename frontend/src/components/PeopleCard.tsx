import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api, ApiError, type Me, type Person } from '../api'
import { suggestUsername, useToast } from '../accounts'
import { CopyBox, Dialog, Menu, type MenuItem } from './Dialog'
import '../accounts.css'

/** "JD" from "Juan dela Cruz". */
function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  if (words.length === 0) return '?'
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return (words[0][0] + words[words.length - 1][0]).toUpperCase()
}

/** "juan.delacruz2" when juan.delacruz is taken, "juan.delacruz3" after that. */
function nextUsername(taken: string): string {
  const m = /^(.*?)(\d+)$/.exec(taken)
  return m ? `${m[1]}${Number(m[2]) + 1}` : `${taken}2`
}

const USERNAME_OK = /^[a-z0-9][a-z0-9._-]{1,39}$/

/** "signed in today 5:38 AM" · "last signed in 2 Oct, 4:10 PM" · "has not signed in yet". */
function signInFact(iso: string | null): string {
  if (!iso) return 'has not signed in yet'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return `last signed in ${iso}`
  const now = new Date()
  const time = d.toLocaleTimeString('en-PH', { hour: 'numeric', minute: '2-digit' }).replace(' ', '\u00a0') // "6:23 AM" stays on one line
  if (d.toDateString() === now.toDateString()) return `signed in today ${time}`
  const date = d.toLocaleDateString('en-PH', { day: 'numeric', month: 'short', ...(d.getFullYear() !== now.getFullYear() ? { year: 'numeric' } : {}) })
  return `last signed in ${date}, ${time}`
}

const keysText = (n: number) => `${n} security key${n === 1 ? '' : 's'}`

/** The third line of a card: how the person signs in. */
function method(p: Person): { text: string; bad: boolean } {
  if (p.must_change_password) return { text: 'Temporary password', bad: true }
  const parts: string[] = []
  if (p.two_factor) parts.push('Two-step verification on')
  if (p.passkeys > 0) parts.push(keysText(p.passkeys))
  if (parts.length === 0) return { text: 'Password only', bad: false }
  if (!p.two_factor) parts.unshift('Password')
  return { text: parts.join(' · '), bad: false }
}

const firstName = (p: Person) => p.display_name.trim().split(/\s+/)[0] || p.display_name

type Open =
  | { kind: 'add' }
  | { kind: 'secret'; title: string; who: string; password: string }
  | { kind: 'rename'; p: Person }
  | { kind: 'role'; p: Person }
  | { kind: 'reset'; p: Person }
  | { kind: 'twostep'; p: Person }
  | { kind: 'remove'; p: Person }

/** Settings › People, for owners: who can sign in, as a list of person cards; every action is a dialog of the app's own. */
export default function PeopleCard({ me, heading = true }: { me: Me; heading?: boolean }) {
  const [people, setPeople] = useState<Person[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [open, setOpen] = useState<Open | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const { toast, show } = useToast()
  const location = useLocation()
  // the old one-page Settings reaches the account section by its hash; the account page by its route
  const accountHref = location.pathname === '/settings' ? '/settings#account' : '/settings/account'

  // the Add a person form
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [usernameTouched, setUsernameTouched] = useState(false)
  const [role, setRole] = useState<Person['role']>('engineer')
  const [taken, setTaken] = useState<string | null>(null)
  // the Rename form
  const [newName, setNewName] = useState('')

  const load = () => api.users().then(setPeople).catch((e) => setLoadError((e as Error).message))
  useEffect(() => {
    load()
  }, [])

  const close = () => {
    setOpen(null)
    setError(null)
    setTaken(null)
  }
  const start = (o: Open) => {
    setError(null)
    setTaken(null)
    if (o.kind === 'add') {
      setName('')
      setUsername('')
      setUsernameTouched(false)
      setRole('engineer')
    }
    if (o.kind === 'rename') setNewName(o.p.display_name)
    setOpen(o)
  }

  /** Runs one action; the server's refusal prints inside the dialog, never in a banner outside it. */
  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    setError(null)
    try {
      await fn()
      await load()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const usernameValid = USERNAME_OK.test(username)
  const add = (e: FormEvent) => {
    e.preventDefault()
    if (!usernameValid) return
    run(async () => {
      try {
        const p = await api.createUser(username, name.trim(), role)
        setOpen({ kind: 'secret', title: `${p.display_name} is added`, who: p.display_name, password: p.temporary_password })
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          setTaken(nextUsername(username))
          return
        }
        throw err
      }
    })
  }
  const rename = (e: FormEvent, p: Person) => {
    e.preventDefault()
    const next = newName.trim()
    if (!next) return
    run(async () => {
      await api.patchUser(p.id, { display_name: next })
      setOpen(null)
      show(`Renamed to ${next}.`)
    })
  }
  const setRoleOf = (p: Person) => {
    const next: Person['role'] = p.role === 'owner' ? 'engineer' : 'owner'
    run(async () => {
      await api.patchUser(p.id, { role: next })
      setOpen(null)
      show(`${p.display_name} is now ${next === 'owner' ? 'an owner' : 'an engineer'}.`)
    })
  }
  const resetPassword = (p: Person) =>
    run(async () => {
      const r = await api.resetUserPassword(p.id)
      setOpen({ kind: 'secret', title: `New temporary password for ${r.display_name}`, who: r.display_name, password: r.temporary_password })
    })
  const turnOffTwoStep = (p: Person) =>
    run(async () => {
      await api.resetUserAuthenticator(p.id)
      setOpen(null)
      show(`Two-step verification is off for ${p.display_name}.`)
    })
  const removeAccess = (p: Person) =>
    run(async () => {
      await api.patchUser(p.id, { active: false })
      setOpen(null)
      show(`${p.display_name}'s access is removed.`)
    })
  const restoreAccess = (p: Person) =>
    run(async () => {
      await api.patchUser(p.id, { active: true })
      show(`${p.display_name} can sign in again.`)
    })

  const menuFor = (p: Person): MenuItem[] => {
    if (!p.active) return [{ label: 'Restore access', onSelect: () => restoreAccess(p) }]
    const items: MenuItem[] = [
      { label: 'Rename…', onSelect: () => start({ kind: 'rename', p }) },
      { label: p.role === 'owner' ? 'Make an engineer' : 'Make an owner', onSelect: () => start({ kind: 'role', p }) },
      { label: 'Reset password…', onSelect: () => start({ kind: 'reset', p }) },
    ]
    if (p.two_factor || p.passkeys > 0) items.push({ label: 'Turn off two-step verification…', onSelect: () => start({ kind: 'twostep', p }) })
    items.push({ label: 'Remove access…', onSelect: () => start({ kind: 'remove', p }), danger: true })
    return items
  }

  const sorted = people ? [...people.filter((p) => p.active), ...people.filter((p) => !p.active)] : []
  const onlyMe = people !== null && people.length === 1 && people[0].username === me.username
  const addButton = (
    <button type="button" className="primary" onClick={() => start({ kind: 'add' })} data-testid="add-person">
      Add a person
    </button>
  )

  /** What "Turn off two-step verification" removes for this person, in words. */
  const removed = (p: Person) => {
    const what: string[] = []
    if (p.two_factor) what.push('their authenticator app')
    if (p.passkeys > 0) what.push(keysText(p.passkeys))
    const text = what.join(' and ')
    return `${text.charAt(0).toUpperCase()}${text.slice(1)} ${what.length > 1 || p.passkeys > 1 ? 'are' : 'is'} removed.`
  }

  return (
    <div className="card settings-section" id="people" data-testid="section-people">
      <div className="people-head">
        <div>
          {heading && <h2>People</h2>}
          <div className="lead">Who can sign in to the back office.</div>
        </div>
        {addButton}
      </div>
      {loadError && <div className="banner bad">{loadError}</div>}
      {people === null && !loadError ? (
        <div className="muted">Loading…</div>
      ) : (
        <div className="people-list" data-testid="people-list">
          {sorted.map((p) => {
            const self = p.username === me.username
            const m = method(p)
            return (
              <div key={p.id} className={`person ${p.active ? '' : 'removed'} ${self ? 'self' : ''}`.replace(/\s+/g, ' ').trim()} data-testid={`person-${p.username}`}>
                <div className="avatar" aria-hidden="true">
                  {initials(p.display_name)}
                </div>
                <div className="person-top">
                  <span className="person-name">{p.display_name}</span>
                  {self && <span className="person-you">(you)</span>}
                  <span className={`badge ${p.role === 'owner' ? 'gold' : 'neutral'}`}>{p.role === 'owner' ? 'Owner' : 'Engineer'}</span>
                </div>
                <div className="person-line">
                  {p.username} · {p.active ? signInFact(p.last_login_at) : 'access removed'}
                </div>
                {p.active && <div className={`person-line ${m.bad ? 'bad' : ''}`.trim()}>{m.bad ? <span className="bad">{m.text}</span> : m.text}</div>}
                <div className="person-side">
                  {self ? (
                    <Link to={accountHref} data-testid="your-account-link">
                      Your account ›
                    </Link>
                  ) : (
                    <Menu label={`Actions for ${p.display_name}`} title={p.display_name} items={menuFor(p)} testId={`menu-${p.username}`} />
                  )}
                </div>
              </div>
            )
          })}
          {onlyMe && (
            <div className="people-empty" data-testid="people-empty">
              <div>Only you so far. Add an engineer so they can open projects on their own phone.</div>
              {addButton}
            </div>
          )}
        </div>
      )}
      {error && !open && <div className="banner bad" style={{ marginTop: 10 }}>{error}</div>}
      {toast}

      {/* Add a person, step 1 */}
      <Dialog
        open={open?.kind === 'add'}
        title="Add a person"
        onClose={close}
        tall
        testId="dialog-add"
        footer={
          <>
            <button type="button" onClick={close}>
              Cancel
            </button>
            <button type="submit" form="add-person-form" className="primary" disabled={busy || name.trim().length === 0 || !usernameValid} data-testid="add-submit">
              Add
            </button>
          </>
        }
      >
        <form id="add-person-form" onSubmit={add}>
          <div className="field">
            <label htmlFor="add-name">Name</label>
            <input
              id="add-name"
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                if (!usernameTouched) setUsername(suggestUsername(e.target.value))
                setTaken(null)
              }}
              placeholder="Juan dela Cruz"
              maxLength={80}
              autoComplete="off"
              autoFocus
              data-testid="add-name"
            />
          </div>
          <div className="field">
            <label htmlFor="add-username">Username</label>
            <input
              id="add-username"
              value={username}
              onChange={(e) => {
                setUsernameTouched(true)
                setUsername(e.target.value.toLowerCase())
                setTaken(null)
              }}
              maxLength={40}
              autoComplete="off"
              autoCapitalize="none"
              spellCheck={false}
              data-testid="add-username"
            />
            {taken ? (
              <div className="taken" role="alert" data-testid="username-taken">
                Taken; try{' '}
                <button
                  type="button"
                  onClick={() => {
                    setUsernameTouched(true)
                    setUsername(taken)
                    setTaken(null)
                  }}
                >
                  {taken}
                </button>
              </div>
            ) : (
              <div className="help">What they type to sign in</div>
            )}
          </div>
          <div className="field">
            <div className="field-head">
              <span className="field-label">Role</span>
            </div>
            <div className="role-tiles" role="radiogroup" aria-label="Role">
              <label className="role-tile">
                <input type="radio" name="add-role" value="engineer" checked={role === 'engineer'} onChange={() => setRole('engineer')} />
                <span className="role-name">Engineer</span>
                <span className="role-what">Projects, calculations and documents</span>
              </label>
              <label className="role-tile">
                <input type="radio" name="add-role" value="owner" checked={role === 'owner'} onChange={() => setRole('owner')} />
                <span className="role-name">Owner</span>
                <span className="role-what">Everything, including pricing, materials and people</span>
              </label>
            </div>
          </div>
          {error && (
            <div className="dlg-error" role="alert" data-testid="dialog-error">
              {error}
            </div>
          )}
        </form>
      </Dialog>

      {/* The temporary password, shown once: after Add a person (step 2) and after Reset password */}
      {open?.kind === 'secret' && (
        <Dialog
          open
          title={open.title}
          onClose={close}
          testId="dialog-secret"
          footer={
            <button type="button" className="primary" onClick={close} data-testid="secret-done">
              Done
            </button>
          }
        >
          <p>Give them this temporary password in person or by a call, not in the same message as the address.</p>
          <CopyBox value={open.password} label={`Temporary password for ${open.who}`} />
          <p className="muted">They choose their own password at their first sign-in. It opens nothing else.</p>
        </Dialog>
      )}

      {open?.kind === 'rename' && (
        <Dialog
          open
          title={`Rename ${open.p.display_name}`}
          onClose={close}
          testId="dialog-rename"
          footer={
            <>
              <button type="button" onClick={close}>
                Cancel
              </button>
              <button type="submit" form="rename-form" className="primary" disabled={busy || newName.trim().length === 0}>
                Save
              </button>
            </>
          }
        >
          <form id="rename-form" onSubmit={(e) => rename(e, open.p)}>
            <div className="field">
              <label htmlFor="rename-name">Name</label>
              <input id="rename-name" value={newName} onChange={(e) => setNewName(e.target.value)} maxLength={80} autoFocus data-testid="rename-name" />
            </div>
            {error && (
              <div className="dlg-error" role="alert">
                {error}
              </div>
            )}
          </form>
        </Dialog>
      )}

      {open?.kind === 'role' && (
        <Dialog
          open
          title={open.p.role === 'owner' ? `Make ${open.p.display_name} an engineer?` : `Make ${open.p.display_name} an owner?`}
          onClose={close}
          testId="dialog-role"
          footer={
            <>
              <button type="button" onClick={close}>
                Cancel
              </button>
              <button type="button" className="primary" disabled={busy} onClick={() => setRoleOf(open.p)} data-testid="role-confirm">
                {open.p.role === 'owner' ? 'Make an engineer' : 'Make an owner'}
              </button>
            </>
          }
        >
          <p>
            {open.p.role === 'owner'
              ? 'They keep projects and documents and lose Settings, Materials and People.'
              : `Owners change pricing, materials and people. ${firstName(open.p)} keeps every project.`}
          </p>
          {error && (
            <div className="dlg-error" role="alert">
              {error}
            </div>
          )}
        </Dialog>
      )}

      {open?.kind === 'reset' && (
        <Dialog
          open
          title={`Reset ${open.p.display_name}'s password?`}
          onClose={close}
          testId="dialog-reset"
          footer={
            <>
              <button type="button" onClick={close}>
                Cancel
              </button>
              <button type="button" className="primary" disabled={busy} onClick={() => resetPassword(open.p)} data-testid="reset-confirm">
                Reset password
              </button>
            </>
          }
        >
          <p>They are signed out everywhere and get a temporary password to change at their next sign-in.</p>
          {error && (
            <div className="dlg-error" role="alert">
              {error}
            </div>
          )}
        </Dialog>
      )}

      {open?.kind === 'twostep' && (
        <Dialog
          open
          title={`Turn off two-step verification for ${open.p.display_name}?`}
          onClose={close}
          testId="dialog-twostep"
          footer={
            <>
              <button type="button" onClick={close}>
                Cancel
              </button>
              <button type="button" className="primary" disabled={busy} onClick={() => turnOffTwoStep(open.p)} data-testid="twostep-confirm">
                Turn off
              </button>
            </>
          }
        >
          <p>
            {removed(open.p)} Their password alone signs them in until they set them up again under Your account.
          </p>
          {error && (
            <div className="dlg-error" role="alert">
              {error}
            </div>
          )}
        </Dialog>
      )}

      {open?.kind === 'remove' && (
        <Dialog
          open
          title={`Remove ${open.p.display_name}'s access?`}
          onClose={close}
          testId="dialog-remove"
          footer={
            <>
              <button type="button" onClick={close}>
                Cancel
              </button>
              <button type="button" className="danger-fill" disabled={busy} onClick={() => removeAccess(open.p)} data-testid="remove-confirm">
                Remove access
              </button>
            </>
          }
        >
          <p>They are signed out everywhere and cannot sign in. Their projects stay.</p>
          {error && (
            <div className="dlg-error" role="alert">
              {error}
            </div>
          )}
        </Dialog>
      )}
    </div>
  )
}
