import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getFhirEverything } from '../api/client'

export default function FhirExport({
  patientId,
  hospitalNumber,
}: {
  patientId: number
  hospitalNumber: string
}) {
  const [open, setOpen] = useState(false)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['fhir', patientId],
    queryFn: () => getFhirEverything(patientId),
    enabled: open,
  })

  function download() {
    if (!data) return
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/fhir+json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${hospitalNumber || `patient-${patientId}`}-fhir.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="fhir">
      <div className="fhir__head">
        <h2>FHIR export (R4)</h2>
        <button className="btn" onClick={() => setOpen((o) => !o)}>
          {open ? 'Hide' : 'View bundle'}
        </button>
      </div>
      <p className="muted small">
        Standards-based export as a FHIR R4 Bundle (Patient + ServiceRequests).
      </p>

      {open && (
        <>
          {isLoading && <p className="muted small">Loading…</p>}
          {isError && <p className="error">{(error as Error).message}</p>}
          {data ? (
            <>
              <div className="form-actions" style={{ justifyContent: 'flex-start' }}>
                <button className="btn btn--primary" onClick={download}>
                  Download .json
                </button>
              </div>
              <pre className="fhir__json">
                {JSON.stringify(data, null, 2)}
              </pre>
            </>
          ) : null}
        </>
      )}
    </div>
  )
}
