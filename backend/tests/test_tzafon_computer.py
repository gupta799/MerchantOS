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
        assert request.url == "https://mock.tzafon.test/v1/responses"
        assert request.headers["Authorization"] == "Bearer tz-test"
        captured = json.loads(request.content.decode("utf-8"))
        assert isinstance(captured, dict)
        captured_payloads.append(captured)
        return httpx.Response(
            200,
            json={
                "id": "resp_1",
                "output": [
                    {
                        "type": "computer_call",
                        "call_id": "call_1",
                        "action": {"type": "click", "x": 500, "y": 400, "button": "left"},
                    }
                ],
            },
        )

    client = TzafonComputerClient(settings(), transport=httpx.MockTransport(handler))
    turn = await client.start(
        ComputerStartRequest(
            goal="Select 10.5 Wide for StormRunner GTX and add it to cart.",
            observation=observation(),
        )
    )

    assert captured_payloads[0]["model"] == "tzafon.northstar-cua-fast-1.6"
    assert captured_payloads[0]["tools"] == [
        {"type": "computer_use", "display_width": 1000, "display_height": 1000, "environment": "browser"}
    ]
    assert "StormRunner GTX" in str(captured_payloads[0]["input"])
    assert "previous_response_id" not in captured_payloads[0]
    assert turn.actions[0].type == ComputerActionType.CLICK
    assert turn.actions[0].x == 400
    assert turn.actions[0].y == 240
    assert "Tzafon Northstar" in turn.actions[0].reason


async def test_tzafon_client_continues_until_cart_is_present() -> None:
    captured_payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured = json.loads(request.content.decode("utf-8"))
        assert isinstance(captured, dict)
        captured_payloads.append(captured)
        return httpx.Response(
            200,
            json={
                "id": "resp_2",
                "output": [
                    {
                        "type": "message",
                        "content": [{"text": "The observed page now satisfies the visual goal."}],
                    }
                ],
            },
        )

    client = TzafonComputerClient(settings(), transport=httpx.MockTransport(handler))
    done = await client.continue_turn(
        ComputerContinueRequest(
            previous_response_id=ComputerResponseId("tzafon_response_1"),
            call_id=ComputerCallId("tzafon_call_1"),
            observation=observation(selected=True),
        )
    )

    assert captured_payloads[0]["previous_response_id"] == "tzafon_response_1"
    assert captured_payloads[0]["input"][0]["type"] == "computer_call_output"
    assert captured_payloads[0]["input"][0]["call_id"] == "tzafon_call_1"
    assert done.completed is True
    assert len(done.actions) == 0
