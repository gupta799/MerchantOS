from __future__ import annotations

from typing import NotRequired, TypedDict

from app.computer.protocol import ComputerContinueRequest, ComputerStartRequest


class ComputerToolPayload(TypedDict):
    type: str


class ComputerScreenshotOutput(TypedDict):
    type: str
    image_url: str
    detail: str


class ComputerCallOutputPayload(TypedDict):
    type: str
    call_id: str
    output: ComputerScreenshotOutput


class StartInputImage(TypedDict):
    type: str
    image_url: str
    detail: str


class StartInputText(TypedDict):
    type: str
    text: str


class StartMessage(TypedDict):
    role: str
    content: list[StartInputText | StartInputImage]


class ComputerActionPayload(TypedDict):
    type: str
    x: NotRequired[int]
    y: NotRequired[int]
    text: NotRequired[str]
    scroll_x: NotRequired[int]
    scroll_y: NotRequired[int]
    key: NotRequired[str]


class ComputerCallPayload(TypedDict):
    type: str
    call_id: str
    actions: list[ComputerActionPayload]


def computer_tool_payload() -> list[ComputerToolPayload]:
    return [{"type": "computer"}]


def start_input_payload(request: ComputerStartRequest) -> list[StartMessage]:
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": request.goal,
                },
                {
                    "type": "input_image",
                    "image_url": request.observation.screenshot,
                    "detail": "original",
                },
            ],
        }
    ]


def continue_input_payload(request: ComputerContinueRequest) -> list[ComputerCallOutputPayload]:
    return [
        {
            "type": "computer_call_output",
            "call_id": str(request.call_id),
            "output": {
                "type": "computer_screenshot",
                "image_url": request.observation.screenshot,
                "detail": "original",
            },
        }
    ]

