import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  base: process.env.ANDROID_BUILD ? '/__android__/' : '/',
  build: { target: 'chrome100' },
  server: { host: '127.0.0.1', proxy: { '/api': 'http://127.0.0.1:8000' } },
  plugins: [
    react(),
    tailwindcss(),
  ],
})