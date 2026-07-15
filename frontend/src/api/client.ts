import type {
  Consultation,
  ConsultationCreate,
  ConsultationStatus,
} from './types'

const BASE = '/api'
const TOKEN_KEY = 'consulthub_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** Raised on 401 so callers can trigger a logout. */
export class UnauthorizedError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string>),
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...init, headers })

  if (res.status === 401) {
    setToken(null)
    // Notify the app so auth state (and the UI) can reset.
    window.dispatchEvent(new Event('consulthub:unauthorized'))
    throw new UnauthorizedError('Session expired. Please sign in again.')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function listConsultations(
  status?: ConsultationStatus,
): Promise<Consultation[]> {
  const qs = status ? `?status=${status}` : ''
  return request<Consultation[]>(`/consultations${qs}`)
}

export function getConsultation(id: number): Promise<Consultation> {
  return request<Consultation>(`/consultations/${id}`)
}

export function createConsultation(
  payload: ConsultationCreate,
): Promise<Consultation> {
  return request<Consultation>('/consultations', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function transitionConsultation(
  id: number,
  toStatus: ConsultationStatus,
  note?: string,
): Promise<Consultation> {
  return request<Consultation>(`/consultations/${id}/transition`, {
    method: 'POST',
    body: JSON.stringify({ to_status: toStatus, note: note || null }),
  })
}

export function health(): Promise<{ status: string; service: string }> {
  return request('/health')
}

// ---- Auth ----

export interface AuthUser {
  id: number
  full_name: string
  email: string
  role: string
  designation: string | null
  institution_id: number | null
  is_active: boolean
  created_at: string
}

interface TokenResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export async function login(
  email: string,
  password: string,
): Promise<AuthUser> {
  // OAuth2 password flow expects form-encoded body with `username`.
  const body = new URLSearchParams({ username: email, password })
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!res.ok) {
    const detail = await res
      .json()
      .then((b) => b.detail)
      .catch(() => 'Login failed')
    throw new Error(detail ?? 'Login failed')
  }
  const data = (await res.json()) as TokenResponse
  setToken(data.access_token)
  return data.user
}

export function fetchMe(): Promise<AuthUser> {
  return request<AuthUser>('/auth/me')
}

export function logout() {
  setToken(null)
}
