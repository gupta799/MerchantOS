from __future__ import annotations

from collections.abc import Sequence

from deepagents import create_deep_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from app.agents.model_provider import build_harness_model
from app.agents.plans import DeepAgentPlanResult
from app.agents.prompts import MERCHANT_SYSTEM_PROMPT
from app.agents.tools import MerchantToolbox
from app.config import AppSettings


def build_merchant_deep_agent(
    settings: AppSettings,
    toolbox: MerchantToolbox,
    model_override: BaseChatModel | None = None,
) -> CompiledStateGraph:
    model = model_override if model_override is not None else build_harness_model(settings)
    return create_deep_agent(
        model=model,
        tools=_merchant_tools(toolbox),
        system_prompt=MERCHANT_SYSTEM_PROMPT,
        response_format=DeepAgentPlanResult,
        name="agentready_merchant_harness",
    )


def _merchant_tools(toolbox: MerchantToolbox) -> Sequence[object]:
    return (
        toolbox.get_session_context,
        toolbox.search_catalog,
        toolbox.get_cart_state,
        toolbox.build_visual_guidance_goal,
        toolbox.update_cart,
    )
