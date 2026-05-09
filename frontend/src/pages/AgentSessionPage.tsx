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
    const guideStart = await postCustomerMessage(sessionId, "Run the autonomous commerce-readiness simulation.");
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
    return <main className="loading-page">Loading AgentReady session...</main>;
  }

  return (
    <main className="session-page" data-agent-safe-root ref={rootRef}>
      <section className="storefront-band">
        <div>
          <p className="eyebrow">RidgeRun merchant storefront</p>
          <h1>Trail gear under autonomous CUA test</h1>
        </div>
        <div className="source-pill">Intent from {session.source_agent}</div>
      </section>

      <section className="commerce-grid">
        <div className="product-list">
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
          <AssistantPanel
            intentGoal={session.intent_goal}
            assistantMessage={assistantMessage}
            prompts={session.relationship_prompts}
            runtime={runtime}
            onAllowGuide={() => void allowGuide()}
            guideRunning={guideRunning}
          />
          <CartDrawer cart={cart} />
        </div>
      </section>

      <TracePanel entries={traceEntries} />
    </main>
  );
}
