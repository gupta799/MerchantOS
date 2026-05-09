from __future__ import annotations

from app.models import BrowserObservation


def sanitize_observation_for_computer_use(observation: BrowserObservation) -> BrowserObservation:
    """Keep this explicit so production PII redaction has one obvious hook."""
    return observation

