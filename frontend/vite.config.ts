import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Two pages: the back office (index.html) and the public estimate (estimate.html).
// The embeddable widget is a separate build, see vite.widget.config.ts.
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: { main: 'index.html', estimate: 'estimate.html' },
    },
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
