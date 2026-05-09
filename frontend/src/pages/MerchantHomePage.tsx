import type { ReactElement } from "react";
import { useEffect, useRef, useState } from "react";
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

export function MerchantHomePage(): ReactElement {
  const testbedRef = useRef<HTMLDivElement | null>(null);
  const clientRef = useRef<AgentReadyClient | null>(null);
  const createdRef = useRef(false);
  const runRequestedRef = useRef(false);
  const startedSessionRef = useRef("");
  const analysisTimerRef = useRef<number | null>(null);
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
  const [telemetryOpen, setTelemetryOpen] = useState(true);
  const [analysisMarkdown, setAnalysisMarkdown] = useState("");
  const [analysisStatus, setAnalysisStatus] = useState<string | null>(null);
  const [analysisStreaming, setAnalysisStreaming] = useState(false);
  const [analysisTarget, setAnalysisTarget] = useState("current");

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

  async function createAndRunSimulation(shouldStartRun = true): Promise<void> {
    clientRef.current?.disconnect();
    clientRef.current = null;
    startedSessionRef.current = "";
    runRequestedRef.current = shouldStartRun;
    setRerunning(true);
    setTraceEntries([]);
    setTelemetry(null);
    setMcpReadiness(null);
    setAnalysisMarkdown("");
    setAnalysisStatus(null);
    setStatusMessage(shouldStartRun ? "Creating automated CUA simulation run..." : "Preparing RidgeRun test storefront...");
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
      !shouldStartRun
        ? "RidgeRun storefront is ready. Use Run CUA demo to start the visible agent simulation."
        : browserEnvironment === "kernel"
        ? "Kernel cloud browser launched. Tzafon computer-use actions will stream into telemetry."
        : "Browser SDK connected. Autonomous agent run will start automatically."
    );
    setRerunning(false);
    focusSimulationWorkspace();
  }

  async function startAutonomousRun(sessionId: string, simulationId: string): Promise<void> {
    if (startedSessionRef.current === sessionId) {
      return;
    }
    if (!runRequestedRef.current) {
      return;
    }
    startedSessionRef.current = sessionId;
    setTelemetryOpen(true);
    focusSimulationWorkspace();
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

  async function runDemoSimulation(): Promise<void> {
    if (session === null || simulation === null) {
      await createAndRunSimulation(true);
      return;
    }
    if (simulation.status === "completed" || simulation.status === "failed") {
      await createAndRunSimulation(true);
      return;
    }
    runRequestedRef.current = true;
    setRerunning(true);
    try {
      await startAutonomousRun(session.session_id, simulation.simulation_id);
    } finally {
      setRerunning(false);
    }
  }

  function focusSimulationWorkspace(): void {
    window.setTimeout(() => {
      document.getElementById("testbed")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 250);
  }

  useEffect(() => {
    if (createdRef.current) {
      return;
    }
    createdRef.current = true;
    void createAndRunSimulation(false);
  }, []);

  useEffect(() => {
    return () => {
      if (analysisTimerRef.current !== null) {
        window.clearInterval(analysisTimerRef.current);
      }
    };
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

  function streamAnalysis(markdown: string, intervalMs: number): void {
    if (analysisTimerRef.current !== null) {
      window.clearInterval(analysisTimerRef.current);
    }
    const lines = markdown.split("\n");
    let index = 0;
    setAnalysisMarkdown("");
    setAnalysisStreaming(true);
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
    }, intervalMs);
  }

  async function analyzeTelemetry(): Promise<void> {
    const targetId = analysisTarget === "current" ? simulation?.simulation_id : analysisTarget;
    if (targetId === undefined) {
      return;
    }
    setTelemetryOpen(true);
    setAnalysisStatus("Summarizing this simulation...");
    try {
      const summary = await summarizeTelemetry({ simulation_id: targetId });
      streamAnalysis(summary.markdown, 42);
    } catch {
      setAnalysisStreaming(false);
      setAnalysisStatus("Telemetry analysis failed. Try rerunning the simulation.");
    }
  }

  async function analyzeAllTelemetry(): Promise<void> {
    setTelemetryOpen(true);
    setAnalysisStatus("Summarizing all simulations...");
    try {
      const summary = await summarizeAllTelemetry();
      streamAnalysis(summary.markdown, 34);
    } catch {
      setAnalysisStreaming(false);
      setAnalysisStatus("All-runs summary failed. Try again.");
    }
  }

  const actionTraceCount = traceEntries.filter((entry) => entry.action !== null && entry.action !== undefined).length;
  const failureCount = telemetry?.failures.filter((failure) => failure !== "task_completed").length ?? 0;
  const readinessScore = simulation?.report.readiness_score ?? 0;

  return (
    <main className="home-page lab-page">
      <div className="announcement-bar">MerchantOS · agent-readiness telemetry for commerce teams</div>
      <header className="shop-header">
        <a className="brand-mark" href="/" aria-label="MerchantOS home">
          <span>M</span>
          MerchantOS
        </a>
        <label className="retail-search">
          <span>Search</span>
          <input readOnly value="runs, traces, failures, MCP readiness" />
        </label>
        <nav className="shop-nav" aria-label="Lab navigation">
          <a href="#telemetry">Agent telemetry</a>
          <a href="#testbed">RidgeRun test site</a>
          <a href="#telemetry" onClick={() => setTelemetryOpen(true)}>MCP readiness</a>
        </nav>
        <div className="header-actions">
          <a href="#testbed">View environment</a>
        </div>
      </header>

      <section className="lab-hero">
        <div>
          <p className="eyebrow">MerchantOS dashboard</p>
          <h1>Agent-readiness telemetry for commerce teams.</h1>
          <p>
            Tzafon Northstar navigates this storefront like a buyer. AgentReady records every
            observation, click, verification, and failure so merchants can make their sites agent-ready.
          </p>
        </div>
        <aside className="simulation-map" aria-label="Run status">
          <div className="map-header">
            <span>Readiness score</span>
            <strong>{simulation?.report.readiness_score ?? 0}</strong>
          </div>
          <div className="map-stage active">
            <span>1</span>
            <div>
              <strong>Goal</strong>
              <p>Find a waterproof 10.5 Wide trail shoe under $150 and stop before checkout.</p>
            </div>
          </div>
          <div className="map-stage">
            <span>2</span>
            <div>
              <strong>Computer-use model</strong>
              <p>{runtime?.computer_client_mode ?? "tzafon"} / {runtime?.computer_model ?? "northstar-cua-fast"}</p>
            </div>
          </div>
          <div className="map-stage">
            <span>3</span>
            <div>
              <strong>Harness result</strong>
              <p>{simulation?.report.summary ?? "Waiting for the first telemetry sample."}</p>
            </div>
          </div>
        </aside>
      </section>

      <section id="telemetry" className="lab-grid">
        <article className="lab-panel wide">
          <p className="eyebrow">Live autonomous run</p>
          <h2>{simulation?.scenario.title ?? "Starting simulation"}</h2>
          <p>{simulation?.current_goal ?? "Preparing scenario goal..."}</p>
          <div className="run-flow">
            <span>observe</span>
            <span>act</span>
            <span>verify</span>
            <span>classify</span>
          </div>
          <div className="status-strip">
            <span>Status: {simulation?.status ?? "connecting"}</span>
            <span>{statusMessage}</span>
          </div>
          <button className="telemetry-inline-action" type="button" onClick={() => setTelemetryOpen(true)}>
            Open telemetry console
          </button>
        </article>
      </section>

      <button
        className={telemetryOpen ? "telemetry-fab hidden" : "telemetry-fab"}
        type="button"
        onClick={() => setTelemetryOpen(true)}
        aria-expanded={telemetryOpen}
      >
        Telemetry
        <span>{traceEntries.length}</span>
      </button>

      <aside className={telemetryOpen ? "telemetry-console open" : "telemetry-console"} aria-label="MerchantOS telemetry console">
        <header className="telemetry-console-header">
          <div>
            <p className="eyebrow">MerchantOS telemetry</p>
            <h2>Run intelligence</h2>
          </div>
          <button type="button" onClick={() => setTelemetryOpen(false)} aria-label="Close telemetry console">
            Close
          </button>
        </header>
        <div className="telemetry-console-grid">
          <div>
            <span>Readiness</span>
            <strong>{readinessScore}</strong>
          </div>
          <div>
            <span>Traces</span>
            <strong>{traceEntries.length}</strong>
          </div>
          <div>
            <span>Actions</span>
            <strong>{actionTraceCount}</strong>
          </div>
          <div>
            <span>Risks</span>
            <strong>{failureCount}</strong>
          </div>
        </div>
        <p className="telemetry-console-summary">
          {simulation?.report.summary ?? "Start a CUA run to stream observations, actions, and verification events."}
        </p>
        <section className="console-mcp-panel" aria-label="MCP readiness recommendations">
          <div className="console-subhead">
            <span>MCP readiness</span>
            <strong>{mcpReadiness?.recommendations.length ?? 0} recommendations</strong>
          </div>
          <div className="console-mcp-list">
            {(mcpReadiness?.recommendations ?? []).map((recommendation) => (
              <article key={recommendation.name}>
                <span>{recommendation.kind}</span>
                <strong>{recommendation.name}</strong>
                <p>{recommendation.description}</p>
              </article>
            ))}
          </div>
        </section>
        <div className="analysis-actions">
          <select
            className="analysis-select"
            value={analysisTarget}
            onChange={(event) => setAnalysisTarget(event.target.value)}
            disabled={analysisStreaming}
          >
            <option value="current">Current run</option>
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
            {analysisStreaming ? "Analyzing..." : "Analyze"}
          </button>
          <button type="button" className="secondary-action" onClick={() => void analyzeAllTelemetry()} disabled={analysisStreaming}>
            All runs
          </button>
        </div>
        {analysisStatus !== null ? <p className="analysis-status">{analysisStatus}</p> : null}
        {analysisMarkdown.length > 0 ? renderMarkdown(analysisMarkdown) : (
          <p className="analysis-placeholder">Use the summary controls to generate a concise telemetry readout.</p>
        )}
        <div className="telemetry-trace-card">
          <TracePanel entries={traceEntries} />
        </div>
      </aside>

      <section id="testbed" className="simulation-workspace">
        <div className="section-heading environment-heading">
          <div>
            <p className="eyebrow">Embedded test environment</p>
            <h2>RidgeRun environment</h2>
            <p className="environment-copy">Running inside MerchantOS as an isolated browser viewport.</p>
          </div>
          <span>isolated browser viewport</span>
        </div>
        {session !== null && cart !== null ? (
          <div className="kernel-embed-frame">
            <div className="kernel-embed-toolbar" aria-label="Embedded browser controls">
              <div className="browser-dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <div className="browser-address">
                <span>https://ridgerun.example/agent-test</span>
              </div>
              <div className="browser-live-status">
                <span />
                Live CUA viewport
              </div>
            </div>
            <div className="storefront-shell" data-agent-safe-root ref={testbedRef}>
            <header className="ridge-store-header">
              <a className="ridge-brand" href="#testbed" aria-label="RidgeRun storefront">
                <span>R</span>
                RidgeRun
              </a>
              <label className="ridge-search">
                <span>Search</span>
                <input readOnly value="waterproof trail running shoes" />
              </label>
              <nav aria-label="RidgeRun departments">
                <a href="#testbed">New</a>
                <a href="#testbed">Running</a>
                <a href="#testbed">Trail</a>
                <a href="#testbed">Gear</a>
              </nav>
              <button
                className="ridge-sim-button"
                type="button"
                onClick={() => void runDemoSimulation()}
                disabled={rerunning}
              >
                {rerunning ? "Running..." : "Run CUA demo"}
              </button>
            </header>
            <section className="ridge-hero" aria-label="RidgeRun campaign">
              <div>
                <p>StormRunner GTX</p>
                <h3>Built for wet miles.</h3>
                <span>Waterproof trail grip, wide-fit support, and Friday delivery.</span>
              </div>
            </section>
            <div className="commerce-grid">
              <aside className="filter-rail" aria-label="Shopping filters">
                <strong>Refine by</strong>
                <span>Waterproof</span>
                <span>Wide fit</span>
                <span>Arrives by Friday</span>
                <span>Under $150</span>
                <span>Free returns</span>
              </aside>
              <div className="product-list">
                <div className="policy-strip">
                  <button type="button" data-agent-action="view_shipping_policy">
                    Delivery: eligible trail sizes arrive by Friday
                  </button>
                  <button type="button" data-agent-action="view_return_policy">
                    Returns: 30-day unworn gear window
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
          </div>
          </div>
        ) : (
          <div className="loading-page">Loading simulated storefront...</div>
        )}
      </section>

    </main>
  );
}
