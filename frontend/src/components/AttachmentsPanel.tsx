import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteAttachment,
  downloadAttachment,
  listAttachments,
  uploadAttachment,
} from '../api/client'
import type { Attachment } from '../api/types'

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export default function AttachmentsPanel({
  consultationId,
}: {
  consultationId: number
}) {
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)

  const { data } = useQuery({
    queryKey: ['attachments', consultationId],
    queryFn: () => listAttachments(consultationId),
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['attachments', consultationId] })

  const upload = useMutation({
    mutationFn: (file: File) => uploadAttachment(consultationId, file),
    onSuccess: () => {
      invalidate()
      if (inputRef.current) inputRef.current.value = ''
    },
    onError: (e) => setError((e as Error).message),
  })

  const remove = useMutation({
    mutationFn: (id: number) => deleteAttachment(id),
    onSuccess: invalidate,
  })

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null)
    const file = e.target.files?.[0]
    if (file) upload.mutate(file)
  }

  async function onDownload(att: Attachment) {
    try {
      await downloadAttachment(att)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div className="attachments">
      <h2>Attachments</h2>

      <div className="attachments__upload">
        <input
          ref={inputRef}
          type="file"
          onChange={onPick}
          disabled={upload.isPending}
        />
        {upload.isPending && <span className="muted small">Uploading…</span>}
      </div>
      {error && <p className="error">{error}</p>}

      {data && data.length === 0 && (
        <p className="muted small">No attachments yet.</p>
      )}
      {data && data.length > 0 && (
        <ul className="att-list">
          {data.map((att) => (
            <li key={att.id} className="att-item">
              <span className="att-icon" aria-hidden>
                📎
              </span>
              <span className="att-meta">
                <button
                  className="att-name"
                  onClick={() => onDownload(att)}
                  title="Download"
                >
                  {att.filename}
                </button>
                <span className="muted small">
                  {formatBytes(att.size_bytes)} · {att.content_type}
                </span>
              </span>
              <button
                className="btn"
                disabled={remove.isPending}
                onClick={() => remove.mutate(att.id)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
