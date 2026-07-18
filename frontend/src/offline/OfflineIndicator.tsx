import { useEffect, useState } from 'react'
import { pendingCount, subscribe } from './queue'

/** A small fixed banner shown when offline or when writes are queued. */
export default function OfflineIndicator() {
  const [online, setOnline] = useState(navigator.onLine)
  const [pending, setPending] = useState(0)

  useEffect(() => {
    const refresh = () => {
      setOnline(navigator.onLine)
      pendingCount().then(setPending)
    }
    refresh()
    const unsub = subscribe(refresh)
    window.addEventListener('online', refresh)
    window.addEventListener('offline', refresh)
    return () => {
      unsub()
      window.removeEventListener('online', refresh)
      window.removeEventListener('offline', refresh)
    }
  }, [])

  if (online && pending === 0) return null

  return (
    <div className={`offline-bar ${online ? 'offline-bar--sync' : ''}`}>
      {!online && <span>● Offline</span>}
      {pending > 0 && (
        <span>
          {online ? 'Syncing' : 'Queued'} {pending} change
          {pending === 1 ? '' : 's'}
          {online ? '…' : ''}
        </span>
      )}
    </div>
  )
}
