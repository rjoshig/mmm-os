"""LLM client abstraction with OpenAI and Anthropic backends (ADR-008).

Handlers depend on the ``LLMClient`` protocol so a fake can be injected in tests.
The concrete backends lazily import their SDKs (optional ``mmm-os[llm]`` deps), so
the core imports and runs without them. The factory refuses to build a client
while the LLM is disabled.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mmm_os.ai.config import LLMConfig, resolve_provider
from mmm_os.ai.errors import LLMDisabledError, LLMError


@runtime_checkable
class LLMClient(Protocol):
    """A minimal chat-completion interface over an LLM provider."""

    def complete(self, *, system: str, user: str) -> str:
        """Return the model's text completion for a system + user prompt."""
        ...


class OpenAIClient:
    """LLM client backed by the OpenAI API (and OpenAI-compatible endpoints)."""

    def __init__(self, config: LLMConfig) -> None:
        """Build the OpenAI client from config (SDK imported lazily)."""
        self._config = config
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised only without the SDK
            raise LLMError("openai package not installed; install 'mmm-os[llm]'") from exc
        self._client = OpenAI(
            api_key=config.api_key, base_url=config.base_url, timeout=config.timeout_seconds
        )

    def complete(self, *, system: str, user: str) -> str:
        """Return a chat completion using the configured model."""
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )
        return str(response.choices[0].message.content or "")


class AnthropicClient:
    """LLM client backed by the Anthropic SDK."""

    def __init__(self, config: LLMConfig) -> None:
        """Build the Anthropic client from config (SDK imported lazily)."""
        self._config = config
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the SDK
            raise LLMError("anthropic package not installed; install 'mmm-os[llm]'") from exc
        self._client = anthropic.Anthropic(api_key=config.api_key, timeout=config.timeout_seconds)

    def complete(self, *, system: str, user: str) -> str:
        """Return a message completion using the configured model."""
        message = self._client.messages.create(
            model=self._config.model,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )
        parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
        return str("".join(parts))


def build_llm_client(config: LLMConfig) -> LLMClient:
    """Build the configured LLM client.

    Args:
        config: The LLM config.

    Returns:
        An ``LLMClient`` for the resolved provider.

    Raises:
        LLMDisabledError: If the LLM is disabled (the default).
        LLMConfigError: If the provider cannot be resolved.
    """
    if not config.enabled:
        raise LLMDisabledError("LLM is disabled; enable via LLM_ENABLED / config file")
    provider = resolve_provider(config)
    if provider == "openai":
        return OpenAIClient(config)
    return AnthropicClient(config)
