import type { ReactElement } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { createAgentIntent, getRuntime, getSession, getTrace, postCustomerMessage } from "../api/http";
import type { AgentIntentRequest, Cart, Product, RuntimeResponse, SessionResponse, TraceEntry } from "../api/types";
import { AgentReadyClient } from "../sdk/AgentReadyClient";
import { emitMerchantEvent } from "../sdk/events";
import { AssistantPanel } from "../components/AssistantPanel";
import { CartDrawer } from "../components/CartDrawer";
import { ProductCard } from "../components/ProductCard";
import { TracePanel } from "../components/TracePanel";

type RouteParams = {
  sessionId: string;
};

function currentSessionId(): RouteParams {
  const segments = window.location.pathname.split("/");
  return { sessionId: segments[segments.length - 1] };
}

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

const fallbackIntentRequest: AgentIntentRequest = {
  merchant_id: "demo_shop",
  source_agent: "chatgpt",
  user_goal: "Find waterproof trail running shoes under $150 that can arrive by Friday",
  preferences: {
    category: "trail running shoes",
    budget_max: 150,
    delivery_by: "Friday",
    size: "10.5",
    fit: "wide"
  }
};

export function AgentSessionPage(): ReactElement {
  const { sessionId } = useMemo(currentSessionId, []);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const clientRef = useRef<AgentReadyClient | null>(null);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [runtime, setRuntime] = useState<RuntimeResponse | null>(null);
  const [cart, setCart] = useState<Cart | null>(null);
  const [traceEntries, setTraceEntries] = useState<TraceEntry[]>([]);
  const [assistantMessage, setAssistantMessage] = useState("Loading automated simulation session...");
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const [guideRunning, setGuideRunning] = useState(false);

  async function refreshSession(updateAssistantMessage = true): Promise<void> {
    const loaded = await loadOrCreateSession(sessionId);
    setSession(loaded);
    setCart(loaded.cart);
    setSelectedVariantId(loaded.recommended_products[0]?.variant_id ?? null);
    if (updateAssistantMessage) {
      setAssistantMessage(loaded.assistant_message);
    }
  }

  async function loadOrCreateSession(currentId: string): Promise<SessionResponse> {
    try {
      return await getSession(currentId);
    } catch {
      const created = await createAgentIntent(fallbackIntentRequest);
      window.location.replace(created.handoff_url);
      return await new Promise<SessionResponse>(() => {});
    }
  }

  async function refreshTrace(): Promise<void> {
    const trace = await getTrace(sessionId);
    setTraceEntries(trace.entries);
    await refreshSession(false);
  }

  useEffect(() => {
    document.title = "RidgeRun Trail Supply";
    void refreshSession();
    void getRuntime()
      .then(setRuntime)
      .catch(() => setRuntime(null));
  }, [sessionId]);

  useEffect(() => {
    if (rootRef.current === null || clientRef.current !== null) {
      return;
    }
    const client = new AgentReadyClient(sessionId, rootRef.current, {
      onAssistantUpdate: setAssistantMessage,
      onTraceUpdate: () => void refreshTrace(),
      onDone: (message) => {
        setAssistantMessage(message);
        setGuideRunning(false);
        void refreshTrace();
      },
      onError: (message) => {
        setAssistantMessage(message);
        setGuideRunning(false);
      }
    });
    client.connect();
    clientRef.current = client;
    void client.emitGuidedSessionOpened();
    return () => {
      client.disconnect();
      clientRef.current = null;
    };
  }, [sessionId, session?.session_id]);

  async function allowGuide(): Promise<void> {
    setGuideRunning(true);
    await emitMerchantEvent(sessionId, {
      type: "guide_allowed",
      source: "merchant_sdk",
      message: "Manual simulation run requested"
    });
    const guideStart = await postCustomerMessage(
      sessionId,
      "Run the autonomous commerce-readiness simulation with Tzafon Northstar."
    );
    if (guideStart.status !== "running") {
      setAssistantMessage(guideStart.message);
      setGuideRunning(false);
    }
  }

  function selectVariant(variantId: string): void {
    setSelectedVariantId(variantId);
  }

  function addToCart(productId: string, variantId: string): void {
    if (cart === null || session === null) {
      return;
    }
    setCart(addCartItem(cart, session.products, productId, variantId));
  }

  if (session === null || cart === null) {
    return <main className="loading-page">Loading RidgeRun...</main>;
  }

  return (
    <main className="session-page" data-agent-safe-root ref={rootRef}>
      <div className="merchant-utility-bar">
        <span>Free shipping over $75</span>
        <span>30-day trail fit returns</span>
        <span>Agent-readable product data enabled</span>
      </div>
      <header className="merchant-site-header">
        <a className="merchant-logo" href="/" aria-label="RidgeRun home">
          <span>R</span>
          RidgeRun
        </a>
        <nav aria-label="RidgeRun navigation">
          <a href="#shop">Trail shoes</a>
          <a href="#fit">Fit guide</a>
          <a href="#shipping">Shipping</a>
          <a href="#cart">Cart</a>
        </nav>
        <div className="merchant-header-actions">
          <button type="button">Search</button>
          <button type="button">Account</button>
          <a href="#cart">Bag {cart.items.length}</a>
        </div>
      </header>

      <section className="merchant-store-hero">
        <div>
          <p className="eyebrow">Spring trail system</p>
          <h1>Waterproof trail shoes built for messy weekends.</h1>
          <p>
            Find stable, wide-friendly trail runners with clear delivery promises, easy returns,
            and fit details that a human shopper or buying agent can understand.
          </p>
          <div className="hero-actions">
            <a className="primary-action" href="#shop">Shop trail shoes</a>
            <a className="secondary-action" href="#fit">Check fit notes</a>
            <button
              type="button"
              className="tzafon-action"
              onClick={() => void allowGuide()}
              disabled={guideRunning}
            >
              {guideRunning ? "Tzafon is running..." : "Run Tzafon CUA simulation"}
            </button>
          </div>
        </div>
        <aside className="merchant-intent-card">
          <span>Live agent brief</span>
          <strong>Waterproof trail runner · under $150 · arrives Friday · 10.5 wide</strong>
          <p>
            Source: {session.source_agent}. The simulation will observe this page, ask Tzafon Northstar
            for browser actions, and stop before checkout.
          </p>
        </aside>
      </section>

      <section className="merchant-editorial-row" aria-label="RidgeRun shopping highlights">
        <article>
          <span>01</span>
          <strong>Storm-tested waterproofing</strong>
          <p>All-weather uppers and grippy lugs for wet trail days.</p>
        </article>
        <article>
          <span>02</span>
          <strong>Wide sizes surfaced</strong>
          <p>Fit variants stay visible so agents do not have to infer size state.</p>
        </article>
        <article>
          <span>03</span>
          <strong>Policy clarity</strong>
          <p>Shipping and return promises are structured as clickable affordances.</p>
        </article>
      </section>

      <section className="merchant-trust-row" id="shipping">
        <button type="button" data-agent-action="view_shipping_policy">
          <strong>Friday delivery</strong>
          <span>Core trail sizes ship from local inventory.</span>
        </button>
        <button type="button" data-agent-action="view_return_policy">
          <strong>30-day returns</strong>
          <span>Try unworn gear indoors before committing.</span>
        </button>
        <button type="button" data-agent-action="view_fit_policy">
          <strong>Wide-fit guidance</strong>
          <span>Variant labels stay visible for agent verification.</span>
        </button>
      </section>

      <section id="fit" className="merchant-fit-band">
        <p className="eyebrow">Fit and policy clarity</p>
        <h2>Every key decision is visible, structured, and verifiable.</h2>
        <p>
          This storefront intentionally exposes delivery, return policy, variant, and cart state so
          computer-use agents can complete research without guessing or leaving the merchant site.
        </p>
      </section>

      <section id="shop" className="commerce-grid merchant-commerce-grid">
        <div className="product-list">
          <div className="merchant-shop-heading">
            <div>
              <p className="eyebrow">Shop the agent-ready collection</p>
              <h2>Trail runners with visible fit, shipping, and cart state.</h2>
            </div>
            <span>{session.products.length} products</span>
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
          <div id="cart">
            <CartDrawer cart={cart} />
          </div>
          <AssistantPanel
            intentGoal={session.intent_goal}
            assistantMessage={assistantMessage}
            prompts={session.relationship_prompts}
            runtime={runtime}
            onAllowGuide={() => void allowGuide()}
            guideRunning={guideRunning}
          />
        </div>
      </section>

      <TracePanel entries={traceEntries} />
    </main>
  );
}
