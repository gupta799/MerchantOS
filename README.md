# AgentReady

AgentReady is an automated computer-use telemetry lab for agent-ready commerce.

The demo runs autonomous CUA simulations against a controlled RidgeRun merchant storefront, captures screenshots, DOM summaries, actions, browser results, and policy verification, then turns the trajectory into a merchant telemetry dashboard with MCP readiness recommendations.

## Quick Start

```bash
npm install
npm run install:frontend
npm run test
npm run dev
```

Open `http://127.0.0.1:5175`. The Merchant OS dashboard automatically creates a simulation run, attaches the browser SDK to the mock storefront, starts the autonomous computer-use loop, and streams telemetry into the dashboard. Use `Rerun Simulation` for a fresh run.

## Runtime Modes

Default local demo:

```bash
export AGENTREADY_HARNESS_MODE=deepagents
export AGENTREADY_HARNESS_MODEL_PROVIDER=llamacpp
export AGENTREADY_HARNESS_MODEL=gemma4-e4b-it
export AGENTREADY_COMPUTER_CLIENT=scripted
```

Run Gemma 4 from Hugging Face through llama.cpp:

```bash
brew install llama.cpp
npm run model:gemma4
```

Use Tzafon Northstar as the computer-use provider:

```bash
export AGENTREADY_COMPUTER_CLIENT=tzafon
export TZAFON_API_KEY=...
export TZAFON_COMPUTER_MODEL=tzafon.northstar-cua-fast-1.6
```

The harness model and computer-use provider are intentionally separate: DeepAgents/Gemma orchestrates the simulation and telemetry interpretation; Tzafon/OpenAI/scripted computer clients perform the visual action loop.

## Simulation APIs

- `POST /api/simulations`
- `GET /api/simulations/{id}`
- `GET /api/simulations/{id}/trace`
- `GET /api/simulations/{id}/telemetry`
- `GET /api/simulations/{id}/mcp-readiness`

## Tests

```bash
npm run test:backend
npm run test:frontend
npm run test:e2e
npm run test:e2e:tzafon
```

For the Gemma harness smoke, keep `npm run model:gemma4` running and then run:

```bash
npm run test:e2e:gemma4
```
