from __future__ import annotations

from app.browser.kernel_driver import kernel_target_url
from app.config import AppSettings


def test_kernel_target_url_defaults_to_local_tunnel_storefront() -> None:
    settings = AppSettings(
        _env_file=None,
        KERNEL_API_KEY="ker-test",
        AGENTREADY_BROWSER_ENV="kernel",
        AGENTREADY_PUBLIC_STOREFRONT_URL=None,
        AGENTREADY_KERNEL_LOCAL_STOREFRONT_URL="http://localhost:5173",
        AGENTREADY_HARNESS_MODE="scripted",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )

    assert kernel_target_url(settings, "sess_123") == "http://localhost:5173/agent-session/sess_123"


def test_kernel_target_url_prefers_public_storefront_when_configured() -> None:
    settings = AppSettings(
        _env_file=None,
        KERNEL_API_KEY="ker-test",
        AGENTREADY_BROWSER_ENV="kernel",
        AGENTREADY_PUBLIC_STOREFRONT_URL="https://merchant.example/session/{session_id}",
        AGENTREADY_KERNEL_LOCAL_STOREFRONT_URL="http://localhost:5173",
        AGENTREADY_HARNESS_MODE="scripted",
        AGENTREADY_COMPUTER_CLIENT="scripted",
    )

    assert kernel_target_url(settings, "sess_123") == "https://merchant.example/session/sess_123"
