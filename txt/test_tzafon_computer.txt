from __future__ import annotations

import json

import httpx

from app.computer.protocol import ComputerContinueRequest, ComputerStartRequest
from app.computer.tzafon_computer import TzafonComputerClient
from app.config import AppSettings
from app.ids import ComputerCallId, ComputerResponseId, ProductId, VariantId
from app.models import BrowserDomSummary, BrowserObservation, ComputerActionType, Viewport


def observation(selected: bool = False, cart_count: int = 0) -> BrowserObservation:
    return BrowserObservation(
        url="http://localhost:5178/agent-session/sess_123",
        screenshot="data:image/png;base64,",
        viewport=Viewport(width=800, height=600),
        dom_summary=BrowserDomSummary(
            selected_variant_id=VariantId("shoe_123_105_wide") if selected else None,
            cart_count=cart_count,
            cart_product_ids=[ProductId("shoe_123")] if cart_count > 0 else [],
        ),
    )


def settings() -> AppSettings:
    return AppSettings(
        _env_file=None,
        TZAFON_API_KEY="tz-test",
        TZAFON_API_BASE_URL="https://mock.tzafon.test",
        TZAFON_COMPUTER_MODEL="tzafon.northstar-cua-fast-1.6",
        AGENTREADY_HARNESS_MODE="scripted",
        AGENTREADY_COMPUTER_CLIENT="tzafon",
    )


async def test_tzafon_client_posts_harness_task_and_returns_typed_click() -> None:
    captured_payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://mock.tzafon.test/agent/tasks/stream"
        assert request.headers["Authorization"] == "Bearer tz-test"
        captured = json.loads(request.content.decode("utf-8"))
        assert isinstance(captured, dict)
        captured_payloads.append(captured)
        return httpx.Response(
            200,
            content=b'data: {"event":"accepted"}\n\n',
            headers={"content-type": "text/event-stream"},
        )

    client = TzafonComputerClient(settings(), transport=httpx.MockTransport(handler))
    turn = await client.start(
        ComputerStartRequest(
            goal="Select 10.5 Wide for StormRunner GTX and add it to cart.",
            observation=observation(),
        )
    )

    assert captured_payloads[0]["agent_type"] == "harness"
    assert captured_payloads[0]["stream_delta"] is True
    assert captured_payloads[0]["mode"] == "tzafon.northstar-cua-fast-1.6"
    assert "StormRunner GTX" in str(captured_payloads[0]["instruction"])
    assert turn.actions[0].type == ComputerActionType.CLICK
    assert "Tzafon Northstar" in turn.actions[0].reason


async def test_tzafon_client_continues_until_cart_is_present() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b'data: {"event":"accepted"}\n\n')

    client = TzafonComputerClient(settings(), transport=httpx.MockTransport(handler))
    second = await client.continue_turn(
        ComputerContinueRequest(
            previous_response_id=ComputerResponseId("tzafon_response_1"),
            call_id=ComputerCallId("tzafon_call_1"),
            observation=observation(selected=True),
        )
    )
    done = await client.continue_turn(
        ComputerContinueRequest(
            previous_response_id=second.response_id,
            call_id=ComputerCallId("tzafon_call_2"),
            observation=observation(selected=True, cart_count=1),
        )
    )

    assert second.actions[0].reason == "Tzafon Northstar added the recommended product to cart"
    assert done.completed is True
    assert len(done.actions) == 0
