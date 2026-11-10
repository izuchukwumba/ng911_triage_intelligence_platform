import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The research backend (uvicorn ntip.api:create_app --factory) listens on :8000.
const BACKEND = process.env.NTIP_BACKEND_URL ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/v1': BACKEND,
      '/health': BACKEND,
    },
  },
});
