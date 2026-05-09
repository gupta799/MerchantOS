from __future__ import annotations


class AgentReadyError(Exception):
    """Base application error."""


class ConfigError(AgentReadyError):
    """Raised when required runtime configuration is invalid."""


class NotFoundError(AgentReadyError):
    """Raised when a session or domain entity does not exist."""


class GuideChannelError(AgentReadyError):
    """Raised when the browser SDK channel is unavailable or invalid."""


class BrowserEnvironmentError(AgentReadyError):
    """Raised when a managed browser environment fails."""


class PolicyViolationError(AgentReadyError):
    """Raised when a computer action violates merchant policy."""


class UnsupportedComputerActionError(AgentReadyError):
    """Raised when a provider returns an unsupported computer action."""
