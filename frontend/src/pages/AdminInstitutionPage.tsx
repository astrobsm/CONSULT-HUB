import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  brandImageUrl,
  getInstitution,
  listInstitutions,
  updateInstitution,
  uploadBrandImage,
  type Institution,
} from '../api/client'
import { useAuth } from '../auth/AuthContext'
import AdminTabs from '../components/AdminTabs'

export default function AdminInstitutionPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  // The admin's own institution (super admins get the first one for editing).
  const institutions = useQuery({
    queryKey: ['institutions'],
    queryFn: listInstitutions,
  })
  const instId = user?.institution_id ?? institutions.data?.[0]?.id ?? null

  const inst = useQuery({
    queryKey: ['institution', instId],
    queryFn: () => getInstitution(instId as number),
    enabled: instId != null,
  })

  if (!instId)
    return (
      <section>
        <div className="page-head">
          <h1>Administration</h1>
        </div>
        <AdminTabs />
        <p className="muted">No institution to manage.</p>
      </section>
    )

  return (
    <section>
      <div className="page-head">
        <h1>Administration</h1>
      </div>
      <AdminTabs />
      {inst.data && (
        <Editor
          institution={inst.data}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ['institution'] })
            queryClient.invalidateQueries({ queryKey: ['branding'] })
          }}
        />
      )}
    </section>
  )
}

function Editor({
  institution,
  onSaved,
}: {
  institution: Institution
  onSaved: () => void
}) {
  const [form, setForm] = useState({
    name: institution.name,
    motto: institution.motto ?? '',
    address: institution.address ?? '',
    phone: institution.phone ?? '',
    email: institution.email ?? '',
    website: institution.website ?? '',
    primary_color: institution.primary_color ?? '#1e6fd9',
  })
  const [msg, setMsg] = useState<string | null>(null)
  const [logoUrl, setLogoUrl] = useState<string | null>(null)
  const logoRef = useRef<HTMLInputElement>(null)
  const watermarkRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    let revoke: string | null = null
    if (institution.has_logo) {
      brandImageUrl(institution.id, 'logo').then((u) => {
        revoke = u
        setLogoUrl(u)
      })
    } else {
      setLogoUrl(null)
    }
    return () => {
      if (revoke) URL.revokeObjectURL(revoke)
    }
  }, [institution.id, institution.has_logo])

  const save = useMutation({
    mutationFn: () => updateInstitution(institution.id, form),
    onSuccess: () => {
      setMsg('Institution details saved.')
      onSaved()
    },
  })

  const uploadLogo = useMutation({
    mutationFn: (file: File) =>
      uploadBrandImage(institution.id, 'logo', file),
    onSuccess: onSaved,
  })
  const uploadWatermark = useMutation({
    mutationFn: (file: File) =>
      uploadBrandImage(institution.id, 'watermark', file),
    onSuccess: onSaved,
  })

  function set<K extends keyof typeof form>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }))
  }

  return (
    <>
      <div className="panel">
        <div className="brand-preview">
          {logoUrl && (
            <img src={logoUrl} alt="logo" className="brand-logo" />
          )}
          <div>
            <strong>{form.name}</strong>
            {form.motto && (
              <div className="muted small">{form.motto}</div>
            )}
          </div>
        </div>
      </div>

      <div className="panel">
        <h2>Institution details</h2>
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault()
            setMsg(null)
            save.mutate()
          }}
        >
          <label className="field field--full">
            <span>Hospital name *</span>
            <input
              required
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
            />
          </label>
          <label className="field field--full">
            <span>Motto</span>
            <input
              value={form.motto}
              onChange={(e) => set('motto', e.target.value)}
              placeholder="e.g. Care with compassion"
            />
          </label>
          <div className="grid">
            <label className="field">
              <span>Phone</span>
              <input
                value={form.phone}
                onChange={(e) => set('phone', e.target.value)}
              />
            </label>
            <label className="field">
              <span>Email</span>
              <input
                value={form.email}
                onChange={(e) => set('email', e.target.value)}
              />
            </label>
            <label className="field">
              <span>Website</span>
              <input
                value={form.website}
                onChange={(e) => set('website', e.target.value)}
              />
            </label>
          </div>
          <label className="field field--full">
            <span>Address</span>
            <input
              value={form.address}
              onChange={(e) => set('address', e.target.value)}
            />
          </label>
          <label className="field">
            <span>Brand colour</span>
            <input
              type="color"
              value={form.primary_color}
              onChange={(e) => set('primary_color', e.target.value)}
            />
          </label>
          {save.isError && (
            <p className="error">{(save.error as Error).message}</p>
          )}
          {msg && <p className="success-msg">{msg}</p>}
          <div className="form-actions">
            <button className="btn btn--primary" disabled={save.isPending}>
              {save.isPending ? 'Saving…' : 'Save details'}
            </button>
          </div>
        </form>
      </div>

      <div className="panel">
        <h2>Logo & watermark</h2>
        <div className="grid">
          <div className="field">
            <span>Logo (shown in the header)</span>
            <input
              ref={logoRef}
              type="file"
              accept="image/*"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) uploadLogo.mutate(f)
              }}
            />
            {institution.has_logo && (
              <span className="muted small">A logo is set.</span>
            )}
          </div>
          <div className="field">
            <span>Watermark (faint page background)</span>
            <input
              ref={watermarkRef}
              type="file"
              accept="image/*"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) uploadWatermark.mutate(f)
              }}
            />
            {institution.has_watermark && (
              <span className="muted small">A watermark is set.</span>
            )}
          </div>
        </div>
        {(uploadLogo.isError || uploadWatermark.isError) && (
          <p className="error">
            {(
              (uploadLogo.error || uploadWatermark.error) as Error
            )?.message}
          </p>
        )}
      </div>
    </>
  )
}
