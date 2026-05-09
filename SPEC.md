# Computer Use Merchant SDK - Specification Sheet

## Overview

The Computer Use Merchant SDK enables merchants to safely integrate browser-use AI agents into their purchasing flow while retaining ownership of the customer experience, UI, policies, and automation boundaries.

Instead of exposing unrestricted MCP servers directly to third-party agent providers, merchants expose a controlled `/cua` interface that accepts structured user intent from external AI harnesses such as assistants, autonomous shopping agents, and enterprise copilots. The merchant then executes the interaction internally using a browser automation runtime running inside KERNEL.

The SDK provides:

- Controlled browser automation execution
- Rich telemetry collection from browser interactions
- Merchant-defined policy enforcement
- Real-time action streaming back to the harness
- Automatic synthesis of reusable MCP tools from observed workflows

The system bridges:

- Natural language intent
- Browser-native execution
- Structured automation generation

## Problem Statement

Current autonomous browser purchasing systems create several issues for merchants:

- Loss of control over checkout UX
- Inability to enforce branding or compliance requirements
- Limited visibility into agent behavior
- High risk of brittle third-party automation
- Lack of reusable structured APIs for future automation

Merchants are hesitant to expose full MCP servers because:

- MCP schemas are rigid upfront investments
- Flows evolve rapidly
- Direct tool exposure reduces control over customer interaction
- Security and fraud surfaces increase

The Computer Use Merchant SDK solves this by allowing merchants to:

- Own execution infrastructure
- Observe agent behavior
- Learn from interactions
- Gradually transition repeated flows into structured MCP tools

## Core Architecture

### Components

1. Harness

   External AI system responsible for:

   - User interaction
   - Intent extraction
   - Session orchestration

   Examples:

   - ChatGPT
   - Claude
   - Enterprise copilots
   - Shopping assistants

   The harness does not directly control the merchant website.

2. Merchant `/cua` Endpoint

   Merchant-controlled API endpoint receiving structured intents.

   Example:

   ```http
   POST /cua
   ```

   Responsibilities:

   - Authenticate harness
   - Validate permissions
   - Launch execution session
   - Apply merchant policies
   - Stream execution telemetry

3. KERNEL Browser Runtime

   Isolated browser execution environment.

   Responsibilities:

   - Launch browser instances
   - Execute computer-use agent
   - Collect telemetry
   - Capture DOM interaction graphs
   - Enforce runtime constraints

   Execution occurs entirely under merchant control.

4. Computer Use SDK

   Embedded SDK integrated into the merchant browser runtime.

   Capabilities:

   - Action instrumentation
   - DOM snapshotting
   - Event tracing
   - Semantic labeling
   - Checkout state modeling
   - Fraud/risk hooks
   - Human escalation

5. Telemetry and Workflow Compiler

   Observes browser interactions and converts repeated workflows into structured automation primitives.

   Outputs:

   - Candidate MCP tool definitions
   - Structured APIs
   - Workflow templates
   - Intent-to-action mappings

## High-Level Flow

```text
User
  -> AI Harness
  -> Merchant /cua Endpoint
  -> KERNEL Browser Runtime
  -> Computer Use Agent
  -> Merchant Website
  -> Telemetry + Action Stream
  -> Harness + Workflow Compiler
```

## Example Request Flow

### Step 1 - User Intent

User says:

> Buy me size 10 black running shoes under $150.

### Step 2 - Harness Distills Intent

```json
{
  "intent": "purchase_product",
  "constraints": {
    "category": "running shoes",
    "color": "black",
    "size": 10,
    "max_price": 150
  }
}
```

### Step 3 - Merchant `/cua` Request

```http
POST /cua/session
```

```json
{
  "session_id": "sess_123",
  "intent": {...},
  "capabilities": [
    "browse_products",
    "checkout"
  ]
}
```

### Step 4 - Merchant Executes Browser Agent

Merchant launches:

- Sandboxed browser
- Merchant-controlled prompts
- Merchant policies
- Fraud/risk enforcement

### Step 5 - Telemetry Stream

```json
{
  "event": "click",
  "target": "add_to_cart_button",
  "confidence": 0.98,
  "page": "/product/abc"
}
```

### Step 6 - Workflow Compilation

Observed sequence:

```text
search -> filter -> select_size -> add_to_cart -> checkout
```

Converted into:

```json
{
  "tool_name": "purchase_running_shoes",
  "inputs": {...}
}
```

Potential future MCP endpoint generated automatically.

## Key Features

### Merchant-Controlled Execution

Merchants retain:

- UI ownership
- Checkout logic
- Compliance enforcement
- Payment flows
- Experimentation frameworks

### Rich Browser Telemetry

Collected data includes:

- DOM structure
- Click paths
- Form interactions
- Navigation graphs
- Visual state transitions
- Timing metadata
- Agent reasoning traces
- Success/failure outcomes

### Policy Engine

Supports:

- Allowed action lists
- Restricted pages
- Spending limits
- Human approval gates
- CAPTCHA escalation
- Compliance requirements

### Progressive MCP Generation

The system learns repeated workflows and automatically proposes:

- MCP tools
- Structured APIs
- Parameter schemas
- Action abstractions

This enables gradual migration from:

- Browser automation
- Structured programmable interfaces

### Feedback Streaming

Real-time updates sent back to harness:

```json
{
  "status": "awaiting_confirmation",
  "cart_total": 127.99
}
```

Enables:

- Human-in-the-loop review
- Conversational transparency
- Recovery handling

## Security Model

### Isolation

Each session executes in:

- Ephemeral containers
- Isolated browser runtimes
- Sandboxed network environments

### Permissioning

Harnesses receive scoped permissions:

- Browsing only
- Add-to-cart
- Checkout
- Refund initiation
- Order tracking

### Auditability

All actions are logged:

- Browser actions
- Network requests
- Tool invocations
- Session state transitions

### Fraud Prevention

Supports:

- Velocity checks
- Behavioral anomaly detection
- Risk scoring
- Manual review triggers

## MCP Evolution Strategy

### Phase 1 - Browser Automation

- No structured APIs required.
- Merchant only integrates SDK.

### Phase 2 - Workflow Observation

System learns:

- Common tasks
- Stable UI patterns
- Frequent intents

### Phase 3 - Tool Synthesis

Automatic MCP proposals generated:

```json
{
  "name": "reorder_last_purchase",
  "schema": {...}
}
```

### Phase 4 - Structured Automation

High-confidence flows transition from:

- Visual automation
- Deterministic APIs

Reducing:

- Latency
- Cost
- Failure rates

## SDK Interfaces

### `/cua/session`

Starts execution session.

Request:

```json
{
  "intent": {},
  "user_context": {},
  "capabilities": []
}
```

Response:

```json
{
  "session_id": "sess_abc",
  "stream_url": "...",
  "status": "running"
}
```

### Telemetry Stream

WebSocket or SSE stream.

Example:

```json
{
  "timestamp": 123456789,
  "action": "navigate",
  "url": "/checkout"
}
```

### Workflow Export API

```http
GET /cua/workflows
```

Returns:

- Candidate MCP tools
- Workflow statistics
- Automation confidence scores

## Intended Use Cases

- Commerce
  - Purchasing
  - Checkout
  - Reordering
  - Subscription management
- Travel
  - Booking
  - Seat selection
  - Modifications
- Enterprise SaaS
  - Internal tooling automation
  - Procurement flows
  - CRM workflows
- Financial Services
  - Controlled onboarding
  - Document workflows
  - Approval chains

## Design Principles

- Merchant Ownership
  - The merchant always controls execution.
- Progressive Structuring
  - Browser automation becomes APIs over time.
- Observability First
  - Telemetry is foundational.
- Human-Compatible
  - Supports human review and intervention.
- Harness Agnostic
  - Compatible with any external orchestration layer.

## Future Extensions

- Multi-agent cooperative workflows
- Cross-merchant workflow composition
- Shared workflow embeddings
- Federated workflow learning
- Deterministic replay
- Self-healing automation
- Fine-grained economic routing between browser-use and MCP execution

## Summary

The Computer Use Merchant SDK provides a controlled bridge between conversational AI systems, browser-native execution, and future structured automation.

It allows merchants to:

- Preserve UX ownership
- Safely enable autonomous purchasing
- Collect actionable telemetry
- Evolve naturally toward MCP-native interfaces without requiring upfront API design
Computer Use Merchant SDK — Specification Sheet
Overview
The Computer Use Merchant SDK enables merchants to safely integrate browser-use AI agents into their purchasing flow while retaining ownership of the customer experience, UI, policies, and automation boundaries.
Instead of exposing unrestricted MCP servers directly to third-party agent providers, merchants expose a controlled /cua interface that accepts structured user intent from external AI harnesses (e.g. assistants, autonomous shopping agents, enterprise copilots). The merchant then executes the interaction internally using a browser automation runtime running inside KERNEL.
The SDK provides:
Controlled browser automation execution
Rich telemetry collection from browser interactions
Merchant-defined policy enforcement
Real-time action streaming back to the harness
Automatic synthesis of reusable MCP tools from observed workflows
The system bridges:
Natural language intent
Browser-native execution
Structured automation generation

Problem Statement
Current autonomous browser purchasing systems create several issues for merchants:
Loss of control over checkout UX
Inability to enforce branding or compliance requirements
Limited visibility into agent behavior
High risk of brittle third-party automation
Lack of reusable structured APIs for future automation
Merchants are hesitant to expose full MCP servers because:
MCP schemas are rigid upfront investments
Flows evolve rapidly
Direct tool exposure reduces control over customer interaction
Security and fraud surfaces increase
The Computer Use Merchant SDK solves this by allowing merchants to:
Own execution infrastructure
Observe agent behavior
Learn from interactions
Gradually transition repeated flows into structured MCP tools

Core Architecture
Components
1. Harness
External AI system responsible for:
User interaction
Intent extraction
Session orchestration
Examples:
ChatGPT
Claude
Enterprise copilots
Shopping assistants
The harness does not directly control the merchant website.

2. Merchant /cua Endpoint
Merchant-controlled API endpoint receiving structured intents.
Example:
POST /cua

Responsibilities:
Authenticate harness
Validate permissions
Launch execution session
Apply merchant policies
Stream execution telemetry

3. KERNEL Browser Runtime
Isolated browser execution environment.
Responsibilities:
Launch browser instances
Execute computer-use agent
Collect telemetry
Capture DOM interaction graphs
Enforce runtime constraints
Execution occurs entirely under merchant control.

4. Computer Use SDK
Embedded SDK integrated into the merchant browser runtime.
Capabilities:
Action instrumentation
DOM snapshotting
Event tracing
Semantic labeling
Checkout state modeling
Fraud/risk hooks
Human escalation

5. Telemetry & Workflow Compiler
Observes browser interactions and converts repeated workflows into structured automation primitives.
Outputs:
Candidate MCP tool definitions
Structured APIs
Workflow templates
Intent → action mappings

High-Level Flow
User
  ↓
AI Harness
  ↓
Merchant /cua Endpoint
  ↓
KERNEL Browser Runtime
  ↓
Computer Use Agent
  ↓
Merchant Website
  ↓
Telemetry + Action Stream
  ↓
Harness + Workflow Compiler


Example Request Flow
Step 1 — User Intent
User says:
“Buy me size 10 black running shoes under $150.”

Step 2 — Harness Distills Intent
{
  "intent": "purchase_product",
  "constraints": {
    "category": "running shoes",
    "color": "black",
    "size": 10,
    "max_price": 150
  }
}


Step 3 — Merchant /cua Request
POST /cua/session

{
  "session_id": "sess_123",
  "intent": {...},
  "capabilities": [
    "browse_products",
    "checkout"
  ]
}


Step 4 — Merchant Executes Browser Agent
Merchant launches:
Sandboxed browser
Merchant-controlled prompts
Merchant policies
Fraud/risk enforcement

Step 5 — Telemetry Stream
{
  "event": "click",
  "target": "add_to_cart_button",
  "confidence": 0.98,
  "page": "/product/abc"
}


Step 6 — Workflow Compilation
Observed sequence:
search → filter → select_size → add_to_cart → checkout

Converted into:
{
  "tool_name": "purchase_running_shoes",
  "inputs": {...}
}

Potential future MCP endpoint generated automatically.

Key Features
Merchant-Controlled Execution
Merchants retain:
UI ownership
Checkout logic
Compliance enforcement
Payment flows
Experimentation frameworks

Rich Browser Telemetry
Collected data includes:
DOM structure
Click paths
Form interactions
Navigation graphs
Visual state transitions
Timing metadata
Agent reasoning traces
Success/failure outcomes

Policy Engine
Supports:
Allowed action lists
Restricted pages
Spending limits
Human approval gates
CAPTCHA escalation
Compliance requirements

Progressive MCP Generation
The system learns repeated workflows and automatically proposes:
MCP tools
Structured APIs
Parameter schemas
Action abstractions
This enables gradual migration from:
Browser automation
→ structured programmable interfaces

Feedback Streaming
Real-time updates sent back to harness:
{
  "status": "awaiting_confirmation",
  "cart_total": 127.99
}

Enables:
Human-in-the-loop review
Conversational transparency
Recovery handling

Security Model
Isolation
Each session executes in:
Ephemeral containers
Isolated browser runtimes
Sandboxed network environments

Permissioning
Harnesses receive scoped permissions:
Browsing only
Add-to-cart
Checkout
Refund initiation
Order tracking

Auditability
All actions are logged:
Browser actions
Network requests
Tool invocations
Session state transitions

Fraud Prevention
Supports:
Velocity checks
Behavioral anomaly detection
Risk scoring
Manual review triggers

MCP Evolution Strategy
Phase 1 — Browser Automation
No structured APIs required.
Merchant only integrates SDK.

Phase 2 — Workflow Observation
System learns:
Common tasks
Stable UI patterns
Frequent intents

Phase 3 — Tool Synthesis
Automatic MCP proposals generated:
{
  "name": "reorder_last_purchase",
  "schema": {...}
}


Phase 4 — Structured Automation
High-confidence flows transition from:
Visual automation
→ deterministic APIs
Reducing:
Latency
Cost
Failure rates

SDK Interfaces
/cua/session
Starts execution session.
Request
{
  "intent": {},
  "user_context": {},
  "capabilities": []
}

Response
{
  "session_id": "sess_abc",
  "stream_url": "...",
  "status": "running"
}


Telemetry Stream
WebSocket or SSE stream.
Example:
{
  "timestamp": 123456789,
  "action": "navigate",
  "url": "/checkout"
}


Workflow Export API
GET /cua/workflows

Returns:
Candidate MCP tools
Workflow statistics
Automation confidence scores

Intended Use Cases
Commerce
Purchasing
Checkout
Reordering
Subscription management
Travel
Booking
Seat selection
Modifications
Enterprise SaaS
Internal tooling automation
Procurement flows
CRM workflows
Financial Services
Controlled onboarding
Document workflows
Approval chains

Design Principles
Merchant Ownership
The merchant always controls execution.

Progressive Structuring
Browser automation becomes APIs over time.

Observability First
Telemetry is foundational.

Human-Compatible
Supports human review and intervention.

Harness Agnostic
Compatible with any external orchestration layer.

Future Extensions
Multi-agent cooperative workflows
Cross-merchant workflow composition
Shared workflow embeddings
Federated workflow learning
Deterministic replay
Self-healing automation
Fine-grained economic routing between browser-use and MCP execution

Summary
The Computer Use Merchant SDK provides a controlled bridge between:
conversational AI systems,
browser-native execution,
and future structured automation.
It allows merchants to:
preserve UX ownership,
safely enable autonomous purchasing,
collect actionable telemetry,
and evolve naturally toward MCP-native interfaces without requiring upfront API design.

