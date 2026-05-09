from __future__ import annotations

from app.computer.openai_payloads import ComputerActionPayload, ComputerCallPayload
from app.computer.protocol import ComputerTurn
from app.errors import UnsupportedComputerActionError
from app.ids import ComputerCallId, ComputerResponseId, new_action_id
from app.models import ComputerAction, ComputerActionType


def _optional_int(action_payload: ComputerActionPayload, key: str) -> int | None:
    if key in action_payload:
        return action_payload[key]
    return None


def map_openai_action(action_payload: ComputerActionPayload) -> ComputerAction:
    action_type = action_payload["type"]
    if action_type == "click":
        return ComputerAction(
            type=ComputerActionType.CLICK,
            action_id=new_action_id(),
            x=action_payload["x"],
            y=action_payload["y"],
            reason="OpenAI computer click",
        )
    if action_type == "double_click":
        return ComputerAction(
            type=ComputerActionType.DOUBLE_CLICK,
            action_id=new_action_id(),
            x=action_payload["x"],
            y=action_payload["y"],
            reason="OpenAI computer double click",
        )
    if action_type == "scroll":
        return ComputerAction(
            type=ComputerActionType.SCROLL,
            action_id=new_action_id(),
            x=_optional_int(action_payload, "x"),
            y=_optional_int(action_payload, "y"),
            scroll_x=_optional_int(action_payload, "scroll_x"),
            scroll_y=_optional_int(action_payload, "scroll_y"),
            reason="OpenAI computer scroll",
        )
    if action_type == "type":
        return ComputerAction(
            type=ComputerActionType.TYPE,
            action_id=new_action_id(),
            text=action_payload["text"],
            reason="OpenAI computer type",
        )
    if action_type == "wait":
        return ComputerAction(
            type=ComputerActionType.WAIT,
            action_id=new_action_id(),
            reason="OpenAI computer wait",
        )
    if action_type == "keypress":
        return ComputerAction(
            type=ComputerActionType.KEYPRESS,
            action_id=new_action_id(),
            key=action_payload["key"],
            reason="OpenAI computer keypress",
        )
    if action_type == "move":
        return ComputerAction(
            type=ComputerActionType.MOVE,
            action_id=new_action_id(),
            x=action_payload["x"],
            y=action_payload["y"],
            reason="OpenAI computer move",
        )
    if action_type == "screenshot":
        return ComputerAction(
            type=ComputerActionType.SCREENSHOT,
            action_id=new_action_id(),
            reason="OpenAI computer screenshot request",
        )
    if action_type == "drag":
        return ComputerAction(
            type=ComputerActionType.DRAG,
            action_id=new_action_id(),
            x=action_payload["x"],
            y=action_payload["y"],
            reason="OpenAI computer drag",
        )
    raise UnsupportedComputerActionError(f"Unsupported OpenAI computer action type: {action_type}")


def map_computer_call(
    response_id: str,
    call_payload: ComputerCallPayload,
) -> ComputerTurn:
    actions = [map_openai_action(action) for action in call_payload["actions"]]
    return ComputerTurn(
        response_id=ComputerResponseId(response_id),
        call_id=ComputerCallId(call_payload["call_id"]),
        actions=actions,
        completed=False,
        message="OpenAI computer returned actions",
    )
