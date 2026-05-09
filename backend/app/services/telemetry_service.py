from __future__ import annotations

from app.ids import SessionId, SimulationId
from app.models import AgentReadinessReport, FailureLabel, TelemetryMetric, TraceEntry, VerificationStatus
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
