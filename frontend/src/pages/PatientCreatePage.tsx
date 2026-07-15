import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createPatient } from '../api/client'
import type { PatientCreate } from '../api/types'

const EMPTY: PatientCreate = {
  hospital_number: '',
  full_name: '',
  date_of_birth: '',
  sex: '',
  phone: '',
  blood_group: '',
  genotype: '',
  weight_kg: null,
  height_cm: null,
  ward: '',
  bed: '',
  primary_diagnosis: '',
  allergies: '',
}

function clean(form: PatientCreate): PatientCreate {
  const out = { ...form }
  for (const k of Object.keys(out) as (keyof PatientCreate)[]) {
    if (out[k] === '') (out[k] as unknown) = null
  }
  return out
}

export default function PatientCreatePage() {
  const [form, setForm] = useState<PatientCreate>(EMPTY)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (payload: PatientCreate) => createPatient(payload),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['patients'] })
      navigate(`/patients/${created.id}`)
    },
  })

  function update<K extends keyof PatientCreate>(
    key: K,
    value: PatientCreate[K],
  ) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  return (
    <section className="form-page">
      <h1>Register patient</h1>
      <form
        className="form"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate(clean(form))
        }}
      >
        <div className="grid">
          <label className="field">
            <span>Hospital number *</span>
            <input
              required
              value={form.hospital_number}
              onChange={(e) => update('hospital_number', e.target.value)}
              placeholder="MRN-000000"
            />
          </label>
          <label className="field">
            <span>Full name *</span>
            <input
              required
              value={form.full_name}
              onChange={(e) => update('full_name', e.target.value)}
            />
          </label>
        </div>

        <div className="grid">
          <label className="field">
            <span>Date of birth</span>
            <input
              type="date"
              value={form.date_of_birth ?? ''}
              onChange={(e) => update('date_of_birth', e.target.value)}
            />
          </label>
          <label className="field">
            <span>Sex</span>
            <select
              value={form.sex ?? ''}
              onChange={(e) => update('sex', e.target.value)}
            >
              <option value="">—</option>
              <option>Female</option>
              <option>Male</option>
              <option>Other</option>
            </select>
          </label>
          <label className="field">
            <span>Phone</span>
            <input
              value={form.phone ?? ''}
              onChange={(e) => update('phone', e.target.value)}
            />
          </label>
        </div>

        <div className="grid">
          <label className="field">
            <span>Blood group</span>
            <input
              value={form.blood_group ?? ''}
              onChange={(e) => update('blood_group', e.target.value)}
              placeholder="O+"
            />
          </label>
          <label className="field">
            <span>Genotype</span>
            <input
              value={form.genotype ?? ''}
              onChange={(e) => update('genotype', e.target.value)}
              placeholder="AA"
            />
          </label>
          <label className="field">
            <span>Weight (kg)</span>
            <input
              type="number"
              step="0.1"
              value={form.weight_kg ?? ''}
              onChange={(e) =>
                update(
                  'weight_kg',
                  e.target.value ? Number(e.target.value) : null,
                )
              }
            />
          </label>
          <label className="field">
            <span>Height (cm)</span>
            <input
              type="number"
              step="0.1"
              value={form.height_cm ?? ''}
              onChange={(e) =>
                update(
                  'height_cm',
                  e.target.value ? Number(e.target.value) : null,
                )
              }
            />
          </label>
        </div>

        <div className="grid">
          <label className="field">
            <span>Ward</span>
            <input
              value={form.ward ?? ''}
              onChange={(e) => update('ward', e.target.value)}
            />
          </label>
          <label className="field">
            <span>Bed</span>
            <input
              value={form.bed ?? ''}
              onChange={(e) => update('bed', e.target.value)}
            />
          </label>
        </div>

        <label className="field field--full">
          <span>Primary diagnosis</span>
          <input
            value={form.primary_diagnosis ?? ''}
            onChange={(e) => update('primary_diagnosis', e.target.value)}
          />
        </label>
        <label className="field field--full">
          <span>Drug allergies</span>
          <input
            value={form.allergies ?? ''}
            onChange={(e) => update('allergies', e.target.value)}
            placeholder="e.g. Penicillin"
          />
        </label>

        {mutation.isError && (
          <p className="error">{(mutation.error as Error).message}</p>
        )}

        <div className="form-actions">
          <button
            type="button"
            className="btn"
            onClick={() => navigate('/patients')}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={
              mutation.isPending ||
              !form.hospital_number.trim() ||
              !form.full_name.trim()
            }
          >
            {mutation.isPending ? 'Saving…' : 'Register patient'}
          </button>
        </div>
      </form>
    </section>
  )
}
