"""Tests for the Phase-07.2 resilience utilities."""

from __future__ import annotations

import pytest

from mmm_os.resilience import CircuitBreaker, CircuitOpenError, backoff_delays, retry


def test_backoff_delays_capped() -> None:
    """Delays grow exponentially and are capped."""
    assert backoff_delays(4, base=1.0, cap=4.0) == [1.0, 2.0, 4.0, 4.0]


def test_retry_succeeds_after_transient_failures() -> None:
    """retry re-invokes until success without sleeping (base_delay=0)."""
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("boom")
        return "ok"

    assert retry(flaky, retries=3) == "ok"
    assert calls["n"] == 3


def test_retry_reraises_after_exhausting() -> None:
    """retry re-raises the last error once retries are exhausted."""
    slept: list[float] = []

    def always_fail() -> None:
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        retry(always_fail, retries=2, base_delay=1.0, sleeper=slept.append)
    assert slept == [1.0, 2.0]  # two backoff sleeps before the final failure


def test_circuit_breaker_opens_and_recovers() -> None:
    """The breaker trips open after N failures, then half-opens after the timeout."""
    now = {"t": 0.0}
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=10.0, clock=lambda: now["t"])

    def fail() -> None:
        raise RuntimeError("x")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(fail)
    assert cb.state == "open"

    # While open, calls are rejected without invoking fn.
    with pytest.raises(CircuitOpenError):
        cb.call(fail)

    # After the reset timeout it half-opens and a success closes it.
    now["t"] = 11.0
    assert cb.state == "half_open"
    assert cb.call(lambda: "recovered") == "recovered"
    assert cb.state == "closed"
