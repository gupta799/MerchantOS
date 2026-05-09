import { defineConfig, devices } from "@playwright/test";

const frontendPort = 5177;
const backendPort = 8002;

export default defineConfig({
  testDir: "./e2e",
  testIgnore: /(gemma4|tzafon).*\.spec\.ts/,
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: "on-first-retry"
  },
  webServer: [
    {
      command:
        "AGENTREADY_HARNESS_MODE=scripted " +
        "AGENTREADY_COMPUTER_CLIENT=scripted " +
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
