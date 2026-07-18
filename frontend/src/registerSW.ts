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

/** Drop cached API responses (call on sign-out so the next user starts clean). */
export function clearApiCache() {
  navigator.serviceWorker?.controller?.postMessage('clear-api-cache')
}
