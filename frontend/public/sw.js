/* ConsultHUB service worker — offline-first runtime caching.
 *
 * Strategy:
 *  - navigations  -> network first, fall back to the cached app shell ("/")
 *  - static assets -> stale-while-revalidate (instant, refreshed in background)
 *  - GET /api      -> network first with a short timeout, fall back to cache
 *                     (keeps the app usable on poor / dropped connections)
 *  - non-GET       -> always network (mutations need connectivity)
 */
const VERSION = 'v1'
const SHELL = `consulthub-shell-${VERSION}`
const ASSETS = `consulthub-assets-${VERSION}`
const API = `consulthub-api-${VERSION}`
const API_TIMEOUT = 3500

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL).then((c) => c.add('/')).catch(() => {}),
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys()
      await Promise.all(
        keys
          .filter((k) => !k.endsWith(VERSION))
          .map((k) => caches.delete(k)),
      )
      await self.clients.claim()
    })(),
  )
})

self.addEventListener('message', (event) => {
  if (event.data === 'clear-api-cache') caches.delete(API)
})

// Background Sync: when connectivity returns, nudge open clients to replay the
// offline write-queue (the auth token lives in the page, not the worker).
self.addEventListener('sync', (event) => {
  if (event.tag === 'flush-queue') {
    event.waitUntil(
      (async () => {
        const clients = await self.clients.matchAll({
          includeUncontrolled: true,
        })
        clients.forEach((c) => c.postMessage('flush-queue'))
      })(),
    )
  }
})

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error('timeout')), ms)
    promise.then(
      (v) => {
        clearTimeout(t)
        resolve(v)
      },
      (e) => {
        clearTimeout(t)
        reject(e)
      },
    )
  })
}

async function networkFirst(request) {
  const cache = await caches.open(API)
  try {
    const res = await withTimeout(fetch(request), API_TIMEOUT)
    if (res && res.ok) cache.put(request, res.clone())
    return res
  } catch {
    const cached = await cache.match(request)
    if (cached) return cached
    return new Response(JSON.stringify({ detail: 'You are offline.' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}

async function navigation(request) {
  try {
    return await fetch(request)
  } catch {
    const cache = await caches.open(SHELL)
    return (await cache.match('/')) || Response.error()
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(ASSETS)
  const cached = await cache.match(request)
  const network = fetch(request)
    .then((res) => {
      if (res && res.ok) cache.put(request, res.clone())
      return res
    })
    .catch(() => cached)
  return cached || network
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request))
  } else if (request.mode === 'navigate') {
    event.respondWith(navigation(request))
  } else {
    event.respondWith(staleWhileRevalidate(request))
  }
})
