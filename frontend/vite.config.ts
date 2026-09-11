import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The production build is emitted to `dist/` and copied into the FastAPI image,
// which serves it from `/` (single port, no nginx).
//
// During local development `npm run dev` proxies the API routes to a FastAPI
// instance listening on :8080 so the frontend can run on its own port.
const API_TARGET = process.env.VITE_DEV_API_TARGET || 'http://localhost:8080';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/auth': { target: API_TARGET, changeOrigin: true },
      '/foods': { target: API_TARGET, changeOrigin: true },
      '/log': { target: API_TARGET, changeOrigin: true },
      '/api': { target: API_TARGET, changeOrigin: true },
    },
  },
});
