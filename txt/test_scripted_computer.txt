from __future__ import annotations

from app.computer.protocol import ComputerContinueRequest, ComputerStartRequest
from app.computer.scripted_computer import ScriptedComputerClient
from app.ids import ComputerCallId, ComputerResponseId, ProductId, VariantId
from app.models import BrowserDomSummary, BrowserObservation, ComputerActionType, Viewport


def observation(selected: bool = False, cart_count: int = 0) -> BrowserObservation:
    return BrowserObservation(
        url="http://localhost:5173/agent-session/sess_123",
        screenshot="data:image/png;base64,",
        viewport=Viewport(width=800, height=600),
        dom_summary=BrowserDomSummary(
            selected_variant_id=VariantId("shoe_123_105_wide") if selected else None,
            cart_count=cart_count,
            cart_product_ids=[ProductId("shoe_123")] if cart_count > 0 else [],
        ),
    )


async def test_scripted_client_selects_then_adds() -> None:
    client = ScriptedComputerClient()
    first = await client.start(ComputerStartRequest(goal="Add shoe", observation=observation()))
    assert first.actions[0].type == ComputerActionType.CLICK
    second = await client.continue_turn(
        ComputerContinueRequest(
            previous_response_id=ComputerResponseId("scripted_response_1"),
            call_id=ComputerCallId("scripted_call_1"),
            observation=observation(selected=True),
        )
    )
    assert second.actions[0].reason == "Add StormRunner GTX to cart"

