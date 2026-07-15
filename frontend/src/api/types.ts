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
