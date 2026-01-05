import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    allowedHosts: ['metadata.neighborhood', 'localhost'],
    proxy: {
      '/api': {
        target: 'http://metadata.neighborhood:8000',
        changeOrigin: true,
      },
    },
  },
})
