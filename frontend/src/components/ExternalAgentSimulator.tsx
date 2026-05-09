import type { ReactElement } from "react";
import { useState } from "react";
import { createAgentIntent } from "../api/http";
import type { AgentIntentResponse } from "../api/types";

export function ExternalAgentSimulator(): ReactElement {
  const [response, setResponse] = useState<AgentIntentResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function startIntent(): Promise<void> {
    setLoading(true);
    const created = await createAgentIntent({
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
    });
    setResponse(created);
    setLoading(false);
  }

  return (
    <section className="agent-handoff-card">
      <div className="handoff-copy">
        <p className="eyebrow">AgentReady handoff</p>
        <h2>Let your shopping agent continue here.</h2>
        <p>
          A customer can arrive from ChatGPT or another buying agent, but RidgeRun keeps the
          session, cart, recommendations, and relationship prompts on the merchant site.
        </p>
      </div>
      <button className="primary-action" type="button" onClick={() => void startIntent()} disabled={loading}>
        {loading ? "Creating handoff..." : "Create merchant handoff"}
      </button>
      {response !== null ? (
        <div className="handoff-result">
          <p>{response.summary}</p>
          <a href={response.handoff_url}>Open merchant guided session</a>
        </div>
      ) : null}
    </section>
  );
}
