from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TzafonTaskRequest(BaseModel):
    agent_type: Literal["harness"] = "harness"
    instruction: str
    stream_delta: Literal[True] = True
    mode: str


class TzafonStreamSummary(BaseModel):
    lines: list[str] = Field(default_factory=list)

