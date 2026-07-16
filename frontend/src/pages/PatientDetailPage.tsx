import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPatient, listConsultations } from '../api/client'
import { PriorityBadge, StatusBadge } from '../components/StatusBadge'
import FhirExport from '../components/FhirExport'

export default function PatientDetailPage() {
  const { id } = useParams()
  const patientId = Number(id)

  const patientQuery = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => getPatient(patientId),
    enabled: Number.isFinite(patientId),
  })

  const consultsQuery = useQuery({
    queryKey: ['consultations', 'patient', patientId],
    queryFn: () => listConsultations({ patientId }),
    enabled: Number.isFinite(patientId),
  })

  if (patientQuery.isLoading) return <p className="muted">Loading…</p>
  if (patientQuery.isError)
    return <p className="error">{(patientQuery.error as Error).message}</p>
  const p = patientQuery.data
  if (!p) return null

  return (
    <section className="detail">
      <Link to="/patients" className="back">
        ← All patients
      </Link>

      <div className="detail__head">
        <h1>{p.full_name}</h1>
        <Link
          to={`/consultations/new?patient=${p.id}`}
          className="btn btn--primary"
        >
          + New consult for this patient
        </Link>
      </div>

      <dl className="detail__grid">
        <div>
          <dt>Hospital number</dt>
          <dd>{p.hospital_number}</dd>
        </div>
        <div>
          <dt>Age / Sex</dt>
          <dd>
            {p.age ?? '—'} {p.sex ? `· ${p.sex}` : ''}
          </dd>
        </div>
        <div>
          <dt>Blood group / Genotype</dt>
          <dd>
            {p.blood_group ?? '—'} / {p.genotype ?? '—'}
          </dd>
        </div>
        <div>
          <dt>BMI</dt>
          <dd>
            {p.bmi ?? '—'}
            {p.weight_kg && p.height_cm ? (
              <span className="muted small">
                {' '}
                ({p.weight_kg}kg, {p.height_cm}cm)
              </span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt>Ward / Bed</dt>
          <dd>{[p.ward, p.bed].filter(Boolean).join(' / ') || '—'}</dd>
        </div>
        <div>
          <dt>Phone</dt>
          <dd>{p.phone ?? '—'}</dd>
        </div>
        <div className="detail__full">
          <dt>Primary diagnosis</dt>
          <dd>{p.primary_diagnosis ?? '—'}</dd>
        </div>
        <div className="detail__full">
          <dt>Drug allergies</dt>
          <dd>{p.allergies ?? '—'}</dd>
        </div>
      </dl>

      <h2>Consultations</h2>
      {consultsQuery.data && consultsQuery.data.length === 0 && (
        <p className="muted">No consultations for this patient yet.</p>
      )}
      {consultsQuery.data && consultsQuery.data.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>#</th>
              <th>Reason</th>
              <th>Specialty</th>
              <th>Priority</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {consultsQuery.data.map((c) => (
              <tr key={c.id}>
                <td>
                  <Link to={`/consultations/${c.id}`}>{c.id}</Link>
                </td>
                <td className="cell-reason">
                  <Link to={`/consultations/${c.id}`}>{c.reason}</Link>
                </td>
                <td>{c.target_specialty ?? '—'}</td>
                <td>
                  <PriorityBadge priority={c.priority} />
                </td>
                <td>
                  <StatusBadge status={c.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <FhirExport patientId={p.id} hospitalNumber={p.hospital_number} />
    </section>
  )
}
