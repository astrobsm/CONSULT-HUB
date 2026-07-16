import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { getAvailability, rescheduleAppointment } from '../api/client'
import type { Appointment } from '../api/types'

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

export default function RescheduleDialog({
  appointment,
  onClose,
  onDone,
}: {
  appointment: Appointment
  onClose: () => void
  onDone: () => void
}) {
  const [date, setDate] = useState(todayIso())
  const [error, setError] = useState<string | null>(null)

  const availability = useQuery({
    queryKey: ['availability', appointment.clinic_id, date],
    queryFn: () => getAvailability(appointment.clinic_id, date),
  })

  const freeTimes = useMemo(() => {
    const set = new Set<string>()
    availability.data?.stations.forEach((s) =>
      s.free_slots.forEach((t) => set.add(t)),
    )
    return [...set].sort()
  }, [availability.data])

  const move = useMutation({
    mutationFn: (slot: string) => rescheduleAppointment(appointment.id, slot),
    onSuccess: onDone,
    onError: (e) => setError((e as Error).message),
  })

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__head">
          <h2>Reschedule appointment</h2>
          <button className="btn" onClick={onClose}>
            Close
          </button>
        </div>
        <p className="muted small">
          {appointment.patient_name} · {appointment.clinic_name} · currently{' '}
          {fmtTime(appointment.slot_start)}
        </p>

        <label className="field">
          <span>New date</span>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>

        {error && <p className="error">{error}</p>}
        {availability.isLoading && <p className="muted small">Loading…</p>}
        {availability.data &&
          (freeTimes.length === 0 ? (
            <p className="muted small">No available slots on this date.</p>
          ) : (
            <div className="slots">
              {freeTimes.map((t) => (
                <button
                  key={t}
                  className="slot"
                  disabled={move.isPending}
                  onClick={() => move.mutate(t)}
                >
                  {fmtTime(t)}
                </button>
              ))}
            </div>
          ))}
      </div>
    </div>
  )
}
