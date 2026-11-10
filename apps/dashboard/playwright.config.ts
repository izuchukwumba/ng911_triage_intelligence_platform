import { defineConfig, devices } from '@playwright/test';

// Accessibility tests (design v1.2, section 11.2) run the real dashboard
// against a real backend: an in-memory API with authentication explicitly
// disabled, which is only ever acceptable on an isolated test machine.
// Locally, already-running servers on these ports are reused.
const BACKEND_CMD =
  process.env.NTIP_E2E_BACKEND_CMD ??
  'uv run --project ../../backend uvicorn ntip.api:create_app --factory --port 8000';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // the tests share one backend
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: BACKEND_CMD,
      url: 'http://localhost:8000/health/live',
      env: {
        NTIP_AUTH_DISABLED: '1',
        NTIP_RATE_LIMIT_PER_MINUTE: '0',
        NTIP_GIS_REFERENCE: '../../data/gis/synthetic-ssap-1.0.0.csv',
      },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: 'npx vite --port 5173 --strictPort',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
