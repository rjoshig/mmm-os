"""AI-layer error types."""

from __future__ import annotations


class LLMError(RuntimeError):
    """Base class for LLM-layer errors."""


class LLMDisabledError(LLMError):
    """Raised when the LLM is used while disabled (off by default)."""


class LLMConfigError(LLMError):
    """Raised when the LLM configuration is invalid or a provider can't be resolved."""


class LLMResponseError(LLMError):
    """Raised when the model's response cannot be parsed into the expected shape."""


class LLMBudgetExceededError(LLMError):
    """Raised when a tenant's LLM usage would exceed its configured budget (CC-13)."""
