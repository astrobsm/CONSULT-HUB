/**
 * Offline write-queue — true offline-first mutations.
 *
 * When a mutation can't reach the server (offline / dropped connection) it is
 * stored in IndexedDB and replayed automatically when connectivity returns
 * (on the `online` event, on load, and when the service worker's Background
 * Sync fires). The auth token is NOT stored — it's read fresh at replay time,
 * so token refresh and sign-out are respected.
 */
const DB_NAME = 'consulthub-offline'
const STORE = 'mutations'

// Token storage keys (kept in sync with api/client.ts and portal/portalClient.ts).
const STAFF_TOKEN_KEY = 'consulthub_token'
const PATIENT_TOKEN_KEY = 'consulthub_patient_token'

export type Channel = 'staff' | 'patient'
export interface QueuedMutation {
  id?: number
  channel: Channel
  method: string
  url: string
  body?: string
  label: string
  createdAt: number
  // The token subject (user/patient id) that created this mutation. A queued
  // write is only ever replayed while THAT identity is signed in — never under
  // a different user who logs into the same device later.
  subject?: string
}

// Queued mutations expire after a week so they can't be replayed as a stale,
// surprising write long after the fact (or linger forever unreplayable).
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000

function tokenKey(channel: Channel): string {
  return channel === 'patient' ? PATIENT_TOKEN_KEY : STAFF_TOKEN_KEY
}

/** Best-effort read of the `sub` claim from a JWT (no signature check). */
function tokenSubject(token: string | null): string | null {
  if (!token) return null
  try {
    const payload = token.split('.')[1]
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(json).sub ?? null
  } catch {
    return null
  }
}

export class OfflineQueued extends Error {
  constructor() {
    super('Saved offline — will sync when you are back online.')
  }
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE, {
        keyPath: 'id',
        autoIncrement: true,
      })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function withStore<T>(
  mode: IDBTransactionMode,
  fn: (s: IDBObjectStore) => IDBRequest,
): Promise<T> {
  const db = await openDb()
  return new Promise<T>((resolve, reject) => {
    const store = db.transaction(STORE, mode).objectStore(STORE)
    const req = fn(store)
    req.onsuccess = () => resolve(req.result as T)
    req.onerror = () => reject(req.error)
  })
}

export function enqueue(item: QueuedMutation): Promise<number> {
  // Stamp the mutation with the identity that created it, so a later user on a
  // shared device can never have it replayed under their token.
  const subject =
    item.subject ?? tokenSubject(localStorage.getItem(tokenKey(item.channel)))
  return withStore<number>('readwrite', (s) =>
    s.add({ ...item, subject: subject ?? undefined }),
  ).then((id) => {
    notify()
    requestBackgroundSync()
    return id
  })
}

function getAll(): Promise<QueuedMutation[]> {
  return withStore<QueuedMutation[]>('readonly', (s) => s.getAll())
}

function remove(id: number): Promise<void> {
  return withStore('readwrite', (s) => s.delete(id))
}

export async function pendingCount(): Promise<number> {
  try {
    return (await getAll()).length
  } catch {
    return 0
  }
}

let flushing = false

export async function flushQueue(): Promise<void> {
  if (flushing || !navigator.onLine) return
  flushing = true
  try {
    const items = await getAll()
    for (const item of items) {
      // Drop mutations that have aged out rather than replaying a stale write.
      if (Date.now() - item.createdAt > MAX_AGE_MS) {
        if (item.id != null) await remove(item.id)
        continue
      }
      const token = localStorage.getItem(tokenKey(item.channel))
      // Only replay under the same identity that enqueued it. If nobody (or a
      // different user) is signed in on this channel, leave it queued.
      if (item.subject && tokenSubject(token) !== item.subject) continue
      try {
        const res = await fetch(item.url, {
          method: item.method,
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: item.body,
        })
        // Success, or a definitive rejection (slot gone / invalid / auth) —
        // drop it. Only a 5xx or network error keeps it for retry.
        if (res.status < 500) {
          if (item.id != null) await remove(item.id)
        } else {
          break
        }
      } catch {
        break // still offline — try again later
      }
    }
  } finally {
    flushing = false
    notify()
  }
}

// ---- listeners (for the offline indicator) ----

type Listener = () => void
const listeners = new Set<Listener>()
export function subscribe(fn: Listener): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
function notify() {
  listeners.forEach((l) => l())
}

function requestBackgroundSync() {
  navigator.serviceWorker?.ready
    .then((reg) => (reg as ServiceWorkerRegistration & {
      sync?: { register: (t: string) => Promise<void> }
    }).sync?.register('flush-queue'))
    .catch(() => {})
}

export function setupOfflineSync() {
  window.addEventListener('online', () => {
    notify()
    flushQueue()
  })
  window.addEventListener('offline', notify)
  // The service worker asks us to flush when Background Sync fires.
  navigator.serviceWorker?.addEventListener('message', (e) => {
    if (e.data === 'flush-queue') flushQueue()
  })
  // Attempt a flush on startup and periodically as a fallback.
  flushQueue()
  setInterval(flushQueue, 30000)
}
