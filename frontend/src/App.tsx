import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import RequireAuth from './auth/RequireAuth'
import ConsultationsListPage from './pages/ConsultationsListPage'
import ConsultationCreatePage from './pages/ConsultationCreatePage'
import ConsultationDetailPage from './pages/ConsultationDetailPage'
import PatientsListPage from './pages/PatientsListPage'
import PatientCreatePage from './pages/PatientCreatePage'
import PatientDetailPage from './pages/PatientDetailPage'
import LoginPage from './pages/LoginPage'

function Header() {
  const { user, logout } = useAuth()
  const location = useLocation()

  // The login screen has its own full-page layout.
  if (location.pathname === '/login') return null

  return (
    <header className="app__header">
      <Link to="/consultations" className="app__brand">
        Consult<span>HUB</span>
      </Link>
      <nav className="app__nav">
        <Link to="/consultations">Consultations</Link>
        <Link to="/patients">Patients</Link>
        <Link to="/consultations/new" className="btn btn--primary">
          + New consult
        </Link>
        {user && (
          <div className="user-menu">
            <span className="user-menu__name">
              {user.full_name}
              <span className="user-menu__role">{user.role}</span>
            </span>
            <button className="btn" onClick={logout}>
              Sign out
            </button>
          </div>
        )}
      </nav>
    </header>
  )
}

export default function App() {
  return (
    <div className="app">
      <Header />
      <main className="app__main">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Navigate to="/consultations" replace />} />
          <Route
            path="/consultations"
            element={
              <RequireAuth>
                <ConsultationsListPage />
              </RequireAuth>
            }
          />
          <Route
            path="/consultations/new"
            element={
              <RequireAuth>
                <ConsultationCreatePage />
              </RequireAuth>
            }
          />
          <Route
            path="/consultations/:id"
            element={
              <RequireAuth>
                <ConsultationDetailPage />
              </RequireAuth>
            }
          />
          <Route
            path="/patients"
            element={
              <RequireAuth>
                <PatientsListPage />
              </RequireAuth>
            }
          />
          <Route
            path="/patients/new"
            element={
              <RequireAuth>
                <PatientCreatePage />
              </RequireAuth>
            }
          />
          <Route
            path="/patients/:id"
            element={
              <RequireAuth>
                <PatientDetailPage />
              </RequireAuth>
            }
          />
        </Routes>
      </main>
    </div>
  )
}
