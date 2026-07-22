"""AI suggestion layer: config-driven LLM client + human-ratified suggestions [Phase 5]."""

from mmm_os.ai.client import (
    AnthropicClient,
    LLMClient,
    OpenAIClient,
    build_llm_client,
)
from mmm_os.ai.config import LLMConfig, load_llm_config, resolve_provider
from mmm_os.ai.errors import (
    LLMConfigError,
    LLMDisabledError,
    LLMError,
    LLMResponseError,
)

__all__ = [
    "AnthropicClient",
    "LLMClient",
    "LLMConfig",
    "LLMConfigError",
    "LLMDisabledError",
    "LLMError",
    "LLMResponseError",
    "OpenAIClient",
    "build_llm_client",
    "load_llm_config",
    "resolve_provider",
]
