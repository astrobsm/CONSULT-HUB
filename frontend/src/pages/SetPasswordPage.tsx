import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { confirmPasswordSet } from '../api/client'

export default function SetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const navigate = useNavigate()

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const mutation = useMutation({
    mutationFn: () => confirmPasswordSet(token, password),
    onSuccess: () => setDone(true),
    onError: (e) => setError((e as Error).message),
  })

  return (
    <div className="login">
      <div className="login__card">
        <h1 className="login__brand">
          Consult<span>HUB</span>
        </h1>
        <p className="muted">Set a new password.</p>

        {!token && (
          <p className="error">
            Missing or invalid link. Request a new one from the sign-in page.
          </p>
        )}

        {done ? (
          <>
            <p className="success-msg">Password set. You can sign in now.</p>
            <button
              className="btn btn--primary"
              onClick={() => navigate('/login')}
            >
              Go to sign in
            </button>
          </>
        ) : (
          token && (
            <form
              className="form"
              onSubmit={(e) => {
                e.preventDefault()
                setError(null)
                if (password !== confirm) {
                  setError('Passwords do not match.')
                  return
                }
                mutation.mutate()
              }}
            >
              <label className="field field--full">
                <span>New password (min 8)</span>
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <label className="field field--full">
                <span>Confirm password</span>
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                />
              </label>
              {error && <p className="error">{error}</p>}
              <button
                type="submit"
                className="btn btn--primary"
                disabled={mutation.isPending}
              >
                {mutation.isPending ? 'Saving…' : 'Set password'}
              </button>
              <p className="muted small login__hint">
                <Link to="/login">Back to sign in</Link>
              </p>
            </form>
          )
        )}
      </div>
    </div>
  )
}
