import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createUser,
  inviteUser,
  listDepartments,
  listRoles,
  listUsers,
  updateUser,
  type CreateUserInput,
} from '../api/client'
import { useAuth } from '../auth/AuthContext'
import AdminTabs from '../components/AdminTabs'

const EMPTY: CreateUserInput = {
  full_name: '',
  email: '',
  password: '',
  role: 'registrar',
  designation: '',
  department_id: null,
}

export default function AdminUsersPage() {
  const { user: me } = useAuth()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<CreateUserInput>(EMPTY)
  const [showForm, setShowForm] = useState(false)
  const [invite, setInvite] = useState(false)

  const users = useQuery({ queryKey: ['users'], queryFn: listUsers })
  const roles = useQuery({ queryKey: ['roles'], queryFn: listRoles })
  const depts = useQuery({ queryKey: ['departments'], queryFn: listDepartments })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['users'] })

  const create = useMutation({
    mutationFn: (p: CreateUserInput) =>
      invite
        ? inviteUser({
            full_name: p.full_name,
            email: p.email,
            role: p.role,
            designation: p.designation ?? null,
            department_id: p.department_id ?? null,
          })
        : createUser(p),
    onSuccess: () => {
      invalidate()
      setForm(EMPTY)
      setShowForm(false)
    },
  })

  const update = useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: Parameters<typeof updateUser>[1] }) =>
      updateUser(id, patch),
    onSuccess: invalidate,
  })

  const deptName = (id: number | null) =>
    id ? depts.data?.find((d) => d.id === id)?.name ?? '—' : '—'

  return (
    <section>
      <div className="page-head">
        <h1>Administration</h1>
        <button className="btn btn--primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? 'Close' : '+ New user'}
        </button>
      </div>
      <AdminTabs />

      {showForm && (
        <form
          className="form panel"
          onSubmit={(e) => {
            e.preventDefault()
            create.mutate({
              ...form,
              designation: form.designation || null,
            })
          }}
        >
          <div className="grid">
            <label className="field">
              <span>Full name *</span>
              <input
                required
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Email *</span>
              <input
                required
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </label>
            {!invite && (
              <label className="field">
                <span>Password * (min 8)</span>
                <input
                  required={!invite}
                  type="password"
                  minLength={8}
                  value={form.password}
                  onChange={(e) =>
                    setForm({ ...form, password: e.target.value })
                  }
                />
              </label>
            )}
          </div>

          <label className="check-inline">
            <input
              type="checkbox"
              checked={invite}
              onChange={(e) => setInvite(e.target.checked)}
            />
            <span>
              Send email invite instead — the user sets their own password
            </span>
          </label>
          <div className="grid">
            <label className="field">
              <span>Role</span>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
              >
                {roles.data?.map((r) => (
                  <option key={r} value={r}>
                    {r.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Department</span>
              <select
                value={form.department_id ?? ''}
                onChange={(e) =>
                  setForm({
                    ...form,
                    department_id: e.target.value ? Number(e.target.value) : null,
                  })
                }
              >
                <option value="">—</option>
                {depts.data?.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Designation</span>
              <input
                value={form.designation ?? ''}
                onChange={(e) => setForm({ ...form, designation: e.target.value })}
              />
            </label>
          </div>
          {create.isError && (
            <p className="error">{(create.error as Error).message}</p>
          )}
          <div className="form-actions">
            <button className="btn btn--primary" disabled={create.isPending}>
              {create.isPending
                ? 'Saving…'
                : invite
                  ? 'Send invite'
                  : 'Create user'}
            </button>
          </div>
        </form>
      )}

      {users.isLoading && <p className="muted">Loading…</p>}
      {users.data && (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Department</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {users.data.map((u) => (
              <tr key={u.id} className={u.is_active ? '' : 'row--inactive'}>
                <td>{u.full_name}</td>
                <td className="muted">{u.email}</td>
                <td>
                  <select
                    value={u.role}
                    disabled={update.isPending}
                    onChange={(e) =>
                      update.mutate({ id: u.id, patch: { role: e.target.value } })
                    }
                  >
                    {roles.data?.map((r) => (
                      <option key={r} value={r}>
                        {r.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="muted">{deptName(u.department_id)}</td>
                <td>
                  {u.id === me?.id ? (
                    <span className="muted small">You</span>
                  ) : (
                    <button
                      className="btn"
                      disabled={update.isPending}
                      onClick={() =>
                        update.mutate({
                          id: u.id,
                          patch: { is_active: !u.is_active },
                        })
                      }
                    >
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {update.isError && (
        <p className="error">{(update.error as Error).message}</p>
      )}
    </section>
  )
}
