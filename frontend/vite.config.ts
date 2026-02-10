import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

const apiTarget = process.env.VITE_API_TARGET || 'http://localhost:8000';

export default defineConfig({
  plugins: [svelte()],
  resolve: {
    conditions: [
      'browser',
      'module', 
      process.env.NODE_ENV === 'production' ? 'production' : 'development',
      'default',
    ],
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/ws': {
        target: apiTarget.replace('http', 'ws'),
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: process.env.NODE_ENV !== 'production',
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
  },
});
