import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (
            id.includes('plotly.js-dist-min') ||
            id.includes('react-plotly.js')
          ) {
            return 'plotly-vendor'
          }
        },
      },
    },
  },
})