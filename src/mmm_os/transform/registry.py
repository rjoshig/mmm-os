"""Operation registry for the transformation engine.

Operations are handlers registered by name. Adding a capability is adding a
handler (P3-2 extensibility) — the engine itself never changes. A handler takes
the current table, the rule, and a context, and returns the new table.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from mmm_os.canonical.models import Taxonomies
from mmm_os.transform.types import RuleSpec, Table


class TransformError(RuntimeError):
    """Base class for transformation errors."""


class UnknownOperationError(TransformError):
    """Raised when a rule names an operation with no registered handler."""


@dataclass
class RuleContext:
    """Ambient data available to operation handlers.

    Attributes:
        taxonomies: Loaded taxonomies for value harmonisation (``map_value``).
    """

    taxonomies: Taxonomies | None = None


Handler = Callable[[Table, RuleSpec, RuleContext], Table]

_REGISTRY: dict[str, Handler] = {}


def register(name: str) -> Callable[[Handler], Handler]:
    """Register a handler under an operation name.

    Args:
        name: The operation name.

    Returns:
        A decorator that registers and returns the handler.
    """

    def decorator(handler: Handler) -> Handler:
        _REGISTRY[name] = handler
        return handler

    return decorator


def get_handler(name: str) -> Handler:
    """Return the handler for an operation name.

    Args:
        name: The operation name.

    Returns:
        The registered handler.

    Raises:
        UnknownOperationError: If no handler is registered under ``name``.
    """
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise UnknownOperationError(f"unknown operation: {name!r}") from exc


def registered_operations() -> list[str]:
    """Return the sorted list of registered operation names."""
    return sorted(_REGISTRY)
