import type {
  AgentIntentRequest,
  AgentIntentResponse,
  GuideStartResponse,
  McpReadinessResponse,
  RuntimeResponse,
  SessionResponse,
  SimulationCreateRequest,
  SimulationListResponse,
  SimulationRun,
  SimulationTelemetryResponse,
  TelemetrySummaryAllResponse,
  TelemetrySummaryRequest,
  TelemetrySummaryResponse,
  TraceResponse
} from "./types";

const fallbackBaseUrl = "http://localhost:8000";

export function backendBaseUrl(): string {
  return import.meta.env.VITE_BACKEND_BASE_URL ?? fallbackBaseUrl;
}

export async function createAgentIntent(request: AgentIntentRequest): Promise<AgentIntentResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/agent-intent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error("Failed to create agent intent");
  }
  return (await response.json()) as AgentIntentResponse;
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error("Failed to load session");
  }
  return (await response.json()) as SessionResponse;
}

export async function getRuntime(): Promise<RuntimeResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/runtime`);
  if (!response.ok) {
    throw new Error("Failed to load runtime mode");
  }
  return (await response.json()) as RuntimeResponse;
}

export async function createSimulation(request: SimulationCreateRequest): Promise<SimulationRun> {
  const response = await fetch(`${backendBaseUrl()}/api/simulations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error("Failed to create simulation");
  }
  return (await response.json()) as SimulationRun;
}

export async function listSimulations(): Promise<SimulationListResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/simulations`);
  if (!response.ok) {
    throw new Error("Failed to load simulations");
  }
  return (await response.json()) as SimulationListResponse;
}

export async function getSimulation(simulationId: string): Promise<SimulationRun> {
  const response = await fetch(`${backendBaseUrl()}/api/simulations/${simulationId}`);
  if (!response.ok) {
    throw new Error("Failed to load simulation");
  }
  return (await response.json()) as SimulationRun;
}

export async function getSimulationTrace(simulationId: string): Promise<TraceResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/simulations/${simulationId}/trace`);
  if (!response.ok) {
    throw new Error("Failed to load simulation trace");
  }
  return (await response.json()) as TraceResponse;
}

export async function getSimulationTelemetry(simulationId: string): Promise<SimulationTelemetryResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/simulations/${simulationId}/telemetry`);
  if (!response.ok) {
    throw new Error("Failed to load simulation telemetry");
  }
  return (await response.json()) as SimulationTelemetryResponse;
}

export async function getMcpReadiness(simulationId: string): Promise<McpReadinessResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/simulations/${simulationId}/mcp-readiness`);
  if (!response.ok) {
    throw new Error("Failed to load MCP readiness");
  }
  return (await response.json()) as McpReadinessResponse;
}

export async function postCustomerMessage(sessionId: string, message: string): Promise<GuideStartResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  if (!response.ok) {
    throw new Error("Failed to start guided shopping");
  }
  return (await response.json()) as GuideStartResponse;
}

export async function getTrace(sessionId: string): Promise<TraceResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/sessions/${sessionId}/trace`);
  if (!response.ok) {
    throw new Error("Failed to load trace");
  }
  return (await response.json()) as TraceResponse;
}

export async function summarizeTelemetry(request: TelemetrySummaryRequest): Promise<TelemetrySummaryResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error("Failed to summarize telemetry");
  }
  return (await response.json()) as TelemetrySummaryResponse;
}

export async function summarizeAllTelemetry(): Promise<TelemetrySummaryAllResponse> {
  const response = await fetch(`${backendBaseUrl()}/api/summarize-all`, {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  });
  if (!response.ok) {
    throw new Error("Failed to summarize all telemetry");
  }
  return (await response.json()) as TelemetrySummaryAllResponse;
}
