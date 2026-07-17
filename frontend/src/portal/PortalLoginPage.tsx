import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { portalLogin } from './portalClient'

export default function PortalLoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => portalLogin(email, password),
    onSuccess: () => navigate('/portal'),
    onError: (e) => setError((e as Error).message),
  })

  return (
    <div className="login">
      <div className="login__card">
        <h1 className="login__brand">
          Consult<span>HUB</span> · Patient portal
        </h1>
        <p className="muted">Sign in to manage your appointments.</p>
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault()
            setError(null)
            mutation.mutate()
          }}
        >
          <label className="field field--full">
            <span>Email</span>
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="field field--full">
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button
            className="btn btn--primary"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="muted small login__hint">
          <Link to="/portal/activate">First time? Activate your account</Link>
          {' · '}
          <Link to="/login">Staff sign-in</Link>
        </p>
      </div>
    </div>
  )
}
