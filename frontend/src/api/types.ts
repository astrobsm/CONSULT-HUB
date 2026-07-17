export const PRIORITIES = ['routine', 'urgent', 'emergency'] as const
export type Priority = (typeof PRIORITIES)[number]

export const CONSULTATION_TYPES = [
  'routine', 'urgent', 'emergency', 'icu', 'ward', 'clinic',
  'emergency_department', 'theatre', 'preoperative', 'postoperative',
  'nutrition', 'pain_management', 'rehabilitation', 'psychological',
  'social_welfare', 'teleconsultation', 'second_opinion', 'tumor_board',
  'mdt', 'referral', 'home_care', 'palliative_care', 'discharge_planning',
] as const
export type ConsultationType = (typeof CONSULTATION_TYPES)[number]

export const STATUSES = [
  'draft', 'submitted', 'received', 'viewed', 'acknowledged', 'accepted',
  'seen', 'transferred', 'delegated', 'rejected', 'returned', 'escalated',
  'completed', 'cancelled',
] as const
export type ConsultationStatus = (typeof STATUSES)[number]

export interface ConsultationEvent {
  id: number
  from_status: ConsultationStatus | null
  to_status: ConsultationStatus | null
  actor_user_id: number | null
  note: string | null
  created_at: string
}

export interface EscalationEvent {
  id: number
  level: number
  label: string
  threshold_minutes: number
  notify_role: string
  fired_at: string
}

export interface Consultation {
  id: number
  patient_id: number | null
  requesting_user_id: number | null
  institution_id: number | null
  target_department_id: number | null
  target_specialty: string | null
  target_consultant: string | null
  consultation_type: ConsultationType
  priority: Priority
  status: ConsultationStatus
  reason: string
  clinical_summary: string | null
  specific_questions: string | null
  required_response_minutes: number | null
  escalation_level: number
  created_at: string
  updated_at: string
  acknowledged_at: string | null
  completed_at: string | null
  events: ConsultationEvent[]
  escalation_events: EscalationEvent[]
}

export interface ConsultationCreate {
  patient_id?: number | null
  reason: string
  priority: Priority
  consultation_type: ConsultationType
  target_specialty?: string | null
  target_consultant?: string | null
  clinical_summary?: string | null
  specific_questions?: string | null
  required_response_minutes?: number | null
}

export interface Patient {
  id: number
  institution_id: number | null
  hospital_number: string
  full_name: string
  date_of_birth: string | null
  sex: string | null
  phone: string | null
  blood_group: string | null
  genotype: string | null
  weight_kg: number | null
  height_cm: number | null
  ward: string | null
  bed: string | null
  primary_diagnosis: string | null
  allergies: string | null
  age: number | null
  bmi: number | null
  created_at: string
}

export const APPOINTMENT_TYPES = [
  'new_patient', 'review', 'follow_up', 'postoperative', 'procedure',
  'telemedicine', 'emergency', 'walk_in', 'priority', 'vip', 'staff',
  'insurance', 'private',
] as const
export type AppointmentType = (typeof APPOINTMENT_TYPES)[number]

export type AppointmentStatus =
  | 'booked' | 'confirmed' | 'checked_in' | 'waiting' | 'called'
  | 'in_progress' | 'completed' | 'did_not_attend' | 'cancelled'
  | 'rescheduled' | 'referred' | 'admitted' | 'discharged'

export const STATION_TYPES = [
  'consultant', 'registrar', 'medical_officer', 'resident',
  'nurse_practitioner', 'dietician', 'physiotherapy', 'psychology',
  'occupational_therapy', 'social_welfare', 'telemedicine', 'procedure',
  'review', 'emergency_walk_in',
] as const
export type StationType = (typeof STATION_TYPES)[number]

export interface Clinic {
  id: number
  institution_id: number | null
  department_id: number | null
  name: string
  subspecialty: string | null
  location: string | null
  operating_days: string
  open_time: string
  close_time: string
  break_start: string | null
  break_end: string | null
  slot_duration_minutes: number
  load_balancing: 'least_busy' | 'round_robin'
  is_active: boolean
  created_at: string
}

export interface Station {
  id: number
  clinic_id: number
  station_number: number
  name: string
  station_type: StationType
  room_number: string | null
  assigned_user_id: number | null
  max_patients: number | null
  status: 'active' | 'inactive' | 'maintenance'
}

export interface StationAvailability {
  station_id: number
  station_name: string
  booked_count: number
  free_slots: string[]
}

export interface Availability {
  clinic_id: number
  date: string
  slot_duration_minutes: number
  stations: StationAvailability[]
}

export interface WaitingEntry {
  id: number
  clinic_id: number
  patient_id: number
  patient_name: string | null
  target_date: string
  appointment_type: AppointmentType
  status: 'waiting' | 'promoted' | 'cancelled'
  promoted_appointment_id: number | null
  created_at: string
}

export interface Appointment {
  id: number
  appointment_number: string | null
  check_in_code: string | null
  clinic_id: number
  clinic_name: string | null
  station_id: number
  station_name: string | null
  patient_id: number
  patient_name: string | null
  consultation_id: number | null
  appointment_type: AppointmentType
  slot_start: string
  duration_minutes: number
  status: AppointmentStatus
  queue_position: number | null
  reason: string | null
  rescheduled_to_id: number | null
  checked_in_at: string | null
  created_at: string
}

/** Forward transitions allowed per appointment status (mirrors backend). */
export const APPOINTMENT_TRANSITIONS: Record<AppointmentStatus, AppointmentStatus[]> = {
  booked: ['confirmed', 'checked_in', 'cancelled', 'rescheduled', 'did_not_attend'],
  confirmed: ['checked_in', 'cancelled', 'rescheduled', 'did_not_attend'],
  checked_in: ['waiting', 'called', 'cancelled'],
  waiting: ['called', 'cancelled'],
  called: ['in_progress', 'did_not_attend', 'waiting'],
  in_progress: ['completed', 'referred', 'admitted', 'discharged'],
  completed: [],
  did_not_attend: ['rescheduled'],
  cancelled: [],
  rescheduled: [],
  referred: [],
  admitted: [],
  discharged: [],
}

export interface ConsultationMessage {
  id: number
  consultation_id: number
  sender_user_id: number
  sender_name: string
  body: string
  created_at: string
}

export interface Attachment {
  id: number
  consultation_id: number
  uploaded_by_user_id: number | null
  filename: string
  content_type: string
  size_bytes: number
  created_at: string
}

export interface AppNotification {
  id: number
  consultation_id: number | null
  kind: string
  title: string
  body: string
  is_read: boolean
  created_at: string
}

export interface DashboardSummary {
  total: number
  pending: number
  today: number
  completed: number
  overdue: number
  escalated: number
  completion_rate: number
  avg_ack_minutes: number | null
  avg_completion_minutes: number | null
  by_priority_pending: Record<Priority, number>
  by_status: Record<string, number>
  top_specialties: { specialty: string; count: number }[]
}

export interface PatientCreate {
  hospital_number: string
  full_name: string
  date_of_birth?: string | null
  sex?: string | null
  phone?: string | null
  blood_group?: string | null
  genotype?: string | null
  weight_kg?: number | null
  height_cm?: number | null
  ward?: string | null
  bed?: string | null
  primary_diagnosis?: string | null
  allergies?: string | null
}

/** Forward transitions allowed from each status — mirrors the backend engine. */
export const ALLOWED_TRANSITIONS: Record<ConsultationStatus, ConsultationStatus[]> = {
  draft: ['submitted', 'cancelled'],
  submitted: ['received', 'acknowledged', 'escalated', 'cancelled'],
  received: ['viewed', 'acknowledged', 'escalated', 'cancelled'],
  viewed: ['acknowledged', 'escalated', 'cancelled'],
  acknowledged: ['accepted', 'transferred', 'delegated', 'rejected', 'returned', 'escalated', 'cancelled'],
  accepted: ['seen', 'transferred', 'delegated', 'escalated', 'cancelled'],
  seen: ['completed', 'returned', 'escalated'],
  transferred: ['acknowledged', 'cancelled'],
  delegated: ['acknowledged', 'cancelled'],
  returned: ['submitted', 'cancelled'],
  rejected: [],
  escalated: ['acknowledged', 'accepted', 'cancelled'],
  completed: [],
  cancelled: [],
}
