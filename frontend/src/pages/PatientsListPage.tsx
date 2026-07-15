import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listPatients } from '../api/client'

export default function PatientsListPage() {
  const [term, setTerm] = useState('')
  const [search, setSearch] = useState('')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['patients', search],
    queryFn: () => listPatients(search || undefined),
  })

  return (
    <section>
      <div className="page-head">
        <h1>Patients</h1>
        <Link to="/patients/new" className="btn btn--primary">
          + Register patient
        </Link>
      </div>

      <form
        className="search-bar"
        onSubmit={(e) => {
          e.preventDefault()
          setSearch(term)
        }}
      >
        <input
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder="Search by name or hospital number…"
        />
        <button type="submit" className="btn">
          Search
        </button>
        {search && (
          <button
            type="button"
            className="btn"
            onClick={() => {
              setTerm('')
              setSearch('')
            }}
          >
            Clear
          </button>
        )}
      </form>

      {isLoading && <p className="muted">Loading…</p>}
      {isError && (
        <p className="error">Failed to load: {(error as Error).message}</p>
      )}

      {data && data.length === 0 && (
        <div className="empty">
          <p>No patients found.</p>
          <Link to="/patients/new" className="btn btn--primary">
            Register a patient
          </Link>
        </div>
      )}

      {data && data.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Hospital #</th>
              <th>Name</th>
              <th>Age</th>
              <th>Sex</th>
              <th>Ward / Bed</th>
              <th>Primary diagnosis</th>
            </tr>
          </thead>
          <tbody>
            {data.map((p) => (
              <tr key={p.id}>
                <td>
                  <Link to={`/patients/${p.id}`}>{p.hospital_number}</Link>
                </td>
                <td>
                  <Link to={`/patients/${p.id}`}>{p.full_name}</Link>
                </td>
                <td>{p.age ?? '—'}</td>
                <td>{p.sex ?? '—'}</td>
                <td className="muted">
                  {[p.ward, p.bed].filter(Boolean).join(' / ') || '—'}
                </td>
                <td className="cell-reason muted">
                  {p.primary_diagnosis ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
