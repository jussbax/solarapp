import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { api, setUnauthorizedHandler, type Me } from './api'
import type { DataStatus } from './types'
import LoginPage from './pages/LoginPage'
import AssessmentListPage from './pages/AssessmentListPage'
import AssessmentPage from './pages/AssessmentPage'
import LeadsPage from './pages/LeadsPage'
import SettingsPage from './pages/SettingsPage'
import MaterialsPage from './pages/MaterialsPage'
import DataBanner from './components/DataBanner'
import ChangePassword from './components/ChangePassword'

/** The four places in the back office. The estimate page is a website preview and lives under Settings › Website. */
const NAV: { to: string; label: string; match: (path: string) => boolean }[] = [
  { to: '/', label: 'Projects', match: (p) => p === '/' || p.startsWith('/assessments') },
  { to: '/leads', label: 'Leads', match: (p) => p.startsWith('/leads') },
  { to: '/materials', label: 'Materials', match: (p) => p.startsWith('/materials') },
  { to: '/settings', label: 'Settings', match: (p) => p.startsWith('/settings') },
]

export default function App() {
  const [user, setUser] = useState<Me | null | undefined>(undefined)
  const [status, setStatus] = useState<DataStatus | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const refreshStatus = useCallback(() => {
    api.dataStatus().then(setStatus).catch(() => setStatus(null))
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null)
      navigate('/login')
    })
    api.me().then((m) => setUser(m.signed_in ? m : null)).catch(() => setUser(null))
  }, [navigate])

  useEffect(() => {
    if (user) refreshStatus()
  }, [user, refreshStatus])

  if (user === undefined) return <div className="page">Loading...</div>

  const logout = async () => {
    await api.logout()
    setUser(null)
    navigate('/login')
  }

  const current = NAV.find((n) => n.match(location.pathname))
  const pageName = location.pathname.startsWith('/assessments/') ? 'Project' : (current?.label ?? '')

  // a temporary password (first sign-in, or after the owner reset it) opens nothing until the person chooses their own
  if (user?.must_change_password) {
    return (
      <div className="page">
        <div className="card login" style={{ maxWidth: 440 }}>
          <h2>Welcome, {user.display_name || user.username}</h2>
          <div className="muted" style={{ marginBottom: 10 }}>
            The password you signed in with is temporary and opens nothing else. Choose your own to continue.
          </div>
          <ChangePassword user={user} onDone={setUser} temporary />
          <button type="button" className="alt" onClick={logout} style={{ marginTop: 8 }}>
            Sign out
          </button>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className={`topbar ${menuOpen ? 'open' : ''}`}>
        <Link to="/" className="brand" onClick={() => setMenuOpen(false)}>
          <img src="/brand/logo-mark-white.png" alt="" />
          <span>
            <span className="name">PL Development</span>
            <span className="tag">Solar engineering</span>
          </span>
        </Link>
        {user && <span className="page-name">{pageName}</span>}
        {user && (
          <button type="button" className="nav-toggle" aria-expanded={menuOpen} aria-controls="topnav" onClick={() => setMenuOpen((o) => !o)}>
            {menuOpen ? 'Close' : 'Menu'}
          </button>
        )}
        {/* the phone menu closes when a link in it is followed */}
        {user && (
          <nav className="right" id="topnav" aria-label="Main" onClick={() => setMenuOpen(false)}>
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} className={current?.to === n.to ? 'on' : ''} aria-current={current?.to === n.to ? 'page' : undefined}>
                {n.label}
              </Link>
            ))}
            <Link to="/settings#account" className="who" title={`Signed in as ${user.username}${user.role === 'owner' ? ' (owner)' : ''}`}>
              {user.display_name || user.username}
            </Link>
            <button onClick={logout}>Sign out</button>
          </nav>
        )}
      </div>
      <div className="page">
        {user && <DataBanner status={status} />}
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" /> : <LoginPage onLogin={setUser} />} />
          <Route path="/" element={user ? <AssessmentListPage /> : <Navigate to="/login" />} />
          <Route path="/assessments/:id" element={user ? <AssessmentPage status={status} /> : <Navigate to="/login" />} />
          <Route path="/leads" element={user ? <LeadsPage /> : <Navigate to="/login" />} />
          <Route path="/leads/:id" element={user ? <LeadsPage /> : <Navigate to="/login" />} />
          <Route path="/materials" element={user ? <MaterialsPage user={user} /> : <Navigate to="/login" />} />
          <Route path="/settings" element={user ? <SettingsPage user={user} onUser={setUser} status={status} onRefresh={refreshStatus} /> : <Navigate to="/login" />} />
          <Route
            path="*"
            element={
              user ? (
                <div className="card">
                  <div className="banner bad">There is no page at this address.</div>
                  <Link to="/">Back to the projects</Link>
                </div>
              ) : (
                <Navigate to="/login" />
              )
            }
          />
        </Routes>
      </div>
    </>
  )
}
