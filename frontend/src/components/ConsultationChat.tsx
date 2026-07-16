import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listMessages, postMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export default function ConsultationChat({
  consultationId,
}: {
  consultationId: number
}) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [text, setText] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  const { data: messages } = useQuery({
    queryKey: ['messages', consultationId],
    queryFn: () => listMessages(consultationId),
    // WebSocket push drives live updates; slow poll is a fallback only.
    refetchInterval: 60000,
  })

  const send = useMutation({
    mutationFn: (body: string) => postMessage(consultationId, body),
    onSuccess: () => {
      setText('')
      queryClient.invalidateQueries({ queryKey: ['messages', consultationId] })
    },
  })

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'nearest' })
  }, [messages])

  return (
    <div className="chat">
      <h2>Discussion</h2>

      <div className="chat__thread">
        {messages && messages.length === 0 && (
          <p className="muted small">
            No messages yet. Start the discussion below.
          </p>
        )}
        {messages?.map((m) => {
          const mine = m.sender_user_id === user?.id
          return (
            <div
              key={m.id}
              className={`chat__msg ${mine ? 'chat__msg--mine' : ''}`}
            >
              <div className="chat__bubble">
                {!mine && <div className="chat__sender">{m.sender_name}</div>}
                <div className="chat__body">{m.body}</div>
                <div className="chat__time">
                  {new Date(m.created_at).toLocaleString()}
                </div>
              </div>
            </div>
          )
        })}
        <div ref={endRef} />
      </div>

      <form
        className="chat__compose"
        onSubmit={(e) => {
          e.preventDefault()
          const body = text.trim()
          if (body) send.mutate(body)
        }}
      >
        <textarea
          rows={2}
          value={text}
          placeholder="Write a message…"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              const body = text.trim()
              if (body) send.mutate(body)
            }
          }}
        />
        <button
          className="btn btn--primary"
          disabled={send.isPending || !text.trim()}
        >
          {send.isPending ? 'Sending…' : 'Send'}
        </button>
      </form>
      {send.isError && (
        <p className="error">{(send.error as Error).message}</p>
      )}
    </div>
  )
}
