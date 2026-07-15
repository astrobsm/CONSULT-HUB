import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getDashboardSummary } from '../api/client'
import type { DashboardSummary, Priority } from '../api/types'

function fmtMinutes(min: number | null): string {
  if (min == null) return '—'
  if (min < 60) return `${Math.round(min)}m`
  const h = Math.floor(min / 60)
  const m = Math.round(min % 60)
  return m ? `${h}h ${m}m` : `${h}h`
}

// Priority uses the reserved status palette (label always present).
const PRIORITY_META: Record<Priority, { label: string; cls: string }> = {
  emergency: { label: 'Emergency', cls: 'crit' },
  urgent: { label: 'Urgent', cls: 'warn' },
  routine: { label: 'Routine', cls: 'neutral' },
}

const STATUS_ORDER = [
  'submitted', 'received', 'viewed', 'acknowledged', 'accepted', 'seen',
  'transferred', 'delegated', 'returned', 'escalated', 'completed',
  'rejected', 'cancelled',
]

export default function DashboardPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboardSummary,
  })

  if (isLoading) return <p className="muted">Loading…</p>
  if (isError) return <p className="error">{(error as Error).message}</p>
  if (!data) return null

  return (
    <section className="dash">
      <div className="page-head">
        <h1>Dashboard</h1>
        <Link to="/consultations/new" className="btn btn--primary">
          + New consult
        </Link>
      </div>

      <Tiles data={data} />

      <div className="dash__cols">
        <PendingByPriority data={data} />
        <StatusBreakdown data={data} />
      </div>

      <TopSpecialties data={data} />
    </section>
  )
}

function Tiles({ data }: { data: DashboardSummary }) {
  const pct = Math.round(data.completion_rate * 100)
  return (
    <div className="tiles">
      <Link to="/consultations" className="tile">
        <span className="tile__value">{data.pending}</span>
        <span className="tile__label">Pending consults</span>
      </Link>
      <div className="tile">
        <span className="tile__value">{data.today}</span>
        <span className="tile__label">Created today</span>
      </div>
      <div className={`tile ${data.overdue > 0 ? 'tile--critical' : ''}`}>
        <span className="tile__value">
          {data.overdue > 0 && <span className="tile__dot" aria-hidden />}
          {data.overdue}
        </span>
        <span className="tile__label">Overdue (no ack)</span>
      </div>
      <div className={`tile ${data.escalated > 0 ? 'tile--warning' : ''}`}>
        <span className="tile__value">{data.escalated}</span>
        <span className="tile__label">Escalated</span>
      </div>
      <div className="tile">
        <span className="tile__value">{pct}%</span>
        <span className="tile__label">Completion rate</span>
      </div>
      <div className="tile">
        <span className="tile__value">{fmtMinutes(data.avg_ack_minutes)}</span>
        <span className="tile__label">Avg. acknowledgement</span>
      </div>
      <div className="tile">
        <span className="tile__value">
          {fmtMinutes(data.avg_completion_minutes)}
        </span>
        <span className="tile__label">Avg. completion</span>
      </div>
    </div>
  )
}

function PendingByPriority({ data }: { data: DashboardSummary }) {
  const entries = (Object.keys(PRIORITY_META) as Priority[]).map((p) => ({
    p,
    count: data.by_priority_pending[p] ?? 0,
  }))
  const max = Math.max(1, ...entries.map((e) => e.count))

  return (
    <div className="panel">
      <h2>Pending by priority</h2>
      <ul className="bars">
        {entries.map(({ p, count }) => (
          <li key={p} className="bars__row">
            <span className="bars__label">
              <span className={`sdot sdot--${PRIORITY_META[p].cls}`} aria-hidden />
              {PRIORITY_META[p].label}
            </span>
            <span className="bars__track">
              <span
                className={`bars__fill bars__fill--${PRIORITY_META[p].cls}`}
                style={{ width: `${(count / max) * 100}%` }}
              />
            </span>
            <span className="bars__count">{count}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function StatusBreakdown({ data }: { data: DashboardSummary }) {
  const entries = STATUS_ORDER.filter((s) => (data.by_status[s] ?? 0) > 0).map(
    (s) => ({ s, count: data.by_status[s] }),
  )
  const max = Math.max(1, ...entries.map((e) => e.count))

  return (
    <div className="panel">
      <h2>By status</h2>
      {entries.length === 0 ? (
        <p className="muted">No consultations yet.</p>
      ) : (
        <ul className="bars">
          {entries.map(({ s, count }) => (
            <li key={s} className="bars__row">
              <span className="bars__label">{s.replace(/_/g, ' ')}</span>
              <span className="bars__track">
                <span
                  className="bars__fill bars__fill--seq"
                  style={{ width: `${(count / max) * 100}%` }}
                />
              </span>
              <span className="bars__count">{count}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function TopSpecialties({ data }: { data: DashboardSummary }) {
  if (data.top_specialties.length === 0) return null
  const max = Math.max(1, ...data.top_specialties.map((s) => s.count))
  return (
    <div className="panel">
      <h2>Top specialties</h2>
      <ul className="bars">
        {data.top_specialties.map((s) => (
          <li key={s.specialty} className="bars__row">
            <span className="bars__label">{s.specialty}</span>
            <span className="bars__track">
              <span
                className="bars__fill bars__fill--seq"
                style={{ width: `${(s.count / max) * 100}%` }}
              />
            </span>
            <span className="bars__count">{s.count}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
