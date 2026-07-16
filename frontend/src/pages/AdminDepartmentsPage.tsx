import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createDepartment,
  listDepartments,
  updateDepartment,
} from '../api/client'
import AdminTabs from '../components/AdminTabs'

export default function AdminDepartmentsPage() {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [editing, setEditing] = useState<number | null>(null)
  const [editName, setEditName] = useState('')

  const depts = useQuery({ queryKey: ['departments'], queryFn: listDepartments })
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['departments'] })

  const create = useMutation({
    mutationFn: () =>
      createDepartment({ name, specialty: specialty || null }),
    onSuccess: () => {
      invalidate()
      setName('')
      setSpecialty('')
    },
  })

  const rename = useMutation({
    mutationFn: ({ id, newName }: { id: number; newName: string }) =>
      updateDepartment(id, { name: newName }),
    onSuccess: () => {
      invalidate()
      setEditing(null)
    },
  })

  return (
    <section>
      <div className="page-head">
        <h1>Administration</h1>
      </div>
      <AdminTabs />

      <form
        className="form panel"
        onSubmit={(e) => {
          e.preventDefault()
          create.mutate()
        }}
      >
        <div className="grid">
          <label className="field">
            <span>Department name *</span>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Cardiology"
            />
          </label>
          <label className="field">
            <span>Specialty</span>
            <input
              value={specialty}
              onChange={(e) => setSpecialty(e.target.value)}
            />
          </label>
        </div>
        {create.isError && (
          <p className="error">{(create.error as Error).message}</p>
        )}
        <div className="form-actions">
          <button
            className="btn btn--primary"
            disabled={create.isPending || !name.trim()}
          >
            {create.isPending ? 'Adding…' : 'Add department'}
          </button>
        </div>
      </form>

      {depts.isLoading && <p className="muted">Loading…</p>}
      {depts.data && (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Specialty</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {depts.data.map((d) => (
              <tr key={d.id}>
                <td>
                  {editing === d.id ? (
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                    />
                  ) : (
                    d.name
                  )}
                </td>
                <td className="muted">{d.specialty ?? '—'}</td>
                <td>
                  {editing === d.id ? (
                    <>
                      <button
                        className="btn btn--primary"
                        disabled={rename.isPending || !editName.trim()}
                        onClick={() =>
                          rename.mutate({ id: d.id, newName: editName })
                        }
                      >
                        Save
                      </button>{' '}
                      <button className="btn" onClick={() => setEditing(null)}>
                        Cancel
                      </button>
                    </>
                  ) : (
                    <button
                      className="btn"
                      onClick={() => {
                        setEditing(d.id)
                        setEditName(d.name)
                      }}
                    >
                      Rename
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
