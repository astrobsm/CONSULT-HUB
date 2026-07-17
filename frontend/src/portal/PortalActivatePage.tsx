import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { portalActivate } from './portalClient'

export default function PortalActivatePage() {
  const [hospitalNumber, setHospitalNumber] = useState('')
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)

  const mutation = useMutation({
    mutationFn: () => portalActivate(hospitalNumber, email),
    onSuccess: () => setSent(true),
  })

  return (
    <div className="login">
      <div className="login__card">
        <h1 className="login__brand">
          Consult<span>HUB</span> · Activate
        </h1>
        {sent ? (
          <>
            <p className="success-msg">
              If your details match our records, an activation link has been
              emailed to you.
            </p>
            <p className="muted small">
              In development the link is printed to the backend console.
            </p>
            <Link to="/portal/login" className="btn">
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
            <p className="muted">
              Enter your hospital number and the email on your record.
            </p>
            <label className="field field--full">
              <span>Hospital number</span>
              <input
                required
                value={hospitalNumber}
                onChange={(e) => setHospitalNumber(e.target.value)}
                placeholder="MRN-000000"
              />
            </label>
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
              className="btn btn--primary"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? 'Sending…' : 'Send activation link'}
            </button>
            <p className="muted small login__hint">
              <Link to="/portal/login">Back to sign in</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
