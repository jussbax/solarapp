import { useEffect, useState, type FormEvent } from 'react'
import { api, type Me, type Person } from '../api'
import { fmtDateTime } from '../fmt'

/** Settings card for owners: who may sign in. A new person gets a temporary password, shown once. */
export default function PeopleCard({ me }: { me: Me }) {
  const [people, setPeople] = useState<Person[] | null>(null)
  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [role, setRole] = useState<Person['role']>('engineer')
  const [secret, setSecret] = useState<{ who: string; password: string } | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = () => {
    api.users().then(setPeople).catch((e) => setError((e as Error).message))
  }
  useEffect(load, [])

  const run = async (fn: () => Promise<unknown>, done?: string) => {
    setBusy(true)
    setError(null)
    setMsg(null)
    try {
      await fn()
      if (done) setMsg(done)
      load()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const add = (e: FormEvent) => {
    e.preventDefault()
    run(async () => {
      const p = await api.createUser(username.trim().toLowerCase(), displayName.trim(), role)
      setSecret({ who: p.display_name, password: p.temporary_password })
      setUsername('')
      setDisplayName('')
      setRole('engineer')
    })
  }
  const resetPassword = (p: Person) => {
    if (!window.confirm(`Give ${p.display_name} a new temporary password? Their other sessions end and they must change it at sign-in.`)) return
    run(async () => {
      const r = await api.resetUserPassword(p.id)
      setSecret({ who: r.display_name, password: r.temporary_password })
    })
  }
  const resetAuthenticator = (p: Person) => {
    if (!window.confirm(`Turn off the authenticator and remove every security key of ${p.display_name}? They sign in with the password alone and set them up again.`)) return
    run(() => api.resetUserAuthenticator(p.id), `Authenticator and keys reset for ${p.display_name}.`)
  }
  const setActive = (p: Person, active: boolean) => {
    if (!active && !window.confirm(`Deactivate ${p.display_name}? They are signed out everywhere and cannot sign in until reactivated.`)) return
    run(() => api.patchUser(p.id, { active }), `${p.display_name} ${active ? 'reactivated' : 'deactivated'}.`)
  }
  const rename = (p: Person) => {
    const next = window.prompt(`Name shown in the app for ${p.username}:`, p.display_name)
    if (next === null || next.trim() === '' || next.trim() === p.display_name) return
    run(() => api.patchUser(p.id, { display_name: next.trim() }), `Renamed to ${next.trim()}.`)
  }
  const setRoleOf = (p: Person, next: Person['role']) => {
    if (next === 'owner' && !window.confirm(`Make ${p.display_name} an owner? Owners manage people, the company profile and pricing.`)) return
    run(() => api.patchUser(p.id, { role: next }), `${p.display_name} is now ${next === 'owner' ? 'an owner' : 'an engineer'}.`)
  }

  return (
    <div className="card" id="people">
      <h2>People</h2>
      <div className="muted" style={{ marginBottom: 8 }}>
        Everyone signs in with their own username and password and sets up their own authenticator app and security keys. An engineer works on leads,
        projects and the outputs; only an owner changes the company profile, pricing and the materials list, and manages people.
      </div>
      {people === null ? (
        <div className="muted">Loading…</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Username</th>
              <th>Role</th>
              <th>Sign-in</th>
              <th>Last sign-in</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {people.map((p) => {
              const self = p.username === me.username
              return (
                <tr key={p.id} className={p.active ? '' : 'muted'} data-testid={`person-${p.username}`}>
                  <td data-label="Name">
                    {p.display_name}
                    {self && <span className="muted"> (you)</span>}
                    {!p.active && <span className="badge neutral" style={{ marginLeft: 6 }}>deactivated</span>}
                  </td>
                  <td data-label="Username">{p.username}</td>
                  <td data-label="Role">
                    {self ? (
                      p.role
                    ) : (
                      <select value={p.role} disabled={busy} onChange={(e) => setRoleOf(p, e.target.value as Person['role'])} style={{ width: 'auto' }}>
                        <option value="engineer">engineer</option>
                        <option value="owner">owner</option>
                      </select>
                    )}
                  </td>
                  <td data-label="Sign-in">
                    {p.must_change_password ? (
                      <span className="badge bad">temporary password</span>
                    ) : (
                      <>
                        {p.two_factor ? <span className="badge good">authenticator on</span> : <span className="badge neutral">password only</span>}
                        {p.passkeys > 0 && <span className="muted"> + {p.passkeys} key{p.passkeys === 1 ? '' : 's'}</span>}
                      </>
                    )}
                  </td>
                  <td data-label="Last sign-in">{p.last_login_at ? fmtDateTime(p.last_login_at) : 'never'}</td>
                  <td className="cell-actions" style={{ whiteSpace: 'nowrap' }}>
                    <button type="button" className="toggle link" disabled={busy} onClick={() => rename(p)}>
                      Rename
                    </button>
                    {!self && (
                      <>
                        <button type="button" className="toggle link" disabled={busy} onClick={() => resetPassword(p)}>
                          Reset password
                        </button>
                        {(p.two_factor || p.passkeys > 0) && (
                          <button type="button" className="toggle link" disabled={busy} onClick={() => resetAuthenticator(p)}>
                            Reset authenticator
                          </button>
                        )}
                        <button type="button" className="toggle link" disabled={busy} onClick={() => setActive(p, !p.active)}>
                          {p.active ? 'Deactivate' : 'Reactivate'}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
      {secret && (
        <div className="banner info" style={{ marginTop: 10 }} data-testid="temporary-password">
          <strong>Temporary password for {secret.who}, shown once:</strong> <code style={{ fontSize: 16, userSelect: 'all' }}>{secret.password}</code>
          <div style={{ marginTop: 4 }}>
            Give it to them in person or by a call, not in the same message as the address. They change it at their first sign-in; it opens nothing else.
          </div>
          <button type="button" className="small" style={{ marginTop: 6 }} onClick={() => setSecret(null)}>
            I have passed it on
          </button>
        </div>
      )}
      {msg && <div className="banner info" style={{ marginTop: 10 }}>{msg}</div>}
      {error && <div className="banner bad" style={{ marginTop: 10 }}>{error}</div>}
      <h3>Add a person</h3>
      <form className="row" onSubmit={add} data-testid="add-person">
        <div className="field">
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. juan.delacruz" autoComplete="off" maxLength={40} />
          <div className="hint">Lower-case letters, digits, dots, dashes or underscores. It is what they type to sign in.</div>
        </div>
        <div className="field">
          <label>Name</label>
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="As shown in the app" maxLength={80} />
        </div>
        <div className="narrow" style={{ width: 140 }}>
          <label>Role</label>
          <select value={role} onChange={(e) => setRole(e.target.value as Person['role'])}>
            <option value="engineer">engineer</option>
            <option value="owner">owner</option>
          </select>
        </div>
        <div className="narrow inline" style={{ paddingBottom: 4 }}>
          <button className="primary" type="submit" disabled={busy || username.trim().length < 2}>
            Add
          </button>
        </div>
      </form>
    </div>
  )
}
