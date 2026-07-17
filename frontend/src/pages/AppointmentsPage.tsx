import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  bookAppointment,
  checkInByCode,
  getAvailability,
  joinWaitingList,
  listAppointments,
  listClinics,
  listPatients,
  listWaitingList,
  removeWaitingEntry,
  transitionAppointment,
} from '../api/client'
import {
  APPOINTMENT_TRANSITIONS,
  APPOINTMENT_TYPES,
  type Appointment,
  type AppointmentStatus,
} from '../api/types'
import RescheduleDialog from '../components/RescheduleDialog'
import QrModal from '../components/QrModal'
import InsightsModal from '../components/InsightsModal'

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
  const [rescheduling, setRescheduling] = useState<Appointment | null>(null)
  const [qrAppt, setQrAppt] = useState<Appointment | null>(null)
  const [insightsAppt, setInsightsAppt] = useState<Appointment | null>(null)

  const invalidateAppointments = () =>
    queryClient.invalidateQueries({ queryKey: ['appointments'] })

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

      <CheckInBar onDone={invalidateAppointments} />

      {clinicId !== '' && (
        <WaitingListPanel clinicId={clinicId} date={date} />
      )}

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
                    <div className="appt-actions">
                      <button
                        className="btn btn--sm"
                        onClick={() => setQrAppt(a)}
                      >
                        QR
                      </button>
                      <button
                        className="btn btn--sm"
                        onClick={() => setInsightsAppt(a)}
                        title="No-show risk, wait, suggestions"
                      >
                        insights
                      </button>
                      <ApptActions
                        appt={a}
                        onChange={invalidateAppointments}
                        onReschedule={() => setRescheduling(a)}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {rescheduling && (
        <RescheduleDialog
          appointment={rescheduling}
          onClose={() => setRescheduling(null)}
          onDone={() => {
            setRescheduling(null)
            invalidateAppointments()
          }}
        />
      )}

      {qrAppt && (
        <QrModal appointment={qrAppt} onClose={() => setQrAppt(null)} />
      )}

      {insightsAppt && (
        <InsightsModal
          appointment={insightsAppt}
          onClose={() => setInsightsAppt(null)}
        />
      )}
    </section>
  )
}

function CheckInBar({ onDone }: { onDone: () => void }) {
  const [code, setCode] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const mut = useMutation({
    mutationFn: () => checkInByCode(code.trim()),
    onSuccess: (a) => {
      setMsg(`Checked in ${a.patient_name} — queue #${a.queue_position}`)
      setErr(null)
      setCode('')
      onDone()
    },
    onError: (e) => {
      setErr((e as Error).message)
      setMsg(null)
    },
  })
  return (
    <div className="panel">
      <h2>Reception check-in</h2>
      <form
        className="search-bar"
        onSubmit={(e) => {
          e.preventDefault()
          if (code.trim()) mut.mutate()
        }}
      >
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Scan or type the appointment QR code…"
        />
        <button className="btn btn--primary" disabled={mut.isPending}>
          Check in
        </button>
      </form>
      {msg && <p className="success-msg">{msg}</p>}
      {err && <p className="error">{err}</p>}
    </div>
  )
}

function WaitingListPanel({
  clinicId,
  date,
}: {
  clinicId: number
  date: string
}) {
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: ['waiting', clinicId, date],
    queryFn: () => listWaitingList(clinicId, date),
  })
  const remove = useMutation({
    mutationFn: (id: number) => removeWaitingEntry(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['waiting'] }),
  })
  const entries = data ?? []
  if (entries.length === 0) return null
  return (
    <div className="panel">
      <h2>Waiting list ({date})</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Patient</th>
            <th>Type</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.id}>
              <td>{e.patient_name}</td>
              <td className="muted">
                {e.appointment_type.replace(/_/g, ' ')}
              </td>
              <td>
                <span className={`badge badge--status badge--${e.status}`}>
                  {e.status}
                </span>
              </td>
              <td>
                {e.status === 'waiting' && (
                  <button
                    className="btn btn--sm"
                    disabled={remove.isPending}
                    onClick={() => remove.mutate(e.id)}
                  >
                    remove
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const RESCHEDULABLE: AppointmentStatus[] = [
  'booked',
  'confirmed',
  'did_not_attend',
]

function ApptActions({
  appt,
  onChange,
  onReschedule,
}: {
  appt: Appointment
  onChange: () => void
  onReschedule: () => void
}) {
  const next = APPOINTMENT_TRANSITIONS[appt.status]
  const mut = useMutation({
    mutationFn: (to: AppointmentStatus) =>
      transitionAppointment(
        appt.id,
        to,
        to === 'cancelled' ? 'Cancelled by staff' : undefined,
      ),
    onSuccess: onChange,
  })
  const canReschedule = RESCHEDULABLE.includes(appt.status)
  if (next.length === 0 && !canReschedule)
    return <span className="muted small">—</span>
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
      {canReschedule && (
        <button className="btn btn--sm" onClick={onReschedule}>
          reschedule
        </button>
      )}
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

  const waitlist = useMutation({
    mutationFn: () =>
      joinWaitingList(Number(clinicId), {
        patient_id: Number(patientId),
        target_date: `${date}T00:00:00`,
        appointment_type: type as never,
      }),
    onSuccess: () => {
      setResult('Added to the waiting list — will be offered a freed slot.')
      setError(null)
      onBooked()
    },
    onError: (e) => setError((e as Error).message),
  })

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
            <div className="waitlist-cta">
              <p className="muted small">
                No available slots (clinic closed or fully booked).
              </p>
              {patientId !== '' && (
                <button
                  className="btn"
                  disabled={waitlist.isPending}
                  onClick={() => waitlist.mutate()}
                >
                  Join waiting list
                </button>
              )}
            </div>
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
