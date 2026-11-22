import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // El front llama a /api/* y Vite lo reenvía al FastAPI local.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
