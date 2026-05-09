# AgentReady Backend

FastAPI backend for the automated computer-use telemetry lab.

The backend creates simulation runs, coordinates the browser SDK/WebSocket loop, delegates visual actions to a configured computer-use provider, records traces, and returns telemetry plus MCP readiness recommendations.

Default mode uses DeepAgents with `AGENTREADY_HARNESS_MODEL_PROVIDER=llamacpp` and `AGENTREADY_HARNESS_MODEL=gemma4-e4b-it` for the simulation harness brain, plus `ScriptedComputerClient` for deterministic local browser actions.

Set `AGENTREADY_COMPUTER_CLIENT=tzafon`, `TZAFON_API_KEY`, and `TZAFON_COMPUTER_MODEL=tzafon.northstar-cua-fast-1.6` to use Tzafon Northstar as the computer-use provider.

Set `AGENTREADY_BROWSER_ENV=kernel`, `KERNEL_API_KEY`, and `AGENTREADY_PUBLIC_STOREFRONT_URL` to run the same DeepAgents-guided simulation in a Kernel cloud browser. In that mode the backend uses Kernel Computer Controls for screenshots, clicks, typing, scrolling, and live-view telemetry instead of waiting for the local browser SDK websocket.
