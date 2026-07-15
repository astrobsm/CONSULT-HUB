import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listConsultations } from '../api/client'
import { STATUSES, type ConsultationStatus } from '../api/types'
import {
  EscalationBadge,
  PriorityBadge,
  StatusBadge,
} from '../components/StatusBadge'

export default function ConsultationsListPage() {
  const [statusFilter, setStatusFilter] = useState<ConsultationStatus | ''>('')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['consultations', statusFilter],
    queryFn: () =>
      listConsultations(statusFilter ? { status: statusFilter } : undefined),
  })

  return (
    <section>
      <div className="page-head">
        <h1>Consultations</h1>
        <label className="filter">
          Status:{' '}
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as ConsultationStatus | '')
            }
          >
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isLoading && <p className="muted">Loading…</p>}
      {isError && <p className="error">Failed to load: {(error as Error).message}</p>}

      {data && data.length === 0 && (
        <div className="empty">
          <p>No consultations yet.</p>
          <Link to="/consultations/new" className="btn btn--primary">
            Create the first one
          </Link>
        </div>
      )}

      {data && data.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>#</th>
              <th>Reason</th>
              <th>Specialty</th>
              <th>Type</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {data.map((c) => (
              <tr key={c.id}>
                <td>
                  <Link to={`/consultations/${c.id}`}>{c.id}</Link>
                </td>
                <td className="cell-reason">
                  <Link to={`/consultations/${c.id}`}>{c.reason}</Link>
                </td>
                <td>{c.target_specialty ?? '—'}</td>
                <td className="muted">{c.consultation_type.replace(/_/g, ' ')}</td>
                <td>
                  <PriorityBadge priority={c.priority} />
                </td>
                <td>
                  <StatusBadge status={c.status} />{' '}
                  <EscalationBadge level={c.escalation_level} />
                </td>
                <td className="muted">
                  {new Date(c.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
