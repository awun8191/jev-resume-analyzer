import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1', port: 5273, strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:8017', changeOrigin: true } },
  },
  test: {
    environment: 'jsdom', globals: true, setupFiles: ['./tests/setup.ts'], css: false,
    exclude: ['**/node_modules/**', '**/tests/browser/**'],
  },
})
