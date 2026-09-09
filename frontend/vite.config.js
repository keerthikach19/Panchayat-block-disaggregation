import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, req, res) => {
            if (err.code === 'ECONNREFUSED') {
              if (res.writeHead && !res.headersSent) {
                res.writeHead(503, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                  error: 'BackendNotReady',
                  message: 'FastAPI backend on port 8000 is still initializing. Retrying...'
                }));
              }
            }
          });
        }
      }
    }
  }
})
