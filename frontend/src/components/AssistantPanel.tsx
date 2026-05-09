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
  loyalty_signup: "Trail club rewards",
  save_preferences: "Save fit profile"
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
  const usesTzafon = activeRuntime?.computer_client_mode === "tzafon";
  const modeLabel = usesTzafon ? "Tzafon Northstar live" : "Readiness probe";

  return (
    <aside className="assistant-panel">
      <p className="eyebrow">Demo control</p>
      <h2>Computer-use simulation</h2>
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
      {usesTzafon ? (
        <p className="demo-note">
          Sends this storefront observation to Tzafon Northstar, executes approved browser actions here,
          and records the trace for MerchantOS telemetry.
        </p>
      ) : null}
      {hasScriptedComponent && activeRuntime?.computer_client_mode !== "tzafon" && (
        <p className="demo-note">
          Runs the agent-readiness probe without exposing the simulation layer to shoppers.
        </p>
      )}
      <button type="button" className="primary-action" onClick={onAllowGuide} disabled={guideRunning}>
        {guideRunning ? "Running simulation..." : usesTzafon ? "Run Tzafon CUA simulation" : "Run readiness probe"}
      </button>
      <div className="prompt-list">
        {prompts.map((prompt) => (
          <span key={prompt}>{promptLabels[prompt]}</span>
        ))}
      </div>
    </aside>
  );
}
