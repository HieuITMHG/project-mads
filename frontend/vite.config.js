import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Tách Plotly thành chunk riêng để browser cache độc lập
          'plotly-vendor': ['plotly.js-dist-min', 'react-plotly.js'],
        },
      },
    },
  },
})

