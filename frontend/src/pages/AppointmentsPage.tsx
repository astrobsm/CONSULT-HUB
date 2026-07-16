import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  bookAppointment,
  getAvailability,
  listAppointments,
  listClinics,
  listPatients,
  transitionAppointment,
} from '../api/client'
import {
  APPOINTMENT_TRANSITIONS,
  APPOINTMENT_TYPES,
  type AppointmentStatus,
} from '../api/types'

function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate(),
  ).padStart(2, '0')}`
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function AppointmentsPage() {
  const queryClient = useQueryClient()
  const [date, setDate] = useState(todayIso())
  const [clinicId, setClinicId] = useState<number | ''>('')

  const clinics = useQuery({ queryKey: ['clinics'], queryFn: listClinics })
  const patients = useQuery({
    queryKey: ['patients', ''],
    queryFn: () => listPatients(),
  })

  const appts = useQuery({
    queryKey: ['appointments', clinicId, date],
    queryFn: () =>
      listAppointments({
        clinicId: clinicId || undefined,
        date,
      }),
  })

  return (
    <section>
      <div className="page-head">
        <h1>Appointments</h1>
      </div>

      <BookingPanel
        clinics={clinics.data ?? []}
        patients={patients.data ?? []}
        onBooked={() => {
          queryClient.invalidateQueries({ queryKey: ['appointments'] })
        }}
      />

      <div className="panel">
        <div className="appt-filters">
          <h2>Clinic list / queue</h2>
          <div className="filter-row">
            <label className="filter">
              Clinic{' '}
              <select
                value={clinicId}
                onChange={(e) =>
                  setClinicId(e.target.value ? Number(e.target.value) : '')
                }
              >
                <option value="">All</option>
                {clinics.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="filter">
              Date{' '}
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
          </div>
        </div>

        {appts.data && appts.data.length === 0 && (
          <p className="muted small">No appointments for this filter.</p>
        )}
        {appts.data && appts.data.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Patient</th>
                <th>Station</th>
                <th>Type</th>
                <th>Q#</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {appts.data.map((a) => (
                <tr key={a.id}>
                  <td>{fmtTime(a.slot_start)}</td>
                  <td>{a.patient_name}</td>
                  <td className="muted">{a.station_name}</td>
                  <td className="muted">
                    {a.appointment_type.replace(/_/g, ' ')}
                  </td>
                  <td>{a.queue_position ?? '—'}</td>
                  <td>
                    <span className={`badge badge--status badge--${a.status}`}>
                      {a.status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td>
                    <ApptActions
                      id={a.id}
                      status={a.status}
                      onChange={() =>
                        queryClient.invalidateQueries({
                          queryKey: ['appointments'],
                        })
                      }
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}

function ApptActions({
  id,
  status,
  onChange,
}: {
  id: number
  status: AppointmentStatus
  onChange: () => void
}) {
  const next = APPOINTMENT_TRANSITIONS[status]
  const mut = useMutation({
    mutationFn: (to: AppointmentStatus) =>
      transitionAppointment(
        id,
        to,
        to === 'cancelled' ? 'Cancelled by staff' : undefined,
      ),
    onSuccess: onChange,
  })
  if (next.length === 0) return <span className="muted small">—</span>
  return (
    <div className="appt-actions">
      {next.map((s) => (
        <button
          key={s}
          className="btn btn--sm"
          disabled={mut.isPending}
          onClick={() => mut.mutate(s)}
        >
          {s.replace(/_/g, ' ')}
        </button>
      ))}
    </div>
  )
}

function BookingPanel({
  clinics,
  patients,
  onBooked,
}: {
  clinics: { id: number; name: string }[]
  patients: { id: number; full_name: string; hospital_number: string }[]
  onBooked: () => void
}) {
  const [patientId, setPatientId] = useState<number | ''>('')
  const [clinicId, setClinicId] = useState<number | ''>('')
  const [date, setDate] = useState(todayIso())
  const [type, setType] = useState('new_patient')
  const [checked, setChecked] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const availability = useQuery({
    queryKey: ['availability', clinicId, date],
    queryFn: () => getAvailability(Number(clinicId), date),
    enabled: checked && clinicId !== '',
  })

  // Union of times where at least one station is free (system auto-assigns).
  const freeTimes = useMemo(() => {
    const set = new Set<string>()
    availability.data?.stations.forEach((s) =>
      s.free_slots.forEach((t) => set.add(t)),
    )
    return [...set].sort()
  }, [availability.data])

  const book = useMutation({
    mutationFn: (slot: string) =>
      bookAppointment({
        clinic_id: Number(clinicId),
        patient_id: Number(patientId),
        slot_start: slot,
        appointment_type: type as never,
      }),
    onSuccess: (appt) => {
      setResult(
        `Booked ${appt.appointment_number} — ${appt.station_name} at ${fmtTime(
          appt.slot_start,
        )}`,
      )
      setError(null)
      availability.refetch()
      onBooked()
    },
    onError: (e) => {
      setError((e as Error).message)
      setResult(null)
      availability.refetch()
    },
  })

  const canCheck = patientId !== '' && clinicId !== ''

  return (
    <div className="panel">
      <h2>Book appointment</h2>
      <div className="grid">
        <label className="field">
          <span>Patient *</span>
          <select
            value={patientId}
            onChange={(e) =>
              setPatientId(e.target.value ? Number(e.target.value) : '')
            }
          >
            <option value="">— select —</option>
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name} ({p.hospital_number})
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Clinic *</span>
          <select
            value={clinicId}
            onChange={(e) => {
              setClinicId(e.target.value ? Number(e.target.value) : '')
              setChecked(false)
            }}
          >
            <option value="">— select —</option>
            {clinics.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Date</span>
          <input
            type="date"
            value={date}
            onChange={(e) => {
              setDate(e.target.value)
              setChecked(false)
            }}
          />
        </label>
        <label className="field">
          <span>Type</span>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            {APPOINTMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="form-actions" style={{ justifyContent: 'flex-start' }}>
        <button
          className="btn btn--primary"
          disabled={!canCheck}
          onClick={() => {
            setChecked(true)
            setResult(null)
            setError(null)
          }}
        >
          Check availability
        </button>
      </div>

      {result && <p className="success-msg">{result}</p>}
      {error && <p className="error">{error}</p>}

      {checked && availability.isLoading && (
        <p className="muted small">Loading slots…</p>
      )}
      {checked && availability.data && (
        <>
          <p className="muted small">
            Pick a time — the system assigns the least-busy free station.
          </p>
          {freeTimes.length === 0 ? (
            <p className="muted small">
              No available slots (clinic closed or fully booked).
            </p>
          ) : (
            <div className="slots">
              {freeTimes.map((t) => (
                <button
                  key={t}
                  className="slot"
                  disabled={book.isPending}
                  onClick={() => book.mutate(t)}
                >
                  {fmtTime(t)}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
