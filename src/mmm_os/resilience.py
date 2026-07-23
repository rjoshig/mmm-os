"""Resilience utilities: retry-with-backoff and a circuit breaker (Phase 07.2).

Complements the queue's built-in bounded retries + dead-lettering
(:mod:`mmm_os.workers.queue`, CC-6). ``retry`` wraps a single flaky call;
``CircuitBreaker`` stops hammering a dependency that is failing (partner API, LLM,
storage) and lets it recover (P7.2-5). Sleep/clock are injectable so behaviour is
deterministic under test.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def backoff_delays(retries: int, *, base: float, cap: float) -> list[float]:
    """Return the exponential backoff delays for ``retries`` attempts (capped)."""
    return [min(cap, base * (2**i)) for i in range(retries)]


def retry(
    fn: Callable[[], T],
    *,
    retries: int = 2,
    base_delay: float = 0.0,
    max_delay: float = 30.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleeper: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``fn``, retrying on ``exceptions`` with exponential backoff.

    Args:
        fn: The zero-arg callable to run.
        retries: Retries after the first attempt (total attempts = retries + 1).
        base_delay: Base backoff seconds (0 disables sleeping).
        max_delay: Ceiling for any single backoff.
        exceptions: Exception types that trigger a retry.
        sleeper: Sleep function (injectable for tests).

    Returns:
        The successful result.

    Raises:
        The last exception if all attempts fail.
    """
    attempt = 0
    while True:
        try:
            return fn()
        except exceptions:
            if attempt >= retries:
                raise
            delay = min(max_delay, base_delay * (2**attempt))
            if delay > 0:
                sleeper(delay)
            attempt += 1


class CircuitOpenError(RuntimeError):
    """Raised when a call is attempted while the circuit is open."""


class CircuitBreaker:
    """A simple circuit breaker: closed → open (on failures) → half-open → closed.

    Args:
        failure_threshold: Consecutive failures that trip the breaker open.
        reset_timeout: Seconds the breaker stays open before a half-open trial.
        clock: Monotonic clock (injectable for tests).
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialise a closed breaker with no recorded failures."""
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        """Return ``"closed"``, ``"open"``, or ``"half_open"``."""
        if self._opened_at is None:
            return "closed"
        if self._clock() - self._opened_at >= self.reset_timeout:
            return "half_open"
        return "open"

    def call(self, fn: Callable[[], T]) -> T:
        """Run ``fn`` if the breaker allows it; record success/failure.

        Raises:
            CircuitOpenError: If the breaker is open.
        """
        if self.state == "open":
            raise CircuitOpenError("circuit is open")
        try:
            result = fn()
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def _on_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold or self.state == "half_open":
            self._opened_at = self._clock()
