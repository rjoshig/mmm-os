"""Metering + budget-enforcing LLM client wrapper (Phase 05.1, CC-13).

Wraps any :class:`~mmm_os.ai.client.LLMClient` so every call is (a) checked against
the tenant's budget before spending, (b) optionally served from the response cache,
and (c) recorded in the ``llm_usage`` ledger. Handlers are unchanged — they still
depend on the ``LLMClient`` protocol.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from mmm_os.ai import cache
from mmm_os.ai.budget import usage_snapshot
from mmm_os.ai.client import LLMClient
from mmm_os.ai.errors import LLMBudgetExceededError
from mmm_os.core.config import Settings
from mmm_os.models import LlmUsage


def estimate_tokens(text: str) -> int:
    """Estimate token count without a tokenizer dependency (~4 chars/token)."""
    return max(1, len(text) // 4)


class MeteringLLMClient:
    """An ``LLMClient`` that enforces budgets, caches, and records usage."""

    def __init__(
        self,
        inner: LLMClient,
        *,
        session: Session,
        tenant_id: uuid.UUID,
        model: str,
        settings: Settings,
    ) -> None:
        """Bind the wrapper to a tenant's session + budget context."""
        self._inner = inner
        self._session = session
        self._tenant_id = tenant_id
        self._model = model
        self._settings = settings

    def complete(self, *, system: str, user: str) -> str:
        """Return a completion, enforcing budget + cache and recording usage.

        Raises:
            LLMBudgetExceededError: If the tenant is already over its daily cap.
        """
        snapshot = usage_snapshot(self._session, self._tenant_id, self._settings)
        if snapshot.over_budget:
            raise LLMBudgetExceededError(
                f"tenant LLM budget exceeded (calls={snapshot.calls}/{snapshot.call_cap}, "
                f"tokens={snapshot.tokens}/{snapshot.token_cap})"
            )

        key = cache.cache_key(self._model, system, user)
        if self._settings.llm_cache_enabled and (cached := cache.get(key)) is not None:
            self._record(system, cached, cached_hit=True)
            return cached

        result = self._inner.complete(system=system, user=user)
        if self._settings.llm_cache_enabled:
            cache.put(key, result)
        self._record(system + user, result, cached_hit=False)
        return result

    def _record(self, prompt: str, completion: str, *, cached_hit: bool) -> None:
        self._session.add(
            LlmUsage(
                tenant_id=self._tenant_id,
                model=self._model,
                prompt_tokens=estimate_tokens(prompt),
                completion_tokens=estimate_tokens(completion),
                cached=cached_hit,
            )
        )
        self._session.flush()
