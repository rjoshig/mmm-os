"""In-process LLM response cache (Phase 05.1 cost reduction).

Identical suggestion prompts (same model + system + user) reuse a cached response
instead of re-calling the provider. Process-local and bounded; a production
deployment can swap a shared cache behind ``get``/``put``.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict

_MAX_ENTRIES = 512
_cache: OrderedDict[str, str] = OrderedDict()


def cache_key(model: str, system: str, user: str) -> str:
    """Return a stable cache key for a completion request."""
    digest = hashlib.sha256(f"{model}\x00{system}\x00{user}".encode()).hexdigest()
    return digest


def get(key: str) -> str | None:
    """Return the cached completion for ``key`` (LRU touch), or ``None``."""
    if key not in _cache:
        return None
    _cache.move_to_end(key)
    return _cache[key]


def put(key: str, value: str) -> None:
    """Store ``value`` under ``key``, evicting the oldest entry past the cap."""
    _cache[key] = value
    _cache.move_to_end(key)
    while len(_cache) > _MAX_ENTRIES:
        _cache.popitem(last=False)


def clear() -> None:
    """Clear the cache (used by tests)."""
    _cache.clear()
