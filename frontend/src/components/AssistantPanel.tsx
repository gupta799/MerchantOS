import type { ReactElement } from "react";
import type { RelationshipPrompt, RuntimeResponse } from "../api/types";

type AssistantPanelProps = {
  intentGoal: string;
  assistantMessage: string;
  prompts: RelationshipPrompt[];
  runtime?: RuntimeResponse | null;
  onAllowGuide: () => void;
  guideRunning: boolean;
};

const promptLabels: Record<RelationshipPrompt, string> = {
  order_updates: "Order updates",
  loyalty_signup: "RidgeRun rewards",
  save_preferences: "Save fit preferences"
};

export function AssistantPanel({
  intentGoal,
  assistantMessage,
  prompts,
  runtime,
  onAllowGuide,
  guideRunning
}: AssistantPanelProps): ReactElement {
  const activeRuntime = runtime ?? null;
  const hasScriptedComponent =
    activeRuntime?.harness_mode === "scripted" || activeRuntime?.computer_client_mode === "scripted";
  const modeLabel =
    activeRuntime?.harness_mode === "deepagents" && activeRuntime.computer_client_mode === "scripted"
      ? "Hybrid demo mode"
      : hasScriptedComponent
        ? "Scripted demo mode"
        : "Live agent mode";

  return (
    <aside className="assistant-panel">
      <p className="eyebrow">Merchant assistant</p>
      <h2>Autonomous CUA simulation</h2>
      {activeRuntime !== null && (
        <div className={hasScriptedComponent ? "mode-banner scripted" : "mode-banner live"}>
          <strong>{modeLabel}</strong>
          <span>
            Harness: {activeRuntime.harness_mode} · Model: {activeRuntime.harness_model_provider}/
            {activeRuntime.harness_model} · Computer use: {activeRuntime.computer_client_mode}
          </span>
        </div>
      )}
      <p className="intent">“{intentGoal}”</p>
      <p>{assistantMessage}</p>
      {hasScriptedComponent && (
        <p className="demo-note">
          Press allow to run deterministic mocked CUA actions: select the recommended size, add it to cart, and
          write telemetry to the trace.
        </p>
      )}
      <button type="button" className="primary-action" onClick={onAllowGuide} disabled={guideRunning}>
        {guideRunning ? "Simulating..." : "Run simulation"}
      </button>
      <div className="prompt-list">
        {prompts.map((prompt) => (
          <span key={prompt}>{promptLabels[prompt]}</span>
        ))}
      </div>
    </aside>
  );
}
