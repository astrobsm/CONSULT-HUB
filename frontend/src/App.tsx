import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import RequireAuth from './auth/RequireAuth'
import RequireAdmin from './auth/RequireAdmin'
import { isAdminRole } from './api/client'
import NotificationBell from './components/NotificationBell'
import RealtimeBridge from './realtime/RealtimeBridge'
import AdminUsersPage from './pages/AdminUsersPage'
import AdminDepartmentsPage from './pages/AdminDepartmentsPage'
import AccountPage from './pages/AccountPage'
import DashboardPage from './pages/DashboardPage'
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
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/consultations">Consultations</Link>
        <Link to="/patients">Patients</Link>
        {isAdminRole(user?.role) && <Link to="/admin/users">Admin</Link>}
        <Link to="/consultations/new" className="btn btn--primary">
          + New consult
        </Link>
        {user && (
          <div className="user-menu">
            <NotificationBell />
            <Link to="/account" className="user-menu__name">
              {user.full_name}
              <span className="user-menu__role">{user.role}</span>
            </Link>
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
      <RealtimeBridge />
      <Header />
      <main className="app__main">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <DashboardPage />
              </RequireAuth>
            }
          />
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
          <Route
            path="/admin"
            element={<Navigate to="/admin/users" replace />}
          />
          <Route
            path="/admin/users"
            element={
              <RequireAdmin>
                <AdminUsersPage />
              </RequireAdmin>
            }
          />
          <Route
            path="/admin/departments"
            element={
              <RequireAdmin>
                <AdminDepartmentsPage />
              </RequireAdmin>
            }
          />
          <Route
            path="/account"
            element={
              <RequireAuth>
                <AccountPage />
              </RequireAuth>
            }
          />
        </Routes>
      </main>
    </div>
  )
}
