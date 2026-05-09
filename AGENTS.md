# MerchantOS Codex Agent Runbook

This file is for a future Codex agent picking up the hackathon demo quickly.

## Project In One Sentence

MerchantOS is an automated computer-use telemetry lab for merchants: it runs CUA simulations against a storefront, captures screenshots/DOM/actions/verifications, and produces an agentic-commerce readiness dashboard with MCP recommendations.

## Current Product Direction

Do not frame this as a customer shopping assistant.

Frame it as:

```text
Kernel browser
  + Tzafon Northstar computer-use model
  + MerchantOS telemetry harness
  + optional DeepAgents/Gemma harness brain
```

The merchant value is:

- simulate how AI buying agents experience the site
- detect loops, no-op clicks, blocked unsafe actions, and missing structured affordances
- produce MCP/tool recommendations such as `catalog.search`, `product://{id}`, and `cart.prepare`
- help merchants optimize for agentic commerce while keeping the relationship merchant-owned

## Important Files

- `README.md`: public project overview and high-level run modes.
- `spec.md`: product vision, architecture, mockable layers, and hackathon positioning.
- `architecture.html`: presentation-style architecture diagram.
- `LOCAL_KERNEL.md`: Kernel local SSH reverse-tunnel instructions.
- `backend/app/config.py`: runtime settings and env validation.
- `backend/app/browser/kernel_driver.py`: Kernel browser API/controls adapter.
- `backend/app/browser/kernel_runner.py`: Kernel-backed simulation runner.
- `backend/app/computer/tzafon_computer.py`: Tzafon computer-use provider adapter.
- `backend/app/services/guide_service.py`: core autonomous loop.
- `frontend/src/pages/MerchantHomePage.tsx`: main dashboard UI.
- `frontend/src/styles.css`: main visual system.

## Safety Rules

- Never print API keys.
- Never commit `.env`.
- If a command transmits `KERNEL_API_KEY`, `TZAFON_API_KEY`, or `OPENAI_API_KEY` to an external service, get explicit user approval in the chat first.
- `.env.example` may contain hackathon credentials from prior commits. Treat them as sensitive anyway and redact in all output.
- Do not revert unrelated user changes. There may be active UI work in progress.

## Environment Modes

### 1. Zero-Key Local Demo

Use this when you need a deterministic demo that always works.

```bash
AGENTREADY_BROWSER_ENV=local_sdk \
AGENTREADY_HARNESS_MODE=scripted \
AGENTREADY_COMPUTER_CLIENT=scripted \
BACKEND_BASE_URL=http://127.0.0.1:8014 \
FRONTEND_BASE_URL=http://127.0.0.1:5180 \
uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port 8014
```

In another terminal:

```bash
VITE_BACKEND_BASE_URL=http://127.0.0.1:8014 \
npm run dev --prefix frontend -- --host 127.0.0.1 --port 5180
```

Open:

```text
http://127.0.0.1:5180/
```

Expected result:

- dashboard auto-starts a simulation
- readiness score reaches around `91`
- cart gets `StormRunner GTX · 10.5 Wide`
- trace and MCP readiness sections populate

### 2. Tzafon Provider, Local Browser

Use this when demoing the Tzafon computer-use provider slot without Kernel.

```bash
AGENTREADY_BROWSER_ENV=local_sdk \
AGENTREADY_HARNESS_MODE=scripted \
AGENTREADY_COMPUTER_CLIENT=tzafon \
BACKEND_BASE_URL=http://127.0.0.1:8014 \
FRONTEND_BASE_URL=http://127.0.0.1:5180 \
uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port 8014
```

Requires:

```text
TZAFON_API_KEY
TZAFON_COMPUTER_MODEL=tzafon.northstar-cua-fast-1.6
```

If the UI shows `401 Unauthorized`, the adapter is wired but the key/model access is rejected by Tzafon.

### 3. Kernel Browser Mode

Kernel mode is the hackathon-native path, but it requires more setup.

Install tools if missing:

```bash
npm install -g @onkernel/cli
brew install websocat
```

Create a Kernel browser:

```bash
kernel browsers create --timeout 600 --output json
```

Keep reverse tunnels open in separate terminals:

```bash
kernel browsers ssh <session_id> -R 5173:localhost:5173
kernel browsers ssh <session_id> -R 8000:localhost:8000
```

Then run the app using:

```bash
AGENTREADY_BROWSER_ENV=kernel \
AGENTREADY_KERNEL_LOCAL_STOREFRONT_URL=http://localhost:5173 \
AGENTREADY_HARNESS_MODE=scripted \
AGENTREADY_COMPUTER_CLIENT=tzafon \
BACKEND_BASE_URL=http://localhost:8000 \
FRONTEND_BASE_URL=http://localhost:5173 \
uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
VITE_BACKEND_BASE_URL=http://localhost:8000 \
npm run dev --prefix frontend -- --host 127.0.0.1 --port 5173
```

Open the Kernel live view and visit:

```text
http://localhost:5173/
```

Required env:

```text
KERNEL_API_KEY
TZAFON_API_KEY
AGENTREADY_BROWSER_ENV=kernel
AGENTREADY_KERNEL_LOCAL_STOREFRONT_URL=http://localhost:5173
```

Note: Kernel cloud browsers cannot directly access your laptop's `127.0.0.1`; the SSH reverse tunnel makes the VM's `localhost:5173` point to your local Vite server.

## DeepAgents/Gemma Harness Brain

The harness brain is separate from computer use.

```text
DeepAgents/Gemma = chooses merchant objective and telemetry interpretation
Tzafon/OpenAI/scripted = proposes visual computer-use actions
Kernel/local SDK = executes approved browser actions
MerchantOS = validates, records, scores, and recommends
```

Use scripted harness for reliable demo:

```bash
AGENTREADY_HARNESS_MODE=scripted
```

Use Gemma through llama.cpp if the local model server is running:

```bash
brew install llama.cpp
npm run model:gemma4
```

Then:

```bash
AGENTREADY_HARNESS_MODE=deepagents
AGENTREADY_HARNESS_MODEL_PROVIDER=llamacpp
AGENTREADY_HARNESS_MODEL=gemma4-e4b-it
AGENTREADY_LLAMACPP_BASE_URL=http://127.0.0.1:8080/v1
```

## Tests

Run backend:

```bash
uv run --project backend --extra test pytest backend/tests
```

Run frontend:

```bash
npm run test --prefix frontend
npm run build --prefix frontend
```

Run local e2e:

```bash
npm run test:e2e
```

## Current Known Gotchas

- The Kernel CLI may not be installed by default.
- Kernel SSH tunnel requires `websocat`.
- Browser ports must be allowed by both CORS and `MerchantPolicy`.
- Local deterministic demo works best on backend `8014` and frontend `5180`.
- If the backend uses in-memory store and restarts, old simulation IDs in the frontend will 404; reload or rerun the simulation.
- Do not claim a run used Kernel unless the runtime banner says `Browser: kernel`.

## Pitch Shortcut

Use this when explaining the project:

> MerchantOS is a synthetic computer-use lab for agentic commerce. It automatically runs AI buying-agent simulations against a merchant site, records every screen state, action, verification, and failure, then tells the merchant how to make the site agent-ready through better UI affordances, structured data, and MCP tools.
