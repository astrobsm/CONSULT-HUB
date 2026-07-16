import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getToken } from '../api/client'
import { useAuth } from '../auth/AuthContext'

/**
 * Opens a WebSocket to the backend and turns server push events into query
 * invalidations, so the notification bell and open chat threads update live.
 * Reconnects with a short backoff; no-ops when signed out.
 */
export default function RealtimeBridge() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!user) return
    let closed = false
    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | undefined

    function connect() {
      const token = getToken()
      if (!token || closed) return
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const url = `${proto}://${location.host}/api/ws?token=${encodeURIComponent(token)}`
      const ws = new WebSocket(url)
      socket = ws

      ws.onmessage = (e) => {
        try {
          const ev = JSON.parse(e.data)
          if (ev.type === 'notification') {
            queryClient.invalidateQueries({ queryKey: ['notifications'] })
          } else if (ev.type === 'message') {
            queryClient.invalidateQueries({ queryKey: ['notifications'] })
            queryClient.invalidateQueries({
              queryKey: ['messages', ev.consultation_id],
            })
          }
        } catch {
          /* ignore malformed frames */
        }
      }
      ws.onclose = () => {
        if (!closed) retry = setTimeout(connect, 3000)
      }
      ws.onerror = () => {
        try {
          ws.close()
        } catch {
          /* noop */
        }
      }
    }

    connect()
    return () => {
      closed = true
      if (retry) clearTimeout(retry)
      if (socket) {
        try {
          socket.close()
        } catch {
          /* noop */
        }
      }
    }
  }, [user, queryClient])

  return null
}
