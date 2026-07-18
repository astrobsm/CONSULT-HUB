import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  fetchMe,
  getToken,
  login as apiLogin,
  logout as apiLogout,
  type AuthUser,
} from '../api/client'
import { applyAppearance } from '../theme'
import { clearApiCache } from '../registerSW'

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  // On mount, restore the session from a stored token (if any).
  useEffect(() => {
    let cancelled = false
    if (!getToken()) {
      setLoading(false)
      return
    }
    fetchMe()
      .then((u) => !cancelled && setUser(u))
      .catch(() => !cancelled && setUser(null))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  // Reset auth state if any request reports the session is no longer valid.
  useEffect(() => {
    const onUnauthorized = () => setUser(null)
    window.addEventListener('consulthub:unauthorized', onUnauthorized)
    return () =>
      window.removeEventListener('consulthub:unauthorized', onUnauthorized)
  }, [])

  // Apply the signed-in user's appearance preferences.
  useEffect(() => {
    if (user) {
      applyAppearance({
        theme: user.theme,
        accent: user.accent,
        font_family: user.font_family,
      })
    }
  }, [user])

  const login = useCallback(async (email: string, password: string) => {
    const u = await apiLogin(email, password)
    setUser(u)
  }, [])

  const logout = useCallback(() => {
    apiLogout()
    clearApiCache()
    setUser(null)
  }, [])

  const refresh = useCallback(async () => {
    const u = await fetchMe()
    setUser(u)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, logout, refresh }),
    [user, loading, login, logout, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
