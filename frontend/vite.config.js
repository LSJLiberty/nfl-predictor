import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Settings for the tests (run with `npm test`):
  test: {
    environment: 'jsdom',              // a pretend browser, so React can draw the page
    globals: true,                     // lets tests use describe/it/expect without importing
    setupFiles: './src/setupTests.js', // runs once before the tests
  },
})