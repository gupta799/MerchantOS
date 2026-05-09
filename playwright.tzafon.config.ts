import { defineConfig, devices } from "@playwright/test";

const frontendPort = 5178;
const backendPort = 8004;
const tzafonMockPort = 9091;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /tzafon_merchant_website\.spec\.ts/,
  timeout: 45_000,
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: "on-first-retry"
  },
  webServer: [
    {
      command: `TZAFON_MOCK_PORT=${tzafonMockPort} node e2e/tzafon_mock_server.mjs`,
      url: `http://127.0.0.1:${tzafonMockPort}/health`,
      reuseExistingServer: true
    },
    {
      command:
        "AGENTREADY_HARNESS_MODE=scripted " +
        "AGENTREADY_COMPUTER_CLIENT=tzafon " +
        "TZAFON_API_KEY=test_tzafon_key " +
        `TZAFON_API_BASE_URL=http://127.0.0.1:${tzafonMockPort} ` +
        "TZAFON_COMPUTER_MODEL=tzafon.northstar-cua-fast-1.6 " +
        `FRONTEND_BASE_URL=http://127.0.0.1:${frontendPort} ` +
        `BACKEND_BASE_URL=http://127.0.0.1:${backendPort} ` +
        `uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      url: `http://127.0.0.1:${backendPort}/api/health`,
      reuseExistingServer: true
    },
    {
      command:
        `VITE_BACKEND_BASE_URL=http://127.0.0.1:${backendPort} ` +
        `npm run dev --prefix frontend -- --host 127.0.0.1 --port ${frontendPort}`,
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: true
    }
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
