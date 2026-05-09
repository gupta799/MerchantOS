# MerchantOS Spec

## One-Liner

MerchantOS is an automated computer-use telemetry lab that runs CUA agents against merchant storefronts, records every observation/action/state transition, and tells merchants how to make their sites agent-ready and MCP-ready.

## Product Vision

Agentic commerce creates a new merchant problem: agents may browse, compare, and purchase without giving merchants visibility into where their sites help or break the agent journey. MerchantOS gives merchants a controlled simulation environment where computer-use agents behave like buyers, while the merchant collects first-party telemetry about failures, missing affordances, structured-data gaps, and MCP/tool opportunities.

The product is not primarily a customer shopping assistant. It is infrastructure for merchants:

- Run automated computer-use simulations.
- Capture screenshots, DOM summaries, actions, verification, and browser results.
- Detect loops, no-op clicks, unsafe actions, and missing agent-readable affordances.
- Produce readiness metrics and MCP recommendations.
- Let merchants move repeated successful flows from visual automation toward structured tools.

## Hackathon Positioning

Best final product path:

```text
Kernel browser
  + Tzafon Northstar computer-use action model
  + MerchantOS telemetry harness
```

DeepAgents still fits. It is the harness brain, not the visual action model:

```text
Harness brain: DeepAgents + Gemma/OpenAI/scripted mock
Computer-use provider: Tzafon/OpenAI/scripted mock
Browser environment: Kernel cloud browser/local SDK mock
Telemetry layer: MerchantOS
```

This makes the project strong for a computer-use hackathon because the core contribution is not another shopping agent. The contribution is the reliability and telemetry layer around computer-use agents.

## Core Architecture

```text
MerchantOS Dashboard
  -> POST /api/simulations
  -> SimulationService creates run + merchant session
  -> GuideService runs autonomous simulation loop
    -> Harness brain creates visual commerce task
    -> Browser environment captures observation
    -> Computer-use provider proposes action
    -> Merchant policy validates action
    -> Browser environment executes action
    -> TraceService records observation/action/verification
  -> Telemetry + MCP readiness endpoints feed dashboard
```

### Layer 1: Harness Brain

The harness brain decides the merchant simulation objective and narrows it into a visual task for the computer-use provider.

Responsibilities:

- Read merchant session/catalog/cart context.
- Choose the product and variant to test.
- Produce a narrow visual goal.
- Generate merchant-facing assistant/status copy.
- Define what success means for the simulation.

Implementations:

- `deepagents`: Real DeepAgents graph using configured chat model.
- `scripted`: Deterministic mock harness for tests and demos.

Important: the harness model can be mocked. Not everyone can run Gemma locally, and not every judge/reviewer will have a paid model key. The system must still run end-to-end with:

```bash
AGENTREADY_HARNESS_MODE=scripted
```

Real local model option:

```bash
AGENTREADY_HARNESS_MODE=deepagents
AGENTREADY_HARNESS_MODEL_PROVIDER=llamacpp
AGENTREADY_HARNESS_MODEL=gemma4-e4b-it
AGENTREADY_LLAMACPP_BASE_URL=http://127.0.0.1:8080/v1
```

### Layer 2: Computer-Use Provider

The computer-use provider proposes visual actions from an observation and goal.

Responsibilities:

- Accept screenshot/DOM/goal context.
- Return click/type/scroll/wait style actions.
- Continue until task completion or failure.

Implementations:

- `tzafon`: Tzafon Northstar CUA provider.
- `openai`: OpenAI computer-use provider.
- `scripted`: Deterministic provider for local demos and CI.

Mock mode:

```bash
AGENTREADY_COMPUTER_CLIENT=scripted
```

Tzafon mode:

```bash
AGENTREADY_COMPUTER_CLIENT=tzafon
TZAFON_API_KEY=...
TZAFON_COMPUTER_MODEL=tzafon.northstar-cua-fast-1.6
```

Current note: the integration is active when the runtime banner says `Computer use: tzafon`. If Tzafon returns `401 Unauthorized`, the wiring is working but the key/model access is rejected by Tzafon.

### Layer 3: Browser Environment

The browser environment captures observations and executes approved actions.

Responsibilities:

- Load the merchant storefront test session.
- Capture screenshot and DOM summary.
- Execute approved actions.
- Return new state after action.
- Provide live-view or replayable traces where possible.

Implementations:

- `local_sdk`: React browser SDK + WebSocket, best for local demo.
- `kernel`: Kernel cloud browser + computer controls, best for hackathon-native stack.

Local mode:

```bash
AGENTREADY_BROWSER_ENV=local_sdk
```

Kernel mode:

```bash
AGENTREADY_BROWSER_ENV=kernel
KERNEL_API_KEY=...
AGENTREADY_KERNEL_LOCAL_STOREFRONT_URL=http://localhost:5173
```

Local Kernel mode uses SSH reverse tunnels from `LOCAL_KERNEL.md`, so the Kernel browser VM can open `http://localhost:5173` and reach the local backend at `http://localhost:8000`. Public URL mode is still supported with `AGENTREADY_PUBLIC_STOREFRONT_URL=https://public-frontend.example`.

### Layer 4: MerchantOS Telemetry

MerchantOS records every run and turns it into merchant-facing readiness data.

Collected trace data:

- Screenshot before/after.
- Browser URL.
- Viewport.
- DOM action summary.
- Proposed action.
- Policy verification result.
- Browser execution result.
- Cart and variant state.

Computed metrics:

- Task completion rate.
- Action success rate.
- No-op click count.
- Loop count.
- Blocked unsafe action count.
- Missing structured affordance count.
- Actions to completion.
- DOM action coverage.
- Screenshot/state confidence.

Readiness output:

- Readiness score.
- Failure labels.
- Recommendations.
- MCP readiness suggestions.

## Current Demo Storefront

The controlled mock merchant is RidgeRun, a Shopify-esque trail-running storefront.

Default simulation objective:

```text
Behave like a computer-use buying agent. Find a waterproof trail running shoe under $150,
identify the 10.5 Wide variant, add it to cart, verify the shipping promise, look for
return-policy signals, and stop before checkout or payment.
```

The storefront exposes `data-agent-*` attributes so the harness can measure whether the merchant is providing agent-readable affordances.

## Public APIs

### Simulation

```http
POST /api/simulations
GET /api/simulations/{id}
GET /api/simulations/{id}/trace
GET /api/simulations/{id}/telemetry
GET /api/simulations/{id}/mcp-readiness
```

### Session

```http
GET /api/sessions/{id}
POST /api/sessions/{id}/events
POST /api/sessions/{id}/messages
GET /api/sessions/{id}/trace
```

### Runtime

```http
GET /api/runtime
```

Returns the active provider configuration:

```json
{
  "harness_mode": "scripted",
  "harness_model_provider": "llamacpp",
  "harness_model": "gemma4-e4b-it",
  "computer_client_mode": "tzafon",
  "computer_model": "tzafon.northstar-cua-fast-1.6",
  "browser_environment": "local_sdk",
  "demo_mode": true
}
```

## Recommended Run Modes

### Zero-Key Demo

Best for reviewers who just want to see the product work.

```bash
AGENTREADY_HARNESS_MODE=scripted
AGENTREADY_COMPUTER_CLIENT=scripted
AGENTREADY_BROWSER_ENV=local_sdk
```

This mocks both the harness model and the computer-use model. It still exercises the browser SDK, WebSocket loop, trace recording, telemetry, and MCP readiness.

### Gemma Harness Demo

Best for showing DeepAgents/Gemma as the harness brain.

```bash
AGENTREADY_HARNESS_MODE=deepagents
AGENTREADY_HARNESS_MODEL_PROVIDER=llamacpp
AGENTREADY_HARNESS_MODEL=gemma4-e4b-it
AGENTREADY_LLAMACPP_BASE_URL=http://127.0.0.1:8080/v1
AGENTREADY_COMPUTER_CLIENT=scripted
AGENTREADY_BROWSER_ENV=local_sdk
```

This uses a real harness model but mocked computer-use actions.

### Tzafon Computer-Use Demo

Best for showing the actual CUA model provider slot.

```bash
AGENTREADY_HARNESS_MODE=scripted
AGENTREADY_COMPUTER_CLIENT=tzafon
TZAFON_API_KEY=...
TZAFON_COMPUTER_MODEL=tzafon.northstar-cua-fast-1.6
AGENTREADY_BROWSER_ENV=local_sdk
```

This uses a mocked harness brain and real Tzafon provider.

### Full Hackathon Stack

Best final target.

```bash
AGENTREADY_HARNESS_MODE=deepagents
AGENTREADY_HARNESS_MODEL_PROVIDER=llamacpp
AGENTREADY_HARNESS_MODEL=gemma4-e4b-it
AGENTREADY_COMPUTER_CLIENT=tzafon
TZAFON_API_KEY=...
AGENTREADY_BROWSER_ENV=kernel
KERNEL_API_KEY=...
AGENTREADY_KERNEL_LOCAL_STOREFRONT_URL=http://localhost:5173
```

This uses DeepAgents/Gemma, Tzafon, Kernel, and MerchantOS telemetry together.

## What Is Mocked And Why

Mocks are a feature, not a shortcut. The product is a harness, so provider swaps are part of the design.

Mockable layers:

- Harness brain: `scripted` instead of DeepAgents/Gemma.
- Computer-use provider: `scripted` instead of Tzafon/OpenAI.
- Browser environment: `local_sdk` instead of Kernel cloud browser.

Why:

- Reviewers may not have local Gemma running.
- Tzafon credentials may not be available or may fail.
- Kernel local mode requires SSH reverse tunnels; public URL mode remains available for deployed demos.
- CI should be deterministic and cheap.
- The core product value is telemetry, verification, replay, and readiness scoring across providers.

## Evaluation Story

MerchantOS can compare runs across:

- Different harness brains.
- Different CUA models.
- Different storefront versions.
- Different browser environments.

Example claims the product should eventually support:

- "After adding `data-agent-*` affordances, action success improved from 62% to 94%."
- "The agent looped on size selection before structured variant metadata was added."
- "Checkout was correctly blocked by merchant policy."
- "This storefront is ready for `catalog.search`, `product://{id}`, and `cart.prepare` MCP surfaces."

## MCP Readiness

MerchantOS does not need to ship a full MCP server in v1. It recommends concrete tools/resources based on telemetry.

Initial recommendations:

- `catalog.search`: product discovery tool.
- `product://{product_id}`: stable resource for product facts, variants, delivery promises, and policy links.
- `cart.prepare`: add selected variants to a prepared cart while keeping checkout human-controlled.

## Safety Model

Merchant policy validates every proposed action before execution.

Blocked actions include:

- Payment and checkout completion.
- Credential or card entry.
- Offsite navigation.
- Actions outside the allowed merchant viewport/origin.

The current demo intentionally stops before checkout or payment.

## Presentation Narrative

Suggested pitch:

```text
Computer-use agents are powerful, but merchants cannot improve what they cannot observe.
MerchantOS runs automated CUA simulations against merchant storefronts, captures every
screen/action/state transition, and produces telemetry that tells merchants how to make
their sites agent-ready and MCP-ready.
```

Differentiator:

```text
We are not building another shopping agent. We are building the harness that lets merchants
measure, debug, and improve how any computer-use agent experiences their site.
```

## Near-Term Next Steps

- Add a public tunnel/deploy script for Kernel mode.
- Add persistent storage for simulation runs.
- Add a proper replay viewer with screenshot before/after diffs.
- Add failure classifiers for loops/no-op clicks/wrong-page/premature-submit.
- Add comparison view across provider/model/site versions.
- Add optional export of MCP schemas from telemetry.
