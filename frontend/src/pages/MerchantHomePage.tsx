import type { ReactElement } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  createSimulation,
  getMcpReadiness,
  getRuntime,
  getSession,
  getSimulation,
  getSimulationTelemetry,
  getSimulationTrace,
  listSimulations,
  postCustomerMessage,
  summarizeAllTelemetry,
  summarizeTelemetry
} from "../api/http";
import type {
  Cart,
  McpReadinessResponse,
  Product,
  RuntimeResponse,
  SessionResponse,
  SimulationRun,
  SimulationTelemetryResponse,
  TelemetryMetric,
  TraceEntry
} from "../api/types";
import { CartDrawer } from "../components/CartDrawer";
import { ProductCard } from "../components/ProductCard";
import { TracePanel } from "../components/TracePanel";
import { AgentReadyClient } from "../sdk/AgentReadyClient";
import { emitMerchantEvent } from "../sdk/events";

const simulationRequest = {
  merchant_id: "demo_shop",
  scenario_id: "autonomous_commerce_readiness"
};

function addCartItem(cart: Cart, products: Product[], productId: string, variantId: string): Cart {
  const product = products.find((candidate) => candidate.id === productId);
  const variant = product?.variants.find((candidate) => candidate.id === variantId);
  if (product === undefined || variant === undefined) {
    return cart;
  }
  const exists = cart.items.some((item) => item.product_id === productId && item.variant_id === variantId);
  if (exists) {
    return cart;
  }
  const items = [
    ...cart.items,
    {
      product_id: product.id,
      variant_id: variant.id,
      name: product.name,
      variant_label: variant.label,
      price: product.price,
      quantity: 1
    }
  ];
  return {
    ...cart,
    items,
    subtotal: items.reduce((total, item) => total + item.price * item.quantity, 0)
  };
}

function metricText(metric: TelemetryMetric): string {
  if (metric.unit === "%") {
    return `${metric.value}%`;
  }
  if (metric.unit === "count") {
    return metric.value.toFixed(0);
  }
  return `${metric.value.toFixed(0)} ${metric.unit}`;
}

export function MerchantHomePage(): ReactElement {
  const testbedRef = useRef<HTMLDivElement | null>(null);
  const clientRef = useRef<AgentReadyClient | null>(null);
  const createdRef = useRef(false);
  const startedSessionRef = useRef("");
  const [simulation, setSimulation] = useState<SimulationRun | null>(null);
  const [simulationOptions, setSimulationOptions] = useState<SimulationRun[]>([]);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [runtime, setRuntime] = useState<RuntimeResponse | null>(null);
  const [cart, setCart] = useState<Cart | null>(null);
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const [traceEntries, setTraceEntries] = useState<TraceEntry[]>([]);
  const [telemetry, setTelemetry] = useState<SimulationTelemetryResponse | null>(null);
  const [mcpReadiness, setMcpReadiness] = useState<McpReadinessResponse | null>(null);
  const [statusMessage, setStatusMessage] = useState("Preparing automated computer-use simulation...");
  const [rerunning, setRerunning] = useState(false);
  const [analysisMarkdown, setAnalysisMarkdown] = useState("");
  const [analysisStatus, setAnalysisStatus] = useState<string | null>(null);
  const [analysisStreaming, setAnalysisStreaming] = useState(false);
  const [analysisTarget, setAnalysisTarget] = useState("current");
  const analysisTimerRef = useRef<number | null>(null);

  const featuredMetrics = useMemo(
    () =>
      (telemetry?.metrics ?? []).filter((metric) =>
        ["task_completion_rate", "action_success_rate", "loop_count", "dom_action_coverage"].includes(metric.key)
      ),
    [telemetry]
  );

  async function refreshSimulation(simulationId: string): Promise<void> {
    const [nextSimulation, nextTrace, nextTelemetry, nextMcp, nextList] = await Promise.all([
      getSimulation(simulationId),
      getSimulationTrace(simulationId),
      getSimulationTelemetry(simulationId),
      getMcpReadiness(simulationId),
      listSimulations().catch(() => ({ simulations: [] }))
    ]);
    setSimulation(nextSimulation);
    setTraceEntries(nextTrace.entries);
    setTelemetry(nextTelemetry);
    setMcpReadiness(nextMcp);
    setSimulationOptions(nextList.simulations);
    const nextSession = await getSession(nextSimulation.session_id);
    setSession(nextSession);
    setCart(nextSession.cart);
    setSelectedVariantId(nextSession.recommended_products[0]?.variant_id ?? null);
  }

  async function createAndRunSimulation(): Promise<void> {
    clientRef.current?.disconnect();
    clientRef.current = null;
    startedSessionRef.current = "";
    setRerunning(true);
    setTraceEntries([]);
    setTelemetry(null);
    setMcpReadiness(null);
    setStatusMessage("Creating automated CUA simulation run...");
    const nextSimulation = await createSimulation(simulationRequest);
    const [nextRuntime, nextSession, nextTelemetry, nextMcp, nextList] = await Promise.all([
      getRuntime().catch(() => null),
      getSession(nextSimulation.session_id),
      getSimulationTelemetry(nextSimulation.simulation_id),
      getMcpReadiness(nextSimulation.simulation_id),
      listSimulations().catch(() => ({ simulations: [] }))
    ]);
    setRuntime(nextRuntime);
    setSimulation(nextSimulation);
    setSession(nextSession);
    setCart(nextSession.cart);
    setTelemetry(nextTelemetry);
    setMcpReadiness(nextMcp);
    setSimulationOptions(nextList.simulations);
    setAnalysisTarget("current");
    setSelectedVariantId(nextSession.recommended_products[0]?.variant_id ?? null);
    const browserEnvironment = nextRuntime?.browser_environment ?? nextSimulation.browser_environment;
    setStatusMessage(
      browserEnvironment === "kernel"
        ? "Kernel cloud browser launched. Tzafon computer-use actions will stream into telemetry."
        : "Browser SDK connected. Autonomous agent run will start automatically."
    );
    setRerunning(false);
  }

  async function startAutonomousRun(sessionId: string, simulationId: string): Promise<void> {
    if (startedSessionRef.current === sessionId) {
      return;
    }
    startedSessionRef.current = sessionId;
    setStatusMessage("Autonomous CUA agent is observing the storefront and choosing actions...");
    await emitMerchantEvent(sessionId, {
      type: "simulation_opened",
      source: "merchant_sdk",
      message: "Merchant OS simulation environment opened"
    });
    await emitMerchantEvent(sessionId, {
      type: "simulation_started",
      source: "merchant_sdk",
      message: "Automated computer-use telemetry simulation started"
    });
    const guideStart = await postCustomerMessage(
      sessionId,
      "Run the autonomous commerce-readiness simulation and collect telemetry."
    );
    if (guideStart.status !== "running") {
      setStatusMessage(guideStart.message);
    }
    await refreshSimulation(simulationId);
  }

  useEffect(() => {
    if (createdRef.current) {
      return;
    }
    createdRef.current = true;
    void createAndRunSimulation();
  }, []);

  useEffect(() => {
    if (
      testbedRef.current === null ||
      session === null ||
      simulation === null ||
      clientRef.current !== null ||
      simulation.browser_environment === "kernel"
    ) {
      return;
    }
    const client = new AgentReadyClient(session.session_id, testbedRef.current, {
      onReady: () => void startAutonomousRun(session.session_id, simulation.simulation_id),
      onAssistantUpdate: setStatusMessage,
      onTraceUpdate: () => void refreshSimulation(simulation.simulation_id),
      onDone: (message) => {
        setStatusMessage(message);
        void refreshSimulation(simulation.simulation_id);
      },
      onError: setStatusMessage
    });
    client.connect();
    clientRef.current = client;
    return () => {
      client.disconnect();
      clientRef.current = null;
    };
  }, [session?.session_id, simulation?.simulation_id]);

  useEffect(() => {
    return () => {
      if (analysisTimerRef.current !== null) {
        window.clearInterval(analysisTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (simulation === null) {
      return;
    }
    if (simulation.status === "completed" || simulation.status === "failed") {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshSimulation(simulation.simulation_id);
    }, 1500);
    return () => window.clearInterval(timer);
  }, [simulation?.simulation_id, simulation?.status]);

  function selectVariant(variantId: string): void {
    setSelectedVariantId(variantId);
  }

  function addToCart(productId: string, variantId: string): void {
    if (cart === null || session === null) {
      return;
    }
    setCart(addCartItem(cart, session.products, productId, variantId));
  }

  function renderInlineMarkdown(text: string): ReactElement[] {
    const tokens = text.split(/(\*\*[^*]+\*\*)/g).filter((token) => token.length > 0);
    return tokens.map((token, index) => {
      if (token.startsWith("**") && token.endsWith("**")) {
        return <strong key={`strong-${index}`}>{token.slice(2, -2)}</strong>;
      }
      return <span key={`text-${index}`}>{token}</span>;
    });
  }

  function renderMarkdown(markdown: string): ReactElement {
    const lines = markdown.split("\n");
    const elements: ReactElement[] = [];
    let listItems: string[] = [];

    const flushList = (): void => {
      if (listItems.length === 0) {
        return;
      }
      elements.push(
        <ul key={`list-${elements.length}`}>
          {listItems.map((item, index) => (
            <li key={`item-${index}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>
      );
      listItems = [];
    };

    lines.forEach((line) => {
      if (line.startsWith("- ")) {
        listItems.push(line.slice(2));
        return;
      }
      flushList();
      if (line.startsWith("### ")) {
        elements.push(<h4 key={`h4-${elements.length}`}>{renderInlineMarkdown(line.slice(4))}</h4>);
        return;
      }
      if (line.startsWith("## ")) {
        elements.push(<h3 key={`h3-${elements.length}`}>{renderInlineMarkdown(line.slice(3))}</h3>);
        return;
      }
      if (line.startsWith("# ")) {
        elements.push(<h2 key={`h2-${elements.length}`}>{renderInlineMarkdown(line.slice(2))}</h2>);
        return;
      }
      if (line.trim() === "") {
        elements.push(<div className="analysis-spacer" key={`spacer-${elements.length}`} />);
        return;
      }
      elements.push(<p key={`p-${elements.length}`}>{renderInlineMarkdown(line)}</p>);
    });

    flushList();
    return <div className="analysis-output">{elements}</div>;
  }

  async function analyzeTelemetry(): Promise<void> {
    const targetId = analysisTarget === "current" ? simulation?.simulation_id : analysisTarget;
    if (!targetId) {
      return;
    }
    if (analysisTimerRef.current !== null) {
      window.clearInterval(analysisTimerRef.current);
    }
    setAnalysisMarkdown("");
    setAnalysisStatus("Analyzing telemetry with OpenAI summary mock...");
    setAnalysisStreaming(true);
    try {
      const summary = await summarizeTelemetry({ simulation_id: targetId });
      const lines = summary.markdown.split("\n");
      let index = 0;
      analysisTimerRef.current = window.setInterval(() => {
        setAnalysisMarkdown((previous) => {
          const nextLine = lines[index];
          const prefix = previous.length === 0 ? "" : "\n";
          return `${previous}${prefix}${nextLine}`;
        });
        index += 1;
        if (index >= lines.length) {
          if (analysisTimerRef.current !== null) {
            window.clearInterval(analysisTimerRef.current);
          }
          analysisTimerRef.current = null;
          setAnalysisStreaming(false);
          setAnalysisStatus(null);
        }
      }, 80);
    } catch (error) {
      setAnalysisStreaming(false);
      setAnalysisStatus("Telemetry analysis failed. Try rerunning the simulation.");
    }
  }

  async function analyzeAllTelemetry(): Promise<void> {
    if (analysisTimerRef.current !== null) {
      window.clearInterval(analysisTimerRef.current);
    }
    setAnalysisMarkdown("");
    setAnalysisStatus("Summarizing all simulations...");
    setAnalysisStreaming(true);
    try {
      const summary = await summarizeAllTelemetry();
      const lines = summary.markdown.split("\n");
      let index = 0;
      analysisTimerRef.current = window.setInterval(() => {
        setAnalysisMarkdown((previous) => {
          const nextLine = lines[index];
          const prefix = previous.length === 0 ? "" : "\n";
          return `${previous}${prefix}${nextLine}`;
        });
        index += 1;
        if (index >= lines.length) {
          if (analysisTimerRef.current !== null) {
            window.clearInterval(analysisTimerRef.current);
          }
          analysisTimerRef.current = null;
          setAnalysisStreaming(false);
          setAnalysisStatus(null);
        }
      }, 70);
    } catch (error) {
      setAnalysisStreaming(false);
      setAnalysisStatus("All-simulations summary failed. Try again.");
    }
  }

  return (
    <main className="home-page lab-page">
      <div className="announcement-bar">Merchant OS · Automated computer-use telemetry lab</div>
      <header className="shop-header">
        <a className="brand-mark" href="/" aria-label="Merchant OS home">
          <span>M</span>
          Merchant OS
        </a>
        <nav className="shop-nav" aria-label="Lab navigation">
          <a href="#telemetry">Telemetry</a>
          <a href="#testbed">Storefront</a>
          <a href="#mcp">MCP readiness</a>
        </nav>
        <button
          className="cart-link lab-rerun"
          type="button"
          onClick={() => void createAndRunSimulation()}
          disabled={rerunning}
        >
          {rerunning ? "Rerunning..." : "Rerun Simulation"}
        </button>
      </header>

      <section className="lab-hero">
        <div>
          <p className="eyebrow">AgentReady Lab</p>
          <h1>Automated computer-use telemetry for agent-ready commerce</h1>
          <p>
            Autonomous CUA agents simulate real browsing behavior, stream screenshots and DOM state,
            and turn every action into merchant-owned readiness analytics.
          </p>
        </div>
        <aside className="readiness-card">
          <span>Readiness score</span>
          <strong>{simulation?.report.readiness_score ?? 0}</strong>
          <p>{simulation?.report.summary ?? "Waiting for the first telemetry sample."}</p>
        </aside>
      </section>

      <section id="telemetry" className="lab-grid">
        <article className="lab-panel wide">
          <p className="eyebrow">Live autonomous run</p>
          <h2>{simulation?.scenario.title ?? "Starting simulation"}</h2>
          <p>{simulation?.current_goal ?? "Preparing scenario goal..."}</p>
          <div className="status-strip">
            <span>Status: {simulation?.status ?? "connecting"}</span>
            <span>{statusMessage}</span>
          </div>
          {runtime !== null ? (
            <div className="mode-banner live">
              <strong>Harness: {runtime.harness_mode}</strong>
              <span>
                Model: {runtime.harness_model_provider}/{runtime.harness_model} · Computer use:{" "}
                {runtime.computer_client_mode} · Browser: {runtime.browser_environment}
              </span>
              {simulation?.browser_live_view_url !== null && simulation?.browser_live_view_url !== undefined ? (
                <a href={simulation.browser_live_view_url} target="_blank" rel="noreferrer">
                  Open Kernel live view
                </a>
              ) : null}
            </div>
          ) : null}
        </article>

        <article className="lab-panel wide analysis-panel">
          <p className="eyebrow">Telemetry analysis</p>
          <div className="analysis-header">
            <h2>Agent-ready insights</h2>
            <div className="analysis-actions">
              <select
                className="analysis-select"
                value={analysisTarget}
                onChange={(event) => setAnalysisTarget(event.target.value)}
                disabled={analysisStreaming}
              >
                <option value="current">Current simulation</option>
                {simulationOptions.map((option) => (
                  <option key={option.simulation_id} value={option.simulation_id}>
                    {option.simulation_id} · {option.status}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="primary-action"
                onClick={() => void analyzeTelemetry()}
                disabled={analysisStreaming || (analysisTarget === "current" && simulation === null)}
              >
                {analysisStreaming ? "Analyzing..." : "Analyze telemetry"}
              </button>
              <button
                type="button"
                className="secondary-action"
                onClick={() => void analyzeAllTelemetry()}
                disabled={analysisStreaming}
              >
                Summarize all
              </button>
            </div>
          </div>
          {analysisStatus !== null ? <p className="analysis-status">{analysisStatus}</p> : null}
          {analysisMarkdown.length > 0 ? renderMarkdown(analysisMarkdown) : (
            <p className="analysis-placeholder">Generate a summarized report from the telemetry stream.</p>
          )}
        </article>

        {featuredMetrics.map((metric) => (
          <article className="metric-card" key={metric.key}>
            <span>{metric.label}</span>
            <strong>{metricText(metric)}</strong>
            <p>{metric.description}</p>
          </article>
        ))}
      </section>

      <section id="testbed" className="simulation-workspace">
        <div className="section-heading">
          <p className="eyebrow">Simulated merchant environment</p>
          <h2>RidgeRun storefront under test</h2>
        </div>
        {session !== null && cart !== null ? (
          <div className="commerce-grid" data-agent-safe-root ref={testbedRef}>
            <div className="product-list">
              <div className="policy-strip">
                <button type="button" data-agent-action="view_shipping_policy">
                  Shipping promise: core trail sizes arrive by Friday
                </button>
                <button type="button" data-agent-action="view_return_policy">
                  Return policy: 30-day unworn gear returns
                </button>
              </div>
              {session.products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  selectedVariantId={selectedVariantId}
                  onSelectVariant={selectVariant}
                  onAddToCart={addToCart}
                />
              ))}
            </div>
            <div className="side-stack">
              <CartDrawer cart={cart} />
              <section className="lab-panel compact">
                <p className="eyebrow">Failure labels</p>
                <div className="failure-list">
                  {(telemetry?.failures ?? []).map((failure) => (
                    <span key={failure}>{failure.replaceAll("_", " ")}</span>
                  ))}
                </div>
              </section>
            </div>
          </div>
        ) : (
          <div className="loading-page">Loading simulated storefront...</div>
        )}
      </section>

      <TracePanel entries={traceEntries} />

      <section id="mcp" className="mcp-panel">
        <div className="section-heading">
          <p className="eyebrow">MCP readiness</p>
          <h2>Recommended tools and resources for agents</h2>
        </div>
        <div className="mcp-grid">
          {(mcpReadiness?.recommendations ?? []).map((recommendation) => (
            <article className="mcp-card" key={recommendation.name}>
              <span>{recommendation.kind}</span>
              <h3>{recommendation.name}</h3>
              <p>{recommendation.description}</p>
              <code>{recommendation.schema_preview_json}</code>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
