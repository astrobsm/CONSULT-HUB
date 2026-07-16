import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { requestPasswordReset } from '../api/client'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)

  const mutation = useMutation({
    mutationFn: () => requestPasswordReset(email),
    onSuccess: () => setSent(true),
  })

  return (
    <div className="login">
      <div className="login__card">
        <h1 className="login__brand">
          Consult<span>HUB</span>
        </h1>
        <p className="muted">Reset your password.</p>

        {sent ? (
          <>
            <p className="success-msg">
              If an account exists for <strong>{email}</strong>, a password-reset
              link has been sent.
            </p>
            <p className="muted small">
              In development the link is printed to the backend console.
            </p>
            <Link to="/login" className="btn">
              Back to sign in
            </Link>
          </>
        ) : (
          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault()
              mutation.mutate()
            }}
          >
            <label className="field field--full">
              <span>Email</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? 'Sending…' : 'Send reset link'}
            </button>
            <p className="muted small login__hint">
              <Link to="/login">Back to sign in</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
