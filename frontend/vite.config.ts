import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
const apiProxy = {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: true, // forward WebSocket upgrades (/api/ws)
  },
}

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: apiProxy },
  // `vite preview` serves the production build (with the service worker active);
  // it needs the same API proxy.
  preview: { port: 5173, proxy: apiProxy },
})
