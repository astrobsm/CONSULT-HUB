/** Register the offline-first service worker (production builds only —
 * a SW in dev interferes with Vite's HMR). */
export function registerServiceWorker() {
  if (!('serviceWorker' in navigator) || !import.meta.env.PROD) return
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      /* offline features simply won't be available */
    })
  })
}

/**
 * Drop cached API responses. MUST be called on every sign-in and sign-out (both
 * staff and patient) and on token expiry, so one user's cached PHI can never be
 * served to the next person on a shared device.
 *
 * We delete the caches directly from the page (reliable even when no service
 * worker controls the page yet) AND message the SW as a belt-and-braces signal.
 */
export function clearApiCache() {
  navigator.serviceWorker?.controller?.postMessage('clear-api-cache')
  if ('caches' in window) {
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.includes('api'))
            .map((k) => caches.delete(k)),
        ),
      )
      .catch(() => {
        /* cache API unavailable — nothing to clear */
      })
  }
}
