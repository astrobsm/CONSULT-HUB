import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  portalAvailability,
  portalBook,
  portalCancel,
  portalClinics,
  portalLogout,
  portalMe,
  portalMyAppointments,
  PortalUnauthorized,
} from './portalClient'

function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate(),
  ).padStart(2, '0')}`
}
function fmt(iso: string): string {
  return new Date(iso).toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

const CANCELLABLE = ['booked', 'confirmed']

export default function PortalHomePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const me = useQuery({
    queryKey: ['portal', 'me'],
    queryFn: portalMe,
    retry: false,
  })

  if (me.isError) {
    if (me.error instanceof PortalUnauthorized) {
      navigate('/portal/login', { replace: true })
    }
  }

  const appts = useQuery({
    queryKey: ['portal', 'appointments'],
    queryFn: portalMyAppointments,
    enabled: me.isSuccess,
  })

  const cancel = useMutation({
    mutationFn: (id: number) => portalCancel(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['portal', 'appointments'] }),
  })

  if (me.isLoading) return <p className="muted center">Loading…</p>
  if (!me.data) return null

  return (
    <div className="app">
      <header className="app__header">
        <span className="app__brand">
          Consult<span>HUB</span> · Patient portal
        </span>
        <nav className="app__nav">
          <span className="user-menu__name">{me.data.full_name}</span>
          <button
            className="btn"
            onClick={() => {
              portalLogout()
              navigate('/portal/login')
            }}
          >
            Sign out
          </button>
        </nav>
      </header>

      <main className="app__main">
        <BookPanel
          onBooked={() =>
            queryClient.invalidateQueries({
              queryKey: ['portal', 'appointments'],
            })
          }
        />

        <div className="panel">
          <h2>My appointments</h2>
          {appts.data && appts.data.length === 0 && (
            <p className="muted small">No appointments yet.</p>
          )}
          {appts.data && appts.data.length > 0 && (
            <table className="table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Clinic</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {appts.data.map((a) => (
                  <tr key={a.id}>
                    <td>{fmt(a.slot_start)}</td>
                    <td>{a.clinic_name}</td>
                    <td className="muted">
                      {a.appointment_type.replace(/_/g, ' ')}
                    </td>
                    <td>
                      <span
                        className={`badge badge--status badge--${a.status}`}
                      >
                        {a.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      {CANCELLABLE.includes(a.status) && (
                        <button
                          className="btn btn--sm"
                          disabled={cancel.isPending}
                          onClick={() => cancel.mutate(a.id)}
                        >
                          cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  )
}

function BookPanel({ onBooked }: { onBooked: () => void }) {
  const [clinicId, setClinicId] = useState<number | ''>('')
  const [date, setDate] = useState(todayIso())
  const [checked, setChecked] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const clinics = useQuery({
    queryKey: ['portal', 'clinics'],
    queryFn: portalClinics,
  })
  const availability = useQuery({
    queryKey: ['portal', 'availability', clinicId, date],
    queryFn: () => portalAvailability(Number(clinicId), date),
    enabled: checked && clinicId !== '',
  })

  const freeTimes = useMemo(() => {
    const set = new Set<string>()
    availability.data?.stations.forEach((s) =>
      s.free_slots.forEach((t) => set.add(t)),
    )
    return [...set].sort()
  }, [availability.data])

  const book = useMutation({
    mutationFn: (slot: string) =>
      portalBook({
        clinic_id: Number(clinicId),
        slot_start: slot,
        appointment_type: 'review',
      }),
    onSuccess: (a) => {
      setMsg(`Booked ${a.appointment_number} for ${fmt(a.slot_start)}`)
      setError(null)
      availability.refetch()
      onBooked()
    },
    onError: (e) => {
      setError((e as Error).message)
      availability.refetch()
    },
  })

  return (
    <div className="panel">
      <h2>Book an appointment</h2>
      <div className="grid">
        <label className="field">
          <span>Clinic</span>
          <select
            value={clinicId}
            onChange={(e) => {
              setClinicId(e.target.value ? Number(e.target.value) : '')
              setChecked(false)
            }}
          >
            <option value="">— select —</option>
            {clinics.data?.map((c) => (
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
      </div>
      <div className="form-actions" style={{ justifyContent: 'flex-start' }}>
        <button
          className="btn btn--primary"
          disabled={clinicId === ''}
          onClick={() => {
            setChecked(true)
            setMsg(null)
            setError(null)
          }}
        >
          Check availability
        </button>
      </div>

      {msg && <p className="success-msg">{msg}</p>}
      {error && <p className="error">{error}</p>}

      {checked && availability.isLoading && (
        <p className="muted small">Loading…</p>
      )}
      {checked && availability.data && (
        freeTimes.length === 0 ? (
          <p className="muted small">No available times on this date.</p>
        ) : (
          <div className="slots">
            {freeTimes.map((t) => (
              <button
                key={t}
                className="slot"
                disabled={book.isPending}
                onClick={() => book.mutate(t)}
              >
                {new Date(t).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </button>
            ))}
          </div>
        )
      )}
    </div>
  )
}
