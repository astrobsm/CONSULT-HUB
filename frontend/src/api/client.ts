import type {
  Appointment,
  AppointmentStatus,
  AppointmentType,
  AppNotification,
  Attachment,
  Availability,
  Clinic,
  Consultation,
  ConsultationCreate,
  ConsultationMessage,
  ConsultationStatus,
  DashboardSummary,
  Patient,
  PatientCreate,
  Station,
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

export function listConsultations(opts?: {
  status?: ConsultationStatus
  patientId?: number
}): Promise<Consultation[]> {
  const params = new URLSearchParams()
  if (opts?.status) params.set('status', opts.status)
  if (opts?.patientId != null) params.set('patient_id', String(opts.patientId))
  const qs = params.toString()
  return request<Consultation[]>(`/consultations${qs ? `?${qs}` : ''}`)
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

// ---- Patients ----

export function listPatients(search?: string): Promise<Patient[]> {
  const qs = search ? `?search=${encodeURIComponent(search)}` : ''
  return request<Patient[]>(`/patients${qs}`)
}

export function getPatient(id: number): Promise<Patient> {
  return request<Patient>(`/patients/${id}`)
}

export function createPatient(payload: PatientCreate): Promise<Patient> {
  return request<Patient>('/patients', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

// ---- Dashboard ----

export function getDashboardSummary(): Promise<DashboardSummary> {
  return request<DashboardSummary>('/dashboard/summary')
}

// ---- Notifications ----

export function listNotifications(
  unreadOnly = false,
): Promise<AppNotification[]> {
  const qs = unreadOnly ? '?unread_only=true' : ''
  return request<AppNotification[]>(`/notifications${qs}`)
}

export function getUnreadCount(): Promise<{ unread: number }> {
  return request<{ unread: number }>('/notifications/unread-count')
}

export function markNotificationRead(id: number): Promise<AppNotification> {
  return request<AppNotification>(`/notifications/${id}/read`, {
    method: 'POST',
  })
}

export function markAllNotificationsRead(): Promise<{ unread: number }> {
  return request<{ unread: number }>('/notifications/read-all', {
    method: 'POST',
  })
}

// ---- Admin: users ----

export interface CreateUserInput {
  full_name: string
  email: string
  password: string
  role: string
  designation?: string | null
  department_id?: number | null
  institution_id?: number | null
}

export interface UpdateUserInput {
  role?: string
  designation?: string | null
  department_id?: number | null
  is_active?: boolean
}

export function listRoles(): Promise<string[]> {
  return request<string[]>('/users/roles')
}

export function listUsers(): Promise<AuthUser[]> {
  return request<AuthUser[]>('/users')
}

export function createUser(payload: CreateUserInput): Promise<AuthUser> {
  return request<AuthUser>('/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateUser(
  id: number,
  payload: UpdateUserInput,
): Promise<AuthUser> {
  return request<AuthUser>(`/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

// ---- Admin: org ----

export interface Department {
  id: number
  institution_id: number
  name: string
  specialty: string | null
}

export function listDepartments(): Promise<Department[]> {
  return request<Department[]>('/departments')
}

export function createDepartment(payload: {
  name: string
  specialty?: string | null
}): Promise<Department> {
  return request<Department>('/departments', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateDepartment(
  id: number,
  payload: { name?: string; specialty?: string | null },
): Promise<Department> {
  return request<Department>(`/departments/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

// ---- Attachments ----

export function listAttachments(
  consultationId: number,
): Promise<Attachment[]> {
  return request<Attachment[]>(`/consultations/${consultationId}/attachments`)
}

export async function uploadAttachment(
  consultationId: number,
  file: File,
): Promise<Attachment> {
  const form = new FormData()
  form.append('file', file)
  const token = getToken()
  // Note: don't set Content-Type — the browser adds the multipart boundary.
  const res = await fetch(
    `${BASE}/consultations/${consultationId}/attachments`,
    {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    },
  )
  if (!res.ok) {
    const detail = await res
      .json()
      .then((b) => b.detail)
      .catch(() => 'Upload failed')
    throw new Error(detail ?? 'Upload failed')
  }
  return res.json() as Promise<Attachment>
}

export function deleteAttachment(id: number): Promise<void> {
  return request<void>(`/attachments/${id}`, { method: 'DELETE' })
}

/** Fetch the file (with auth) and trigger a browser download. */
export async function downloadAttachment(
  attachment: Attachment,
): Promise<void> {
  const token = getToken()
  const res = await fetch(`${BASE}/attachments/${attachment.id}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error('Download failed')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = attachment.filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// ---- Consultation messages (secure chat) ----

export function listMessages(
  consultationId: number,
): Promise<ConsultationMessage[]> {
  return request<ConsultationMessage[]>(
    `/consultations/${consultationId}/messages`,
  )
}

export function postMessage(
  consultationId: number,
  body: string,
): Promise<ConsultationMessage> {
  return request<ConsultationMessage>(
    `/consultations/${consultationId}/messages`,
    { method: 'POST', body: JSON.stringify({ body }) },
  )
}

// ---- FHIR export ----

export function getFhirEverything(patientId: number): Promise<unknown> {
  return request<unknown>(`/fhir/Patient/${patientId}/$everything`)
}

// ---- Clinics & stations ----

export function listClinics(): Promise<Clinic[]> {
  return request<Clinic[]>('/clinics')
}
export function createClinic(payload: Partial<Clinic>): Promise<Clinic> {
  return request<Clinic>('/clinics', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
export function updateClinic(
  id: number,
  payload: Partial<Clinic>,
): Promise<Clinic> {
  return request<Clinic>(`/clinics/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
export function listStations(clinicId: number): Promise<Station[]> {
  return request<Station[]>(`/clinics/${clinicId}/stations`)
}
export function createStation(
  clinicId: number,
  payload: Partial<Station>,
): Promise<Station> {
  return request<Station>(`/clinics/${clinicId}/stations`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
export function updateStation(
  stationId: number,
  payload: Partial<Station>,
): Promise<Station> {
  return request<Station>(`/stations/${stationId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
export function getAvailability(
  clinicId: number,
  date: string,
): Promise<Availability> {
  return request<Availability>(`/clinics/${clinicId}/availability?date=${date}`)
}

// ---- Appointments ----

export interface BookInput {
  clinic_id: number
  patient_id: number
  slot_start: string
  appointment_type: AppointmentType
  station_id?: number | null
  reason?: string | null
  consultation_id?: number | null
}

export function bookAppointment(payload: BookInput): Promise<Appointment> {
  return request<Appointment>('/appointments', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
export function listAppointments(params?: {
  clinicId?: number
  date?: string
  status?: AppointmentStatus
  patientId?: number
}): Promise<Appointment[]> {
  const q = new URLSearchParams()
  if (params?.clinicId != null) q.set('clinic_id', String(params.clinicId))
  if (params?.date) q.set('date', params.date)
  if (params?.status) q.set('status', params.status)
  if (params?.patientId != null) q.set('patient_id', String(params.patientId))
  const qs = q.toString()
  return request<Appointment[]>(`/appointments${qs ? `?${qs}` : ''}`)
}
export function transitionAppointment(
  id: number,
  toStatus: AppointmentStatus,
  cancellationReason?: string,
): Promise<Appointment> {
  return request<Appointment>(`/appointments/${id}/transition`, {
    method: 'POST',
    body: JSON.stringify({
      to_status: toStatus,
      cancellation_reason: cancellationReason ?? null,
    }),
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
  department_id: number | null
  is_active: boolean
  created_at: string
}

export const ADMIN_ROLES = ['super_admin', 'institution_admin']
export function isAdminRole(role: string | undefined): boolean {
  return role != null && ADMIN_ROLES.includes(role)
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

export function updateProfile(payload: {
  full_name?: string
  designation?: string | null
}): Promise<AuthUser> {
  return request<AuthUser>('/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function changePassword(payload: {
  current_password: string
  new_password: string
}): Promise<void> {
  return request<void>('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function logout() {
  setToken(null)
}
