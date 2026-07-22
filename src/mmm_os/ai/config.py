"""LLM configuration: env + optional JSON file, provider auto-inference (ADR-008).

The LLM is **off by default**. Configuration is read from an optional JSON file
(``LLM_CONFIG_FILE``) and overlaid with ``LLM_*`` environment variables (env
wins). Switching provider/model is therefore a config-only change; with
``provider = "auto"`` the provider is inferred from the model name.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field

from mmm_os.ai.errors import LLMConfigError

_OPENAI_PREFIXES = ("gpt", "o1", "o3", "o4", "chatgpt", "text-")
_ANTHROPIC_PREFIXES = ("claude",)

_ENV_MAP = {
    "enabled": "LLM_ENABLED",
    "provider": "LLM_PROVIDER",
    "model": "LLM_MODEL",
    "api_key": "LLM_API_KEY",
    "base_url": "LLM_BASE_URL",
    "temperature": "LLM_TEMPERATURE",
    "max_tokens": "LLM_MAX_TOKENS",
    "timeout_seconds": "LLM_TIMEOUT_SECONDS",
    "confidence_autofill": "LLM_CONFIDENCE_AUTOFILL",
    "confidence_flag": "LLM_CONFIDENCE_FLAG",
}


class LLMConfig(BaseModel):
    """LLM settings.

    Attributes:
        enabled: Master switch — the LLM is off unless this is true.
        provider: ``auto`` | ``openai`` | ``anthropic``.
        model: The model name (e.g. ``gpt-4o-mini`` or ``claude-...``).
        api_key: API key; falls back to provider-specific env if unset.
        base_url: Optional base URL (OpenAI-compatible endpoints).
        temperature: Sampling temperature.
        max_tokens: Max output tokens.
        timeout_seconds: Request timeout.
        confidence_autofill: At/above this confidence, a suggestion is auto-fill-as-pending.
        confidence_flag: Below this confidence, a suggestion is low/needs-review.
    """

    enabled: bool = False
    provider: str = "auto"
    model: str = ""
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_seconds: float = 60.0
    confidence_autofill: float = Field(default=0.85, ge=0.0, le=1.0)
    confidence_flag: float = Field(default=0.5, ge=0.0, le=1.0)


def resolve_provider(config: LLMConfig, *, strict: bool = True) -> str:
    """Resolve the concrete provider for a config.

    Args:
        config: The LLM config.
        strict: If true, raise when the provider cannot be resolved; otherwise
            return ``"unknown"``.

    Returns:
        ``"openai"`` or ``"anthropic"`` (or ``"unknown"`` when not strict).

    Raises:
        LLMConfigError: If strict and the provider can't be resolved.
    """
    provider = config.provider.strip().lower()
    if provider in ("openai", "anthropic"):
        return provider
    if provider == "auto":
        model = config.model.strip().lower()
        if model.startswith(_OPENAI_PREFIXES):
            return "openai"
        if model.startswith(_ANTHROPIC_PREFIXES):
            return "anthropic"
    if strict:
        raise LLMConfigError(
            f"cannot resolve provider (provider={config.provider!r}, model={config.model!r})"
        )
    return "unknown"


def _env_overrides() -> dict[str, str]:
    return {key: os.environ[env] for key, env in _ENV_MAP.items() if env in os.environ}


def load_llm_config(config_path: str | None = None) -> LLMConfig:
    """Load the LLM config from an optional JSON file overlaid with env vars.

    Args:
        config_path: Explicit JSON config path; otherwise ``LLM_CONFIG_FILE``.

    Returns:
        The resolved ``LLMConfig`` (env overrides JSON; provider-specific API key
        filled from ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` when unset).

    Raises:
        LLMConfigError: If the JSON file exists but is invalid.
    """
    data: dict[str, object] = {}
    path = config_path or os.getenv("LLM_CONFIG_FILE")
    if path and Path(path).is_file():
        try:
            loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LLMConfigError(f"invalid LLM config file {path!r}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise LLMConfigError(f"LLM config file {path!r} must contain a JSON object")
        data.update(loaded)
    data.update(_env_overrides())

    config = LLMConfig.model_validate(data)
    if config.api_key is None:
        provider = resolve_provider(config, strict=False)
        if provider == "openai":
            config.api_key = os.getenv("OPENAI_API_KEY")
        elif provider == "anthropic":
            config.api_key = os.getenv("ANTHROPIC_API_KEY")
    return config
