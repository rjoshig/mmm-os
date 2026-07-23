"""In-process metrics registry (Phase 07.1, CC-7).

A tiny, dependency-free metrics layer: labelled **counters** (throughput,
failures) and **observations** (latency/queue-depth samples). It defines the
platform metrics standard; a production deployment exports the same names to a
real backend (OpenTelemetry/Prometheus — OQ-07.1-1) behind this interface.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

_Labels = tuple[tuple[str, str], ...]


def _key(name: str, labels: dict[str, str]) -> tuple[str, _Labels]:
    return name, tuple(sorted(labels.items()))


class MetricsRegistry:
    """Thread-safe labelled counters + observations."""

    def __init__(self) -> None:
        """Initialise empty counter/observation maps and a lock."""
        self._counters: dict[tuple[str, _Labels], float] = {}
        self._observations: dict[tuple[str, _Labels], list[float]] = {}
        self._lock = threading.Lock()

    def increment(self, name: str, value: float = 1.0, **labels: str) -> None:
        """Add ``value`` to the counter ``name`` for the given labels."""
        with self._lock:
            key = _key(name, labels)
            self._counters[key] = self._counters.get(key, 0.0) + value

    def observe(self, name: str, value: float, **labels: str) -> None:
        """Record a sample ``value`` for the observation ``name``."""
        with self._lock:
            self._observations.setdefault(_key(name, labels), []).append(value)

    def counter(self, name: str, **labels: str) -> float:
        """Return the current counter value for ``name`` + labels."""
        with self._lock:
            return self._counters.get(_key(name, labels), 0.0)

    def observations(self, name: str, **labels: str) -> list[float]:
        """Return the recorded samples for ``name`` + labels."""
        with self._lock:
            return list(self._observations.get(_key(name, labels), []))

    def reset(self) -> None:
        """Clear all metrics (used by tests)."""
        with self._lock:
            self._counters.clear()
            self._observations.clear()


#: Process-wide default registry.
registry = MetricsRegistry()


@contextmanager
def timed(name: str, *, into: MetricsRegistry | None = None, **labels: str) -> Iterator[None]:
    """Observe the wall-clock duration (ms) of the block as ``name``."""
    target = into or registry
    start = perf_counter()
    try:
        yield
    finally:
        target.observe(name, (perf_counter() - start) * 1000.0, **labels)
