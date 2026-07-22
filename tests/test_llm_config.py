"""Tests for the LLM config, provider inference, and client factory (05.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mmm_os.ai.client import AnthropicClient, OpenAIClient, build_llm_client
from mmm_os.ai.config import LLMConfig, load_llm_config, resolve_provider
from mmm_os.ai.errors import LLMConfigError, LLMDisabledError

_LLM_ENV = [
    "LLM_ENABLED",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_CONFIG_FILE",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
]


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a clean LLM environment for each test."""
    for name in _LLM_ENV:
        monkeypatch.delenv(name, raising=False)


def test_disabled_by_default() -> None:
    """With no config the LLM is disabled."""
    assert load_llm_config().enabled is False


def test_provider_inference_from_model() -> None:
    """provider=auto infers OpenAI for gpt* and Anthropic for claude*."""
    assert resolve_provider(LLMConfig(model="gpt-4o-mini")) == "openai"
    assert resolve_provider(LLMConfig(model="o3-mini")) == "openai"
    assert resolve_provider(LLMConfig(model="claude-sonnet-5")) == "anthropic"


def test_explicit_provider_wins() -> None:
    """An explicit provider overrides model-based inference."""
    assert resolve_provider(LLMConfig(provider="anthropic", model="gpt-4o")) == "anthropic"


def test_unresolvable_provider_raises() -> None:
    """An unknown model with provider=auto cannot be resolved."""
    with pytest.raises(LLMConfigError):
        resolve_provider(LLMConfig(model="mystery-model"))


def test_env_enables_and_selects_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env vars enable the LLM and select the model/provider."""
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    config = load_llm_config()
    assert config.enabled is True
    assert resolve_provider(config) == "openai"


def test_json_config_loaded_and_env_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A JSON config is honoured; env overrides it."""
    path = tmp_path / "llm.json"
    path.write_text(json.dumps({"enabled": True, "model": "claude-sonnet-5"}))
    monkeypatch.setenv("LLM_CONFIG_FILE", str(path))
    assert resolve_provider(load_llm_config()) == "anthropic"

    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")  # env overrides JSON
    assert resolve_provider(load_llm_config()) == "openai"


def test_api_key_falls_back_to_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The API key falls back to the provider-specific env var."""
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert load_llm_config().api_key == "sk-test"


def test_factory_refuses_when_disabled() -> None:
    """The client factory refuses to build while disabled."""
    with pytest.raises(LLMDisabledError):
        build_llm_client(LLMConfig(enabled=False, model="gpt-4o-mini"))


def test_factory_selects_backend_by_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """When enabled, the factory returns the right backend by model/provider.

    The concrete client is only built if its SDK is installed; otherwise building
    raises a clear LLMError (SDKs are optional). We assert the selected class.
    """
    from mmm_os.ai.errors import LLMError

    for model, expected in [("gpt-4o-mini", OpenAIClient), ("claude-sonnet-5", AnthropicClient)]:
        config = LLMConfig(enabled=True, model=model)
        try:
            client = build_llm_client(config)
        except LLMError:
            # SDK not installed in this environment — acceptable; selection logic
            # is covered by resolve_provider tests above.
            continue
        assert isinstance(client, expected)
