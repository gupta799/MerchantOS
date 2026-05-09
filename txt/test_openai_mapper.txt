from __future__ import annotations

from app.computer.mapper import map_computer_call
from app.models import ComputerActionType


def test_openai_mapper_maps_actions() -> None:
    turn = map_computer_call(
        "resp_123",
        {
            "type": "computer_call",
            "call_id": "call_123",
            "actions": [{"type": "click", "x": 10, "y": 20}],
        },
    )
    assert turn.response_id == "resp_123"
    assert turn.call_id == "call_123"
    assert turn.actions[0].type == ComputerActionType.CLICK

