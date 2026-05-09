from __future__ import annotations

from collections.abc import Sequence
from typing import Mapping

from app.agents.plans import DeepAgentPlanResult
from app.errors import AgentReadyError


class DeepAgentParseError(AgentReadyError):
    """Raised when the DeepAgent does not return a typed plan payload."""


def parse_deep_agent_plan(output: Mapping[str, object]) -> DeepAgentPlanResult:
    if "structured_response" in output:
        structured = output["structured_response"]
        if isinstance(structured, DeepAgentPlanResult):
            return structured
    if "messages" not in output:
        raise DeepAgentParseError("DeepAgent output did not include messages")
    messages = output["messages"]
    if not isinstance(messages, Sequence):
        raise DeepAgentParseError("DeepAgent messages were not a sequence")
    for message in reversed(messages):
        content = getattr(message, "content", "")
        if isinstance(content, str):
            parsed = _parse_json_content(content)
            if parsed is not None:
                return parsed
    raise DeepAgentParseError("DeepAgent did not return a JSON plan")


def _parse_json_content(content: str) -> DeepAgentPlanResult | None:
    candidates = [content.strip(), _extract_fenced_json(content), _extract_braced_json(content)]
    for candidate in candidates:
        if candidate is None or candidate == "":
            continue
        try:
            return DeepAgentPlanResult.model_validate_json(candidate)
        except ValueError:
            continue
    return None


def _extract_fenced_json(content: str) -> str | None:
    marker = "```"
    if marker not in content:
        return None
    segments = content.split(marker)
    for segment in segments:
        stripped = segment.strip()
        if stripped.startswith("json"):
            return stripped.removeprefix("json").strip()
        if stripped.startswith("{"):
            return stripped
    return None


def _extract_braced_json(content: str) -> str | None:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return content[start : end + 1]

