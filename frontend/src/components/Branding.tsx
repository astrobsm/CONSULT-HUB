import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { brandImageUrl, getInstitution } from '../api/client'
import { useAuth } from '../auth/AuthContext'

function useInstitution() {
  const { user } = useAuth()
  const id = user?.institution_id ?? null
  return useQuery({
    queryKey: ['branding', id],
    queryFn: () => getInstitution(id as number),
    enabled: id != null,
  })
}

/** Logo + institution name for the app header (falls back to ConsultHUB). */
export function BrandHeader() {
  const inst = useInstitution()
  const [logo, setLogo] = useState<string | null>(null)

  useEffect(() => {
    let revoke: string | null = null
    if (inst.data?.has_logo) {
      brandImageUrl(inst.data.id, 'logo').then((u) => {
        revoke = u
        setLogo(u)
      })
    } else {
      setLogo(null)
    }
    return () => {
      if (revoke) URL.revokeObjectURL(revoke)
    }
  }, [inst.data?.id, inst.data?.has_logo])

  if (inst.data) {
    return (
      <span className="brand-inline">
        {logo && <img src={logo} alt="" className="app__brand-logo" />}
        {inst.data.name}
      </span>
    )
  }
  return (
    <>
      Consult<span>HUB</span>
    </>
  )
}

/** Faint full-page watermark from the institution's uploaded image. */
export default function Branding() {
  const inst = useInstitution()
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    let revoke: string | null = null
    if (inst.data?.has_watermark) {
      brandImageUrl(inst.data.id, 'watermark').then((u) => {
        revoke = u
        setUrl(u)
      })
    } else {
      setUrl(null)
    }
    return () => {
      if (revoke) URL.revokeObjectURL(revoke)
    }
  }, [inst.data?.id, inst.data?.has_watermark])

  if (!url) return null
  return (
    <div
      className="app__watermark"
      style={{ backgroundImage: `url(${url})` }}
      aria-hidden
    />
  )
}
