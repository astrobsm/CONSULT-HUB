import { useQuery } from '@tanstack/react-query'
import {
  getNoShowRisk,
  getSuggestions,
  getWaitEstimate,
} from '../api/client'
import type { Appointment } from '../api/types'

function fmt(iso: string): string {
  return new Date(iso).toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export default function InsightsModal({
  appointment,
  onClose,
}: {
  appointment: Appointment
  onClose: () => void
}) {
  const id = appointment.id
  const risk = useQuery({
    queryKey: ['risk', id],
    queryFn: () => getNoShowRisk(id),
  })
  const wait = useQuery({
    queryKey: ['wait', id],
    queryFn: () => getWaitEstimate(id),
  })
  const suggestions = useQuery({
    queryKey: ['suggestions', id],
    queryFn: () => getSuggestions(id),
  })

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__head">
          <h2>Appointment insights</h2>
          <button className="btn" onClick={onClose}>
            Close
          </button>
        </div>
        <p className="muted small">
          {appointment.patient_name} · {appointment.appointment_number}
        </p>
        <p className="muted small">
          Estimates are heuristic (data-driven), not predictions.
        </p>

        <h3 className="insight-h">No-show risk</h3>
        {risk.data && (
          <p>
            <span className={`badge badge--risk-${risk.data.band}`}>
              {risk.data.band} · {Math.round(risk.data.score * 100)}%
            </span>{' '}
            <span className="muted small">
              {String(risk.data.factors.basis ?? '')}, lead{' '}
              {String(risk.data.factors.lead_days ?? '')}d
            </span>
          </p>
        )}

        <h3 className="insight-h">Estimated wait</h3>
        {wait.data && (
          <p>
            <strong>{wait.data.estimated_wait_minutes} min</strong>{' '}
            <span className="muted small">
              ({wait.data.ahead_in_queue} ahead ×{' '}
              {wait.data.slot_minutes} min)
            </span>
          </p>
        )}

        <h3 className="insight-h">Earlier / alternative slots</h3>
        {suggestions.data && suggestions.data.length === 0 && (
          <p className="muted small">No suggestions found.</p>
        )}
        {suggestions.data && suggestions.data.length > 0 && (
          <ul className="suggestion-list">
            {suggestions.data.map((s, i) => (
              <li key={i}>
                {fmt(s.slot_start)} · {s.station_name}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
