"""Structured logging context (Phase 07.1, CC-7).

Binds ``tenant_id`` / ``job_id`` (and other) fields to the current async context so
log lines and events carry them without threading arguments everywhere. Secret
values MUST NOT be bound here (CC-12).
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager

_context: contextvars.ContextVar[dict[str, str] | None] = contextvars.ContextVar(
    "log_context", default=None
)


def get_context() -> dict[str, str]:
    """Return a copy of the current logging context."""
    return dict(_context.get() or {})


@contextmanager
def log_context(**fields: str) -> Iterator[None]:
    """Bind ``fields`` onto the logging context for the duration of the block."""
    merged = {**get_context(), **{k: str(v) for k, v in fields.items()}}
    token = _context.set(merged)
    try:
        yield
    finally:
        _context.reset(token)


def context_str() -> str:
    """Render the current context as ``k=v`` pairs (for log line suffixes)."""
    return " ".join(f"{k}={v}" for k, v in sorted(get_context().items()))
