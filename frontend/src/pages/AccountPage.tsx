import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { changePassword, updateProfile } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { ACCENTS, applyAppearance, FONTS } from '../theme'

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

  // Appearance
  const [theme, setTheme] = useState('system')
  const [accent, setAccent] = useState('blue')
  const [font, setFont] = useState('system')
  const [apprMsg, setApprMsg] = useState<string | null>(null)

  useEffect(() => {
    if (user) {
      setTheme(user.theme)
      setAccent(user.accent)
      setFont(user.font_family)
    }
  }, [user])

  // Apply live as the user tweaks (before saving).
  function previewAppearance(next: {
    theme?: string
    accent?: string
    font_family?: string
  }) {
    applyAppearance({
      theme: next.theme ?? theme,
      accent: next.accent ?? accent,
      font_family: next.font_family ?? font,
    })
  }

  const appearance = useMutation({
    mutationFn: () =>
      updateProfile({ theme, accent, font_family: font }),
    onSuccess: async () => {
      await refresh()
      setApprMsg('Appearance saved.')
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
        <h2>Appearance</h2>
        <div className="grid">
          <label className="field">
            <span>Theme</span>
            <select
              value={theme}
              onChange={(e) => {
                setTheme(e.target.value)
                previewAppearance({ theme: e.target.value })
              }}
            >
              <option value="system">System</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </label>
          <label className="field">
            <span>Font</span>
            <select
              value={font}
              onChange={(e) => {
                setFont(e.target.value)
                previewAppearance({ font_family: e.target.value })
              }}
            >
              {Object.keys(FONTS).map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="field">
          <span>Accent colour</span>
          <div className="accent-swatches">
            {Object.entries(ACCENTS).map(([name, c]) => (
              <button
                key={name}
                type="button"
                className={`swatch ${accent === name ? 'swatch--on' : ''}`}
                style={{ background: c.primary }}
                title={name}
                aria-label={name}
                onClick={() => {
                  setAccent(name)
                  previewAppearance({ accent: name })
                }}
              />
            ))}
          </div>
        </div>
        {apprMsg && <p className="success-msg">{apprMsg}</p>}
        <div className="form-actions">
          <button
            className="btn btn--primary"
            disabled={appearance.isPending}
            onClick={() => {
              setApprMsg(null)
              appearance.mutate()
            }}
          >
            {appearance.isPending ? 'Saving…' : 'Save appearance'}
          </button>
        </div>
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
