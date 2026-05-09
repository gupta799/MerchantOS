from __future__ import annotations

from app.models import BrowserDomSummary, BrowserObservation, Viewport
from app.privacy import sanitize_observation_for_computer_use


def test_privacy_hook_returns_observation_for_mvp() -> None:
    observation = BrowserObservation(
        url="http://localhost:5173/agent-session/sess_123",
        screenshot="data:image/png;base64,",
        viewport=Viewport(width=800, height=600),
        dom_summary=BrowserDomSummary(),
    )
    assert sanitize_observation_for_computer_use(observation) == observation

