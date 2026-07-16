import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getUnreadCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../api/client'
import type { AppNotification } from '../api/types'

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Poll the unread count so the badge reflects escalations as they fire.
  const { data: count } = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: getUnreadCount,
    // WebSocket push drives updates; this is just a slow fallback.
    refetchInterval: 60000,
  })

  const { data: notifications } = useQuery({
    queryKey: ['notifications', 'list'],
    queryFn: () => listNotifications(),
    enabled: open,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['notifications'] })

  const readOne = useMutation({
    mutationFn: (id: number) => markNotificationRead(id),
    onSuccess: invalidate,
  })
  const readAll = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: invalidate,
  })

  // Close on outside click.
  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  const unread = count?.unread ?? 0

  function openNotification(n: AppNotification) {
    if (!n.is_read) readOne.mutate(n.id)
    setOpen(false)
    if (n.consultation_id) navigate(`/consultations/${n.consultation_id}`)
  }

  return (
    <div className="bell" ref={ref}>
      <button
        className="bell__btn"
        onClick={() => setOpen((o) => !o)}
        aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
      >
        <span aria-hidden>🔔</span>
        {unread > 0 && (
          <span className="bell__badge">{unread > 99 ? '99+' : unread}</span>
        )}
      </button>

      {open && (
        <div className="bell__panel">
          <div className="bell__head">
            <strong>Notifications</strong>
            {unread > 0 && (
              <button
                className="bell__link"
                onClick={() => readAll.mutate()}
                disabled={readAll.isPending}
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="bell__list">
            {!notifications && <p className="muted small pad">Loading…</p>}
            {notifications && notifications.length === 0 && (
              <p className="muted small pad">No notifications.</p>
            )}
            {notifications?.map((n) => (
              <button
                key={n.id}
                className={`bell__item ${n.is_read ? '' : 'bell__item--unread'}`}
                onClick={() => openNotification(n)}
              >
                <span className={`bell__kind bell__kind--${n.kind}`}>
                  {n.kind === 'escalation' ? '▲' : '•'}
                </span>
                <span className="bell__text">
                  <span className="bell__title">{n.title}</span>
                  <span className="bell__body">{n.body}</span>
                  <span className="muted small">
                    {new Date(n.created_at).toLocaleString()}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
