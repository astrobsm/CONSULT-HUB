import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import RequireAuth from './auth/RequireAuth'
import RequireAdmin from './auth/RequireAdmin'
import { isAdminRole } from './api/client'
import NotificationBell from './components/NotificationBell'
import RealtimeBridge from './realtime/RealtimeBridge'
import AdminUsersPage from './pages/AdminUsersPage'
import AdminDepartmentsPage from './pages/AdminDepartmentsPage'
import AdminClinicsPage from './pages/AdminClinicsPage'
import AppointmentsPage from './pages/AppointmentsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import AccountPage from './pages/AccountPage'
import DashboardPage from './pages/DashboardPage'
import ConsultationsListPage from './pages/ConsultationsListPage'
import ConsultationCreatePage from './pages/ConsultationCreatePage'
import ConsultationDetailPage from './pages/ConsultationDetailPage'
import PatientsListPage from './pages/PatientsListPage'
import PatientCreatePage from './pages/PatientCreatePage'
import PatientDetailPage from './pages/PatientDetailPage'
import LoginPage from './pages/LoginPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import SetPasswordPage from './pages/SetPasswordPage'
import PortalLoginPage from './portal/PortalLoginPage'
import PortalActivatePage from './portal/PortalActivatePage'
import PortalSetPasswordPage from './portal/PortalSetPasswordPage'
import PortalHomePage from './portal/PortalHomePage'

function Header() {
  const { user, logout } = useAuth()
  const location = useLocation()

  // Pre-auth screens + the whole patient portal have their own layouts.
  const bare = ['/login', '/forgot-password', '/set-password']
  if (bare.includes(location.pathname)) return null
  if (location.pathname.startsWith('/portal')) return null

  return (
    <header className="app__header">
      <Link to="/consultations" className="app__brand">
        Consult<span>HUB</span>
      </Link>
      <nav className="app__nav">
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/consultations">Consultations</Link>
        <Link to="/appointments">Appointments</Link>
        <Link to="/analytics">Analytics</Link>
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
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/set-password" element={<SetPasswordPage />} />
          <Route path="/portal/login" element={<PortalLoginPage />} />
          <Route path="/portal/activate" element={<PortalActivatePage />} />
          <Route
            path="/portal/set-password"
            element={<PortalSetPasswordPage />}
          />
          <Route path="/portal" element={<PortalHomePage />} />
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
            path="/admin/clinics"
            element={
              <RequireAdmin>
                <AdminClinicsPage />
              </RequireAdmin>
            }
          />
          <Route
            path="/appointments"
            element={
              <RequireAuth>
                <AppointmentsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/analytics"
            element={
              <RequireAuth>
                <AnalyticsPage />
              </RequireAuth>
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
