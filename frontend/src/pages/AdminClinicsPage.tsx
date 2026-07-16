import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createClinic,
  createStation,
  listClinics,
  listStations,
  updateStation,
} from '../api/client'
import { STATION_TYPES, type Clinic } from '../api/types'
import AdminTabs from '../components/AdminTabs'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function AdminClinicsPage() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<number | null>(null)

  const clinics = useQuery({ queryKey: ['clinics'], queryFn: listClinics })

  const [form, setForm] = useState({
    name: '',
    subspecialty: '',
    location: '',
    open_time: '08:00',
    close_time: '16:00',
    slot_duration_minutes: 20,
    operating_days: '0,1,2,3,4',
  })

  const create = useMutation({
    mutationFn: () => createClinic(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clinics'] })
      setForm({ ...form, name: '', subspecialty: '', location: '' })
    },
  })

  return (
    <section>
      <div className="page-head">
        <h1>Administration</h1>
      </div>
      <AdminTabs />

      <div className="dash__cols">
        <div className="panel">
          <h2>New clinic</h2>
          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault()
              create.mutate()
            }}
          >
            <label className="field field--full">
              <span>Clinic name *</span>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Hand Clinic"
              />
            </label>
            <div className="grid">
              <label className="field">
                <span>Subspecialty</span>
                <input
                  value={form.subspecialty}
                  onChange={(e) =>
                    setForm({ ...form, subspecialty: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Location</span>
                <input
                  value={form.location}
                  onChange={(e) =>
                    setForm({ ...form, location: e.target.value })
                  }
                />
              </label>
            </div>
            <div className="grid">
              <label className="field">
                <span>Open</span>
                <input
                  type="time"
                  value={form.open_time}
                  onChange={(e) =>
                    setForm({ ...form, open_time: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Close</span>
                <input
                  type="time"
                  value={form.close_time}
                  onChange={(e) =>
                    setForm({ ...form, close_time: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Slot (min)</span>
                <input
                  type="number"
                  min={5}
                  max={120}
                  value={form.slot_duration_minutes}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      slot_duration_minutes: Number(e.target.value),
                    })
                  }
                />
              </label>
            </div>
            <label className="field field--full">
              <span>Operating days</span>
              <div className="daypick">
                {WEEKDAYS.map((d, i) => {
                  const set = new Set(
                    form.operating_days
                      .split(',')
                      .filter(Boolean)
                      .map(Number),
                  )
                  const on = set.has(i)
                  return (
                    <button
                      type="button"
                      key={d}
                      className={`daypick__day ${on ? 'daypick__day--on' : ''}`}
                      onClick={() => {
                        if (on) set.delete(i)
                        else set.add(i)
                        setForm({
                          ...form,
                          operating_days: [...set].sort().join(','),
                        })
                      }}
                    >
                      {d}
                    </button>
                  )
                })}
              </div>
            </label>
            {create.isError && (
              <p className="error">{(create.error as Error).message}</p>
            )}
            <div className="form-actions">
              <button
                className="btn btn--primary"
                disabled={create.isPending || !form.name.trim()}
              >
                Create clinic
              </button>
            </div>
          </form>
        </div>

        <div className="panel">
          <h2>Clinics</h2>
          {clinics.data && clinics.data.length === 0 && (
            <p className="muted small">No clinics yet.</p>
          )}
          <ul className="clinic-list">
            {clinics.data?.map((cl) => (
              <li key={cl.id}>
                <button
                  className={`clinic-list__item ${
                    selected === cl.id ? 'clinic-list__item--active' : ''
                  }`}
                  onClick={() => setSelected(cl.id)}
                >
                  <strong>{cl.name}</strong>
                  <span className="muted small">
                    {cl.open_time}–{cl.close_time} · {cl.slot_duration_minutes}
                    min · {cl.is_active ? 'active' : 'inactive'}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {selected != null && (
        <StationManager
          clinic={clinics.data?.find((c) => c.id === selected)}
          clinicId={selected}
        />
      )}
    </section>
  )
}

function StationManager({
  clinicId,
  clinic,
}: {
  clinicId: number
  clinic: Clinic | undefined
}) {
  const queryClient = useQueryClient()
  const stations = useQuery({
    queryKey: ['stations', clinicId],
    queryFn: () => listStations(clinicId),
  })
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['stations', clinicId] })

  const [name, setName] = useState('')
  const [type, setType] = useState<string>('consultant')
  const [room, setRoom] = useState('')

  const nextNumber = (stations.data?.length ?? 0) + 1

  const add = useMutation({
    mutationFn: () =>
      createStation(clinicId, {
        station_number: nextNumber,
        name: name || `Station ${nextNumber}`,
        station_type: type as never,
        room_number: room || null,
      }),
    onSuccess: () => {
      invalidate()
      setName('')
      setRoom('')
    },
  })

  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      updateStation(id, { status: status as never }),
    onSuccess: invalidate,
  })

  return (
    <div className="panel">
      <h2>Stations — {clinic?.name}</h2>
      <table className="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Name</th>
            <th>Type</th>
            <th>Room</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {stations.data?.map((s) => (
            <tr key={s.id}>
              <td>{s.station_number}</td>
              <td>{s.name}</td>
              <td className="muted">{s.station_type.replace(/_/g, ' ')}</td>
              <td className="muted">{s.room_number ?? '—'}</td>
              <td>
                <select
                  value={s.status}
                  onChange={(e) =>
                    setStatus.mutate({ id: s.id, status: e.target.value })
                  }
                >
                  <option value="active">active</option>
                  <option value="inactive">inactive</option>
                  <option value="maintenance">maintenance</option>
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form
        className="form"
        onSubmit={(e) => {
          e.preventDefault()
          add.mutate()
        }}
      >
        <div className="grid">
          <label className="field">
            <span>Station name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={`Station ${nextNumber}`}
            />
          </label>
          <label className="field">
            <span>Type</span>
            <select value={type} onChange={(e) => setType(e.target.value)}>
              {STATION_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Room</span>
            <input value={room} onChange={(e) => setRoom(e.target.value)} />
          </label>
        </div>
        <div className="form-actions">
          <button className="btn btn--primary" disabled={add.isPending}>
            + Add station
          </button>
        </div>
      </form>
    </div>
  )
}
