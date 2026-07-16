import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { changePassword, updateProfile } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export default function AccountPage() {
  const { user, refresh } = useAuth()
  const [fullName, setFullName] = useState('')
  const [designation, setDesignation] = useState('')
  const [profileMsg, setProfileMsg] = useState<string | null>(null)

  useEffect(() => {
    if (user) {
      setFullName(user.full_name)
      setDesignation(user.designation ?? '')
    }
  }, [user])

  const profile = useMutation({
    mutationFn: () =>
      updateProfile({ full_name: fullName, designation: designation || null }),
    onSuccess: async () => {
      await refresh()
      setProfileMsg('Profile updated.')
    },
  })

  // Password form
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [pwMsg, setPwMsg] = useState<string | null>(null)
  const [pwError, setPwError] = useState<string | null>(null)

  const password = useMutation({
    mutationFn: () =>
      changePassword({ current_password: current, new_password: next }),
    onSuccess: () => {
      setPwMsg('Password changed.')
      setCurrent('')
      setNext('')
      setConfirm('')
    },
    onError: (e) => setPwError((e as Error).message),
  })

  if (!user) return null

  return (
    <section className="form-page">
      <h1>Account</h1>

      <div className="panel">
        <h2>Profile</h2>
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault()
            setProfileMsg(null)
            profile.mutate()
          }}
        >
          <div className="grid">
            <label className="field">
              <span>Full name</span>
              <input
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Designation</span>
              <input
                value={designation}
                onChange={(e) => setDesignation(e.target.value)}
              />
            </label>
          </div>
          <div className="account-readonly muted small">
            <span>Email: {user.email}</span>
            <span>Role: {user.role.replace(/_/g, ' ')}</span>
          </div>
          {profile.isError && (
            <p className="error">{(profile.error as Error).message}</p>
          )}
          {profileMsg && <p className="success-msg">{profileMsg}</p>}
          <div className="form-actions">
            <button className="btn btn--primary" disabled={profile.isPending}>
              {profile.isPending ? 'Saving…' : 'Save profile'}
            </button>
          </div>
        </form>
      </div>

      <div className="panel">
        <h2>Change password</h2>
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault()
            setPwMsg(null)
            setPwError(null)
            if (next !== confirm) {
              setPwError('New passwords do not match.')
              return
            }
            password.mutate()
          }}
        >
          <label className="field field--full">
            <span>Current password</span>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </label>
          <div className="grid">
            <label className="field">
              <span>New password (min 8)</span>
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={next}
                onChange={(e) => setNext(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Confirm new password</span>
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            </label>
          </div>
          {pwError && <p className="error">{pwError}</p>}
          {pwMsg && <p className="success-msg">{pwMsg}</p>}
          <div className="form-actions">
            <button className="btn btn--primary" disabled={password.isPending}>
              {password.isPending ? 'Changing…' : 'Change password'}
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}
