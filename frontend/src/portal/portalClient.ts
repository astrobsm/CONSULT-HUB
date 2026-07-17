import type { Appointment, Availability, Clinic } from '../api/types'

const BASE = '/api'
const PKEY = 'consulthub_patient_token'

export interface PortalPatient {
  id: number
  full_name: string
  hospital_number: string
  email: string | null
  phone: string | null
  institution_id: number | null
}

export function getPatientToken(): string | null {
  return localStorage.getItem(PKEY)
}
export function setPatientToken(token: string | null) {
  if (token) localStorage.setItem(PKEY, token)
  else localStorage.removeItem(PKEY)
}

export class PortalUnauthorized extends Error {}

async function preq<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getPatientToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string>),
  }
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${BASE}${path}`, { ...init, headers })
  if (res.status === 401) {
    setPatientToken(null)
    throw new PortalUnauthorized('Please sign in again.')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* non-JSON */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export async function portalLogin(
  email: string,
  password: string,
): Promise<PortalPatient> {
  const body = new URLSearchParams({ username: email, password })
  const res = await fetch(`${BASE}/portal/login`, {
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
  const data = await res.json()
  setPatientToken(data.access_token)
  return data.patient as PortalPatient
}

export function portalActivate(
  hospitalNumber: string,
  email: string,
): Promise<{ status: string }> {
  return preq('/portal/activate', {
    method: 'POST',
    body: JSON.stringify({ hospital_number: hospitalNumber, email }),
  })
}

export function portalSetPassword(
  token: string,
  password: string,
): Promise<void> {
  return preq<void>('/portal/set-password', {
    method: 'POST',
    body: JSON.stringify({ token, password }),
  })
}

export function portalMe(): Promise<PortalPatient> {
  return preq<PortalPatient>('/portal/me')
}
export function portalClinics(): Promise<Clinic[]> {
  return preq<Clinic[]>('/portal/clinics')
}
export function portalAvailability(
  clinicId: number,
  date: string,
): Promise<Availability> {
  return preq<Availability>(`/portal/clinics/${clinicId}/availability?date=${date}`)
}
export function portalMyAppointments(): Promise<Appointment[]> {
  return preq<Appointment[]>('/portal/appointments')
}
export function portalBook(payload: {
  clinic_id: number
  slot_start: string
  appointment_type: string
}): Promise<Appointment> {
  return preq<Appointment>('/portal/appointments', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
export function portalCancel(id: number): Promise<Appointment> {
  return preq<Appointment>(`/portal/appointments/${id}/cancel`, {
    method: 'POST',
  })
}
export function portalLogout() {
  setPatientToken(null)
}
