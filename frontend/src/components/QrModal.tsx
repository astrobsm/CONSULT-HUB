import { useQuery } from '@tanstack/react-query'
import { getAppointmentQrSvg } from '../api/client'
import type { Appointment } from '../api/types'

export default function QrModal({
  appointment,
  onClose,
}: {
  appointment: Appointment
  onClose: () => void
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['qr', appointment.id],
    queryFn: () => getAppointmentQrSvg(appointment.id),
  })

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__head">
          <h2>Check-in QR</h2>
          <button className="btn" onClick={onClose}>
            Close
          </button>
        </div>
        <p className="muted small">
          {appointment.patient_name} · {appointment.appointment_number}
        </p>
        {isLoading && <p className="muted small">Loading…</p>}
        {isError && <p className="error">Could not load QR code.</p>}
        {data && (
          <div className="qr-wrap" dangerouslySetInnerHTML={{ __html: data }} />
        )}
        <p className="muted small qr-code">
          Code: <code>{appointment.check_in_code}</code>
        </p>
      </div>
    </div>
  )
}
