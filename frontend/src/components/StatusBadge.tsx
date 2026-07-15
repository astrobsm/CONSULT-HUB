import type { ConsultationStatus, Priority } from '../api/types'

export function StatusBadge({ status }: { status: ConsultationStatus }) {
  return <span className={`badge badge--status badge--${status}`}>{label(status)}</span>
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <span className={`badge badge--priority badge--${priority}`}>{priority}</span>
  )
}

function label(status: ConsultationStatus): string {
  return status.replace(/_/g, ' ')
}

export function EscalationBadge({ level }: { level: number }) {
  if (level <= 0) return null
  return (
    <span className="badge badge--escalation" title={`Escalation level ${level}`}>
      ▲ Escalated · L{level}
    </span>
  )
}
