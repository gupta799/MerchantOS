import { defineConfig, devices } from "@playwright/test";

const frontendPort = 5176;
const backendPort = 8001;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /gemma4.*\.spec\.ts/,
  timeout: 180_000,
  expect: {
    timeout: 30_000
  },
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: "on-first-retry"
  },
  webServer: [
    {
      command:
        "AGENTREADY_HARNESS_MODE=deepagents " +
        "AGENTREADY_HARNESS_MODEL_PROVIDER=llamacpp " +
        "AGENTREADY_HARNESS_MODEL=gemma4-e4b-it " +
        "AGENTREADY_LLAMACPP_BASE_URL=http://127.0.0.1:8080/v1 " +
        "AGENTREADY_COMPUTER_CLIENT=scripted " +
        `FRONTEND_BASE_URL=http://127.0.0.1:${frontendPort} ` +
        `BACKEND_BASE_URL=http://127.0.0.1:${backendPort} ` +
        `uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      url: `http://127.0.0.1:${backendPort}/api/health`,
      reuseExistingServer: true,
      timeout: 120_000
    },
    {
      command:
        `VITE_BACKEND_BASE_URL=http://127.0.0.1:${backendPort} ` +
        `npm run dev --prefix frontend -- --host 127.0.0.1 --port ${frontendPort}`,
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: true,
      timeout: 120_000
    }
  ],
  projects: [
    {
      name: "chromium-gemma4",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
