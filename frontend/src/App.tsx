import { lazy, Suspense, useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import RequireAuth from './auth/RequireAuth'
import RequireAdmin from './auth/RequireAdmin'
import { isAdminRole } from './api/client'
import NotificationBell from './components/NotificationBell'
import RealtimeBridge from './realtime/RealtimeBridge'
import Branding, { BrandHeader } from './components/Branding'

// Route pages are code-split so the initial download is small — important on
// slow connections. Each page loads on demand behind a Suspense fallback.
const AdminUsersPage = lazy(() => import('./pages/AdminUsersPage'))
const AdminDepartmentsPage = lazy(() => import('./pages/AdminDepartmentsPage'))
const AdminClinicsPage = lazy(() => import('./pages/AdminClinicsPage'))
const AdminInstitutionPage = lazy(() => import('./pages/AdminInstitutionPage'))
const AppointmentsPage = lazy(() => import('./pages/AppointmentsPage'))
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'))
const AccountPage = lazy(() => import('./pages/AccountPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const ConsultationsListPage = lazy(
  () => import('./pages/ConsultationsListPage'),
)
const ConsultationCreatePage = lazy(
  () => import('./pages/ConsultationCreatePage'),
)
const ConsultationDetailPage = lazy(
  () => import('./pages/ConsultationDetailPage'),
)
const PatientsListPage = lazy(() => import('./pages/PatientsListPage'))
const PatientCreatePage = lazy(() => import('./pages/PatientCreatePage'))
const PatientDetailPage = lazy(() => import('./pages/PatientDetailPage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'))
const SetPasswordPage = lazy(() => import('./pages/SetPasswordPage'))
const PortalLoginPage = lazy(() => import('./portal/PortalLoginPage'))
const PortalActivatePage = lazy(() => import('./portal/PortalActivatePage'))
const PortalSetPasswordPage = lazy(
  () => import('./portal/PortalSetPasswordPage'),
)
const PortalHomePage = lazy(() => import('./portal/PortalHomePage'))

function Header() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  // Close the mobile menu whenever the route changes.
  useEffect(() => setOpen(false), [location.pathname])

  // Pre-auth screens + the whole patient portal have their own layouts.
  const bare = ['/login', '/forgot-password', '/set-password']
  if (bare.includes(location.pathname)) return null
  if (location.pathname.startsWith('/portal')) return null

  const close = () => setOpen(false)

  return (
    <header className="app__header">
      <Link to="/dashboard" className="app__brand">
        <BrandHeader />
      </Link>

      <div className="app__header-actions">
        {user && <NotificationBell />}
        <button
          className="nav-toggle"
          aria-label="Menu"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? '✕' : '☰'}
        </button>
      </div>

      <nav className={`app__nav ${open ? 'app__nav--open' : ''}`}>
        <Link to="/dashboard" onClick={close}>
          Dashboard
        </Link>
        <Link to="/consultations" onClick={close}>
          Consultations
        </Link>
        <Link to="/appointments" onClick={close}>
          Appointments
        </Link>
        <Link to="/analytics" onClick={close}>
          Analytics
        </Link>
        <Link to="/patients" onClick={close}>
          Patients
        </Link>
        {isAdminRole(user?.role) && (
          <Link to="/admin/users" onClick={close}>
            Admin
          </Link>
        )}
        <Link
          to="/consultations/new"
          className="btn btn--primary"
          onClick={close}
        >
          + New consult
        </Link>
        {user && (
          <div className="user-menu">
            <Link to="/account" className="user-menu__name" onClick={close}>
              {user.full_name}
              <span className="user-menu__role">{user.role}</span>
            </Link>
            <button
              className="btn"
              onClick={() => {
                close()
                logout()
              }}
            >
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
      <Branding />
      <Header />
      <main className="app__main">
        <Suspense fallback={<p className="muted center">Loading…</p>}>
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
            path="/admin/institution"
            element={
              <RequireAdmin>
                <AdminInstitutionPage />
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
        </Suspense>
      </main>
    </div>
  )
}
