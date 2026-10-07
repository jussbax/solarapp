import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api, setUnauthorizedHandler } from './api'
import type { DataStatus } from './types'
import LoginPage from './pages/LoginPage'
import AssessmentListPage from './pages/AssessmentListPage'
import AssessmentPage from './pages/AssessmentPage'
import SettingsPage from './pages/SettingsPage'
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
        <Link to="/">Solar Roof Simulator</Link>
        {user && (
          <div className="right">
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
          <Route path="/settings" element={user ? <SettingsPage status={status} onRefresh={refreshStatus} /> : <Navigate to="/login" />} />
        </Routes>
      </div>
    </>
  )
}
