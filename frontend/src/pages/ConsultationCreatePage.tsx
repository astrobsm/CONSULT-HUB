import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createConsultation, listPatients } from '../api/client'
import {
  CONSULTATION_TYPES,
  PRIORITIES,
  type ConsultationCreate,
} from '../api/types'

const EMPTY: ConsultationCreate = {
  patient_id: null,
  reason: '',
  priority: 'routine',
  consultation_type: 'ward',
  target_specialty: '',
  target_consultant: '',
  clinical_summary: '',
  specific_questions: '',
  required_response_minutes: null,
}

export default function ConsultationCreatePage() {
  const [searchParams] = useSearchParams()
  const preselectedPatient = searchParams.get('patient')
  const [form, setForm] = useState<ConsultationCreate>({
    ...EMPTY,
    patient_id: preselectedPatient ? Number(preselectedPatient) : null,
  })
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: patients } = useQuery({
    queryKey: ['patients', ''],
    queryFn: () => listPatients(),
  })

  const mutation = useMutation({
    mutationFn: (payload: ConsultationCreate) => createConsultation(payload),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['consultations'] })
      navigate(`/consultations/${created.id}`)
    },
  })

  function update<K extends keyof ConsultationCreate>(
    key: K,
    value: ConsultationCreate[K],
  ) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    mutation.mutate({
      ...form,
      target_specialty: form.target_specialty || null,
      target_consultant: form.target_consultant || null,
      clinical_summary: form.clinical_summary || null,
      specific_questions: form.specific_questions || null,
    })
  }

  return (
    <section className="form-page">
      <h1>New consultation</h1>
      <form onSubmit={onSubmit} className="form">
        <label className="field field--full">
          <span>Patient</span>
          <select
            value={form.patient_id ?? ''}
            onChange={(e) =>
              update('patient_id', e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">— No patient linked —</option>
            {patients?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name} ({p.hospital_number})
                {p.ward ? ` · ${p.ward}` : ''}
              </option>
            ))}
          </select>
        </label>

        <label className="field field--full">
          <span>Reason for consultation *</span>
          <input
            required
            maxLength={500}
            value={form.reason}
            onChange={(e) => update('reason', e.target.value)}
            placeholder="e.g. Diabetic foot ulcer, ? need for debridement"
          />
        </label>

        <div className="grid">
          <label className="field">
            <span>Priority</span>
            <select
              value={form.priority}
              onChange={(e) => update('priority', e.target.value as never)}
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Type</span>
            <select
              value={form.consultation_type}
              onChange={(e) =>
                update('consultation_type', e.target.value as never)
              }
            >
              {CONSULTATION_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Response time (min)</span>
            <input
              type="number"
              min={1}
              value={form.required_response_minutes ?? ''}
              onChange={(e) =>
                update(
                  'required_response_minutes',
                  e.target.value ? Number(e.target.value) : null,
                )
              }
              placeholder="e.g. 60"
            />
          </label>
        </div>

        <div className="grid">
          <label className="field">
            <span>Target specialty</span>
            <input
              value={form.target_specialty ?? ''}
              onChange={(e) => update('target_specialty', e.target.value)}
              placeholder="e.g. Plastic Surgery"
            />
          </label>
          <label className="field">
            <span>Target consultant</span>
            <input
              value={form.target_consultant ?? ''}
              onChange={(e) => update('target_consultant', e.target.value)}
              placeholder="e.g. Dr. Adeyemi"
            />
          </label>
        </div>

        <label className="field field--full">
          <span>Clinical summary</span>
          <textarea
            rows={4}
            value={form.clinical_summary ?? ''}
            onChange={(e) => update('clinical_summary', e.target.value)}
            placeholder="Relevant history, examination, investigations…"
          />
        </label>

        <label className="field field--full">
          <span>Specific questions</span>
          <textarea
            rows={2}
            value={form.specific_questions ?? ''}
            onChange={(e) => update('specific_questions', e.target.value)}
            placeholder="What exactly do you want answered?"
          />
        </label>

        {mutation.isError && (
          <p className="error">{(mutation.error as Error).message}</p>
        )}

        <div className="form-actions">
          <button
            type="button"
            className="btn"
            onClick={() => navigate('/consultations')}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={mutation.isPending || !form.reason.trim()}
          >
            {mutation.isPending ? 'Submitting…' : 'Submit consultation'}
          </button>
        </div>
      </form>
    </section>
  )
}
