import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from './AuthContext'
import { isAdminRole } from '../api/client'

export default function RequireAdmin({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) return <p className="muted center">Loading…</p>
  if (!user) return <Navigate to="/login" replace />
  if (!isAdminRole(user.role)) {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children}</>
}
