from __future__ import annotations

import pytest

from app.errors import PolicyViolationError
from app.ids import new_action_id
from app.models import BrowserDomSummary, BrowserObservation, ComputerAction, ComputerActionType, Viewport
from app.policies import MerchantPolicy


def observation() -> BrowserObservation:
    return BrowserObservation(
        url="http://localhost:5173/agent-session/sess_123",
        screenshot="data:image/png;base64,",
        viewport=Viewport(width=800, height=600),
        dom_summary=BrowserDomSummary(),
    )


def test_policy_allows_click_inside_storefront() -> None:
    MerchantPolicy().validate_action(
        ComputerAction(type=ComputerActionType.CLICK, action_id=new_action_id(), x=20, y=20),
        observation(),
    )


def test_policy_blocks_offsite_url() -> None:
    offsite = observation().model_copy(update={"url": "https://evil.example"})
    with pytest.raises(PolicyViolationError):
        MerchantPolicy().validate_action(
            ComputerAction(type=ComputerActionType.CLICK, action_id=new_action_id(), x=20, y=20),
            offsite,
        )


def test_policy_blocks_payment_text() -> None:
    with pytest.raises(PolicyViolationError):
        MerchantPolicy().validate_action(
            ComputerAction(
                type=ComputerActionType.TYPE,
                action_id=new_action_id(),
                text="4111 1111 1111 1111",
            ),
            observation(),
        )

