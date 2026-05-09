from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TzafonInputText(BaseModel):
    type: Literal["input_text"] = "input_text"
    text: str


class TzafonInputImage(BaseModel):
    type: Literal["input_image"] = "input_image"
    image_url: str
    detail: Literal["auto"] = "auto"


class TzafonUserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: list[TzafonInputText | TzafonInputImage]


class TzafonComputerCallOutputImage(BaseModel):
    type: Literal["input_image"] = "input_image"
    image_url: str
    detail: Literal["auto"] = "auto"


class TzafonComputerCallOutput(BaseModel):
    type: Literal["computer_call_output"] = "computer_call_output"
    call_id: str
    output: TzafonComputerCallOutputImage


class TzafonComputerTool(BaseModel):
    type: Literal["computer_use"] = "computer_use"
    display_width: int
    display_height: int
    environment: Literal["browser"] = "browser"


class TzafonResponsesRequest(BaseModel):
    model: str
    input: list[TzafonUserMessage] | list[TzafonComputerCallOutput]
    tools: list[TzafonComputerTool]
    instructions: str | None = None
    previous_response_id: str | None = None


class TzafonActionPayload(BaseModel):
    type: str
    x: int | None = None
    y: int | None = None
    text: str | None = None
    keys: list[str] | None = None
    key: str | None = None
    scroll_x: int | None = None
    scroll_y: int | None = None
    delta_x: int | None = None
    delta_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    url: str | None = None
    button: str | None = None
    status: str | None = None
    result: str | None = None


class TzafonOutputText(BaseModel):
    text: str | None = None


class TzafonOutputItem(BaseModel):
    type: str
    call_id: str | None = None
    action: TzafonActionPayload | None = None
    content: list[TzafonOutputText] = Field(default_factory=list)


class TzafonResponsesResponse(BaseModel):
    id: str
    output: list[TzafonOutputItem] = Field(default_factory=list)
