from __future__ import annotations

from app.errors import PolicyViolationError
from app.models import BrowserObservation, ComputerAction, ComputerActionType


DEFAULT_ALLOWED_ORIGIN_FRAGMENTS = (
    "localhost:5174",
    "127.0.0.1:5174",
    "localhost:5175",
    "127.0.0.1:5175",
    "localhost:5176",
    "127.0.0.1:5176",
    "localhost:5177",
    "127.0.0.1:5177",
    "localhost:5178",
    "127.0.0.1:5178",
    "localhost:5173",
    "127.0.0.1:5173",
)


class MerchantPolicy:
    def __init__(self, allowed_origin_fragments: tuple[str, ...] = ()) -> None:
        normalized_fragments = tuple(fragment for fragment in allowed_origin_fragments if fragment.strip() != "")
        self._allowed_origin_fragments = DEFAULT_ALLOWED_ORIGIN_FRAGMENTS + normalized_fragments

    def validate_action(self, action: ComputerAction, observation: BrowserObservation) -> None:
        self._validate_current_url(observation)
        if action.type in {ComputerActionType.TYPE, ComputerActionType.KEYPRESS}:
            text = action.text or action.key or ""
            self._validate_text_action(text)
        if action.type == ComputerActionType.CLICK:
            self._validate_click(action, observation)

    def _validate_current_url(self, observation: BrowserObservation) -> None:
        if not any(fragment in observation.url for fragment in self._allowed_origin_fragments):
            raise PolicyViolationError("Computer use is limited to the merchant storefront origin")

    def _validate_text_action(self, text: str) -> None:
        lowered = text.lower()
        forbidden = ("card", "cvv", "password", "place order", "pay now")
        if any(term in lowered for term in forbidden):
            raise PolicyViolationError("Payment or credential entry is blocked")
        digits = "".join(character for character in text if character.isdigit())
        if len(digits) >= 12:
            raise PolicyViolationError("Payment or credential entry is blocked")

    def _validate_click(self, action: ComputerAction, observation: BrowserObservation) -> None:
        if action.x is None or action.y is None:
            raise PolicyViolationError("Click action must include coordinates")
        if action.x < 0 or action.y < 0:
            raise PolicyViolationError("Click action coordinates must be positive")
        if action.x > observation.viewport.width or action.y > observation.viewport.height:
            raise PolicyViolationError("Click action must stay inside the visible merchant viewport")


merchant_policy = MerchantPolicy()


def merchant_policy_for_public_url(public_url: str | None) -> MerchantPolicy:
    if public_url is None:
        return merchant_policy
    if "{session_id}" in public_url:
        return MerchantPolicy((public_url.split("{session_id}")[0].rstrip("/"),))
    return MerchantPolicy((public_url.rstrip("/"),))
