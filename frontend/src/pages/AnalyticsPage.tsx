import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getClinicAnalytics, listClinics } from '../api/client'
import type { AppointmentAnalytics } from '../api/types'

function isoDaysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate(),
  ).padStart(2, '0')}`
}
function isoToday(): string {
  return isoDaysAgo(0)
}
function pct(x: number): string {
  return `${Math.round(x * 100)}%`
}

export default function AnalyticsPage() {
  const clinics = useQuery({ queryKey: ['clinics'], queryFn: listClinics })
  const [clinicId, setClinicId] = useState<number | ''>('')
  const [from, setFrom] = useState(isoDaysAgo(30))
  const [to, setTo] = useState(isoToday())

  const analytics = useQuery({
    queryKey: ['analytics', clinicId, from, to],
    queryFn: () => getClinicAnalytics(Number(clinicId), from, to),
    enabled: clinicId !== '',
  })

  return (
    <section className="dash">
      <div className="page-head">
        <h1>Appointment analytics</h1>
      </div>

      <div className="panel">
        <div className="filter-row">
          <label className="filter">
            Clinic{' '}
            <select
              value={clinicId}
              onChange={(e) =>
                setClinicId(e.target.value ? Number(e.target.value) : '')
              }
            >
              <option value="">— select —</option>
              {clinics.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label className="filter">
            From{' '}
            <input
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
          </label>
          <label className="filter">
            To{' '}
            <input
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
          </label>
        </div>
      </div>

      {clinicId === '' && (
        <p className="muted">Select a clinic to see analytics.</p>
      )}
      {analytics.isLoading && <p className="muted">Loading…</p>}
      {analytics.data && <Report data={analytics.data} />}
    </section>
  )
}

function Report({ data }: { data: AppointmentAnalytics }) {
  if (data.total === 0)
    return <p className="muted">No appointments in this range.</p>

  return (
    <>
      <div className="tiles">
        <Tile value={String(data.total)} label="Appointments" />
        <Tile value={pct(data.completion_rate)} label="Completion rate" />
        <Tile
          value={pct(data.no_show_rate)}
          label="No-show rate"
          warn={data.no_show_rate > 0.2}
        />
        <Tile
          value={pct(data.cancellation_rate)}
          label="Cancellation rate"
        />
        <Tile value={String(data.did_not_attend)} label="Did not attend" />
        <Tile value={String(data.completed)} label="Completed" />
      </div>

      <div className="dash__cols">
        <Bars title="By appointment type" data={data.by_type} />
        <Bars
          title="Peak hours"
          data={Object.fromEntries(
            data.peak_hours.map((p) => [`${p.hour}:00`, p.count]),
          )}
        />
      </div>

      <div className="panel">
        <h2>Station load</h2>
        <BarRows
          rows={data.by_station.map((s) => ({
            label: s.station_name,
            value: s.count,
          }))}
        />
      </div>
    </>
  )
}

function Tile({
  value,
  label,
  warn,
}: {
  value: string
  label: string
  warn?: boolean
}) {
  return (
    <div className={`tile ${warn ? 'tile--warning' : ''}`}>
      <span className="tile__value">{value}</span>
      <span className="tile__label">{label}</span>
    </div>
  )
}

function Bars({
  title,
  data,
}: {
  title: string
  data: Record<string, number>
}) {
  const rows = Object.entries(data).map(([label, value]) => ({ label, value }))
  return (
    <div className="panel">
      <h2>{title}</h2>
      {rows.length === 0 ? (
        <p className="muted small">No data.</p>
      ) : (
        <BarRows rows={rows} />
      )}
    </div>
  )
}

function BarRows({ rows }: { rows: { label: string; value: number }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value))
  return (
    <ul className="bars">
      {rows.map((r) => (
        <li key={r.label} className="bars__row">
          <span className="bars__label">{r.label.replace(/_/g, ' ')}</span>
          <span className="bars__track">
            <span
              className="bars__fill bars__fill--seq"
              style={{ width: `${(r.value / max) * 100}%` }}
            />
          </span>
          <span className="bars__count">{r.value}</span>
        </li>
      ))}
    </ul>
  )
}
