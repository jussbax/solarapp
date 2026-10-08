import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api, setUnauthorizedHandler } from './api'
import type { DataStatus } from './types'
import LoginPage from './pages/LoginPage'
import AssessmentListPage from './pages/AssessmentListPage'
import AssessmentPage from './pages/AssessmentPage'
import SettingsPage from './pages/SettingsPage'
import MaterialsPage from './pages/MaterialsPage'
import DataBanner from './components/DataBanner'

export default function App() {
  const [user, setUser] = useState<string | null | undefined>(undefined)
  const [status, setStatus] = useState<DataStatus | null>(null)
  const navigate = useNavigate()

  const refreshStatus = useCallback(() => {
    api.dataStatus().then(setStatus).catch(() => setStatus(null))
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null)
      navigate('/login')
    })
    api.me().then((m) => setUser(m.username)).catch(() => setUser(null))
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

  return (
    <>
      <div className="topbar">
        <Link to="/" className="brand">
          <img src="/brand/logo-mark-white.png" alt="" />
          <span>
            <span className="name">PL Development</span>
            <span className="tag">Solar assessment</span>
          </span>
        </Link>
        {user && (
          <div className="right">
            <a href="/estimate" target="_blank" rel="noreferrer">Estimate page</a>
            <Link to="/materials">Materials</Link>
            <Link to="/settings">Settings</Link>
            <span>{user}</span>
            <button onClick={logout}>Sign out</button>
          </div>
        )}
      </div>
      <div className="page">
        {user && <DataBanner status={status} />}
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" /> : <LoginPage onLogin={(u) => setUser(u)} />} />
          <Route path="/" element={user ? <AssessmentListPage /> : <Navigate to="/login" />} />
          <Route path="/assessments/:id" element={user ? <AssessmentPage status={status} /> : <Navigate to="/login" />} />
          <Route path="/materials" element={user ? <MaterialsPage /> : <Navigate to="/login" />} />
          <Route path="/settings" element={user ? <SettingsPage status={status} onRefresh={refreshStatus} /> : <Navigate to="/login" />} />
        </Routes>
      </div>
    </>
  )
}
