import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: { '/api': process.env.VITE_API_URL ?? 'http://localhost:8080' },
  },
  test: { environment: 'jsdom', include: ['src/**/*.test.ts'] },
})
