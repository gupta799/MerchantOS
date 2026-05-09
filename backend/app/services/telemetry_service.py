from __future__ import annotations

from app.ids import SessionId, SimulationId
from app.models import (
    AgentReadinessReport,
    FailureLabel,
    TelemetryMetric,
    TelemetrySummaryAllResponse,
    TelemetrySummaryResponse,
    TraceEntry,
    VerificationStatus,
)
from app.store import InMemoryStore


class TelemetryService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def build_report(self, simulation_id: SimulationId, session_id: SessionId) -> AgentReadinessReport:
        traces = self._store.traces_for_session(session_id)
        metrics = self.metrics_for(session_id, traces)
        failures = self.failures_for(session_id, traces)
        score = self.score_for(metrics, failures)
        return AgentReadinessReport(
            simulation_id=simulation_id,
            readiness_score=score,
            summary=self.summary_for(score, failures),
            metrics=metrics,
            failures=failures,
            recommendations=self.recommendations_for(failures),
        )

    def summarize_simulation(self, simulation_id: SimulationId) -> TelemetrySummaryResponse:
        simulation = self._store.get_simulation(simulation_id)
        session = self._store.get_session(simulation.session_id)
        traces = self._store.traces_for_session(simulation.session_id)
        report = self.build_report(simulation_id, simulation.session_id)
        metrics = {metric.key: metric for metric in report.metrics}
        action_entries = [entry for entry in traces if entry.action is not None]
        last_action = action_entries[-1] if action_entries else None
        last_action_label = "observation"
        if last_action is not None and last_action.action is not None:
            last_action_label = f"{last_action.action.type} · {last_action.action.reason}"

        lines = [
            "# Telemetry analysis",
            "",
            f"**Simulation:** {simulation.simulation_id}",
            f"**Session:** {session.session_id}",
            f"**Scenario:** {simulation.scenario.title}",
            f"**Goal:** {simulation.current_goal}",
            "",
            "## Highlights",
            f"- Readiness score: **{report.readiness_score}**",
            f"- Task completion: **{metrics['task_completion_rate'].value}%**",
            f"- Action success rate: **{metrics['action_success_rate'].value}%**",
            f"- DOM action coverage: **{metrics['dom_action_coverage'].value}%**",
            f"- Screenshot confidence: **{metrics['screenshot_state_confidence'].value}%**",
            "",
            "## Issues and risks",
        ]

        if len(report.failures) == 0:
            lines.append("- No failure labels detected in this run.")
        else:
            for failure in report.failures:
                lines.append(f"- {self._failure_label_text(failure)}")

        lines.extend(
            [
                "",
                "## Evidence",
                f"- Trace entries: **{len(traces)}**",
                f"- Actions executed: **{len(action_entries)}**",
                f"- Actions to completion: **{metrics['actions_to_completion'].value}**",
                f"- Last observed action: **{last_action_label}**",
                "",
                "## Recommendations",
            ]
        )
        for recommendation in report.recommendations:
            lines.append(f"- {recommendation}")

        lines.extend(
            [
                "",
                "## Merchant-ready signals",
                "- High DOM action coverage suggests strong data-agent affordances.",
                "- Screenshot confidence indicates replayable evidence for audits.",
                "- Readiness score combines completion, reliability, and safety indicators.",
            ]
        )

        return TelemetrySummaryResponse(
            simulation_id=simulation_id,
            model="openai:gpt-4.1-mini-mock",
            markdown="\n".join(lines),
        )

    def summarize_all_simulations(self) -> TelemetrySummaryAllResponse:
        simulations = list(self._store.simulations.values())
        if len(simulations) == 0:
            return TelemetrySummaryAllResponse(
                simulation_ids=[],
                model="openai:gpt-4.1-mini-mock",
                markdown="# Telemetry analysis\n\nNo simulations available yet.",
            )
        summaries = [self.summarize_simulation(sim.simulation_id) for sim in simulations]
        scores = [self._store.get_simulation(summary.simulation_id).report.readiness_score for summary in summaries]
        average_score = round(sum(scores) / len(scores)) if len(scores) > 0 else 0
        latest = max(simulations, key=lambda sim: sim.created_at)
        lines = [
            "# Telemetry analysis (all simulations)",
            "",
            f"**Total runs:** {len(simulations)}",
            f"**Average readiness score:** {average_score}",
            f"**Latest run:** {latest.simulation_id}",
            "",
            "## Success signals",
            "- Readiness scores show how reliably agents complete the cart task.",
            "- High DOM action coverage indicates strong data-agent affordances.",
            "- Screenshot confidence confirms replayable evidence for audits.",
            "",
            "## Risk signals",
            "- Loop detections and no-op clicks indicate missing state feedback.",
            "- Unsafe action blocks highlight merchant policy safeguards at work.",
            "",
            "## Recommendations",
            "- Prioritize runs with low readiness scores for UI affordance improvements.",
            "- Add MCP tools/resources for the highest-friction steps.",
        ]
        return TelemetrySummaryAllResponse(
            simulation_ids=[sim.simulation_id for sim in simulations],
            model="openai:gpt-4.1-mini-mock",
            markdown="\n".join(lines),
        )

    def metrics_for(self, session_id: SessionId, traces: list[TraceEntry]) -> list[TelemetryMetric]:
        action_entries = [entry for entry in traces if entry.action is not None]
        observation_entries = [entry for entry in traces if entry.observation is not None]
        successful_actions = [
            entry
            for entry in action_entries
            if entry.verification.status == VerificationStatus.SUCCEEDED
        ]
        blocked_actions = [
            entry
            for entry in action_entries
            if entry.verification.status == VerificationStatus.BLOCKED
        ]
        action_total = len(action_entries)
        action_success_rate = 100.0 if action_total == 0 else round(len(successful_actions) / action_total * 100, 1)
        cart = self._store.get_cart(session_id)
        task_completion_rate = 100.0 if len(cart.items) > 0 else 0.0
        no_op_click_count = float(
            len(
                [
                    entry
                    for entry in action_entries
                    if entry.verification.status == VerificationStatus.FAILED
                    and entry.action is not None
                    and entry.action.type == "click"
                ]
            )
        )
        loop_count = float(self._loop_count(action_entries))
        latest_observation = observation_entries[-1].observation if len(observation_entries) > 0 else None
        visible_actions = latest_observation.dom_summary.visible_agent_actions if latest_observation is not None else []
        action_names = {action.action for action in visible_actions}
        coverage = round(len(action_names.intersection({"select_variant", "add_to_cart"})) / 2 * 100, 1)
        screenshot_confidence = 0.0
        if latest_observation is not None and latest_observation.screenshot.startswith("data:image/png;base64,"):
            screenshot_confidence = 95.0
        return [
            TelemetryMetric(
                key="task_completion_rate",
                label="Task completion",
                value=task_completion_rate,
                unit="%",
                description="Whether the autonomous CUA agent reached the target cart state.",
            ),
            TelemetryMetric(
                key="action_success_rate",
                label="Action success",
                value=action_success_rate,
                unit="%",
                description="Approved actions that executed successfully in the browser SDK.",
            ),
            TelemetryMetric(
                key="no_op_click_count",
                label="No-op clicks",
                value=no_op_click_count,
                unit="count",
                description="Click actions that did not produce a verified state transition.",
            ),
            TelemetryMetric(
                key="loop_count",
                label="Loop detections",
                value=loop_count,
                unit="count",
                description="Repeated action patterns that suggest the agent is stuck.",
            ),
            TelemetryMetric(
                key="blocked_unsafe_action_count",
                label="Blocked unsafe actions",
                value=float(len(blocked_actions)),
                unit="count",
                description="Actions stopped by merchant safety policy before reaching the browser.",
            ),
            TelemetryMetric(
                key="missing_structured_affordance_count",
                label="Missing affordances",
                value=0.0 if len(visible_actions) > 0 else 1.0,
                unit="count",
                description="Screens where the harness found no explicit agent-readable actions.",
            ),
            TelemetryMetric(
                key="actions_to_completion",
                label="Actions to completion",
                value=float(action_total),
                unit="actions",
                description="Number of browser actions needed for this simulation run.",
            ),
            TelemetryMetric(
                key="dom_action_coverage",
                label="DOM action coverage",
                value=coverage,
                unit="%",
                description="Coverage of expected merchant actions exposed through data-agent attributes.",
            ),
            TelemetryMetric(
                key="screenshot_state_confidence",
                label="Screenshot confidence",
                value=screenshot_confidence,
                unit="%",
                description="Whether screenshots were captured for replay and state verification.",
            ),
        ]

    def failures_for(self, session_id: SessionId, traces: list[TraceEntry]) -> list[FailureLabel]:
        metrics = {metric.key: metric.value for metric in self.metrics_for(session_id, traces)}
        labels: list[FailureLabel] = []
        if metrics["missing_structured_affordance_count"] > 0:
            labels.extend([FailureLabel.NO_VISIBLE_ACTION, FailureLabel.MISSING_AGENT_ACTION])
        if metrics["no_op_click_count"] > 0:
            labels.append(FailureLabel.NO_OP_CLICK)
        if metrics["loop_count"] > 0:
            labels.append(FailureLabel.LOOP_DETECTED)
        if metrics["blocked_unsafe_action_count"] > 0:
            labels.append(FailureLabel.UNSAFE_ACTION_BLOCKED)
        if metrics["task_completion_rate"] == 100:
            labels.append(FailureLabel.TASK_COMPLETED)
        elif len(traces) >= 6:
            labels.append(FailureLabel.TASK_FAILED)
        return labels

    def score_for(self, metrics: list[TelemetryMetric], failures: list[FailureLabel]) -> int:
        metric_values = {metric.key: metric.value for metric in metrics}
        base_score = (
            metric_values["task_completion_rate"] * 0.32
            + metric_values["action_success_rate"] * 0.22
            + metric_values["dom_action_coverage"] * 0.22
            + metric_values["screenshot_state_confidence"] * 0.14
            + (100 - min(metric_values["blocked_unsafe_action_count"] * 25, 100)) * 0.10
        )
        penalty = 8 * len([label for label in failures if label not in {FailureLabel.TASK_COMPLETED}])
        return max(0, min(100, round(base_score - penalty)))

    def summary_for(self, score: int, failures: list[FailureLabel]) -> str:
        if FailureLabel.TASK_COMPLETED in failures:
            return "The autonomous CUA simulation completed the core cart task and produced replayable telemetry."
        if score >= 70:
            return "The site exposes useful agent affordances, but the simulation still found reliability gaps."
        return "The site needs stronger agent-readable affordances, state confirmation, and MCP/tool surfaces."

    def recommendations_for(self, failures: list[FailureLabel]) -> list[str]:
        recommendations = [
            "Expose product search, product facts, and cart preparation as MCP tools/resources.",
            "Keep checkout and payment behind explicit human confirmation.",
            "Retain data-agent attributes for key buttons so computer-use actions can be validated.",
        ]
        if FailureLabel.NO_VISIBLE_ACTION in failures:
            recommendations.insert(0, "Add explicit data-agent-action attributes to primary commerce controls.")
        if FailureLabel.LOOP_DETECTED in failures:
            recommendations.insert(0, "Add clearer state transitions after clicks so agents can stop retrying.")
        if FailureLabel.NO_OP_CLICK in failures:
            recommendations.insert(0, "Add visual or DOM state confirmation after each important interaction.")
        return recommendations

    def _failure_label_text(self, failure: FailureLabel) -> str:
        mapping = {
            FailureLabel.NO_VISIBLE_ACTION: "No visible agent actions detected on key screens.",
            FailureLabel.MISSING_AGENT_ACTION: "Missing agent-readable affordances for primary flows.",
            FailureLabel.NO_OP_CLICK: "No-op clicks observed; actions did not change state.",
            FailureLabel.LOOP_DETECTED: "Loop behavior detected; the agent repeated similar actions.",
            FailureLabel.UNSAFE_ACTION_BLOCKED: "Unsafe actions were blocked by merchant policy.",
            FailureLabel.TASK_COMPLETED: "Core cart task completed successfully.",
            FailureLabel.TASK_FAILED: "Task failed to complete within the trace window.",
            FailureLabel.AMBIGUOUS_SELECTOR: "Ambiguous UI selectors caused uncertainty.",
            FailureLabel.MISSING_STRUCTURED_DATA: "Structured data gaps reduced agent reliability.",
        }
        return mapping.get(failure, failure.value)

    def _loop_count(self, action_entries: list[TraceEntry]) -> int:
        repeated = 0
        previous_signature = ""
        streak = 0
        for entry in action_entries:
            if entry.action is None:
                continue
            signature = f"{entry.action.type}:{entry.action.reason}"
            if signature == previous_signature:
                streak += 1
            else:
                streak = 1
                previous_signature = signature
            if streak >= 3:
                repeated += 1
        return repeated
