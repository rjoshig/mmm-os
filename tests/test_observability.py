"""Tests for the Phase-07.1 observability primitives."""

from __future__ import annotations

from mmm_os.observability import MetricsRegistry, context_str, get_context, log_context, timed


def test_counters_and_labels() -> None:
    """Counters accumulate per label set independently."""
    reg = MetricsRegistry()
    reg.increment("jobs.processed", stage="ingest")
    reg.increment("jobs.processed", 2, stage="ingest")
    reg.increment("jobs.processed", stage="map")
    assert reg.counter("jobs.processed", stage="ingest") == 3.0
    assert reg.counter("jobs.processed", stage="map") == 1.0
    assert reg.counter("jobs.processed") == 0.0  # different (empty) label set


def test_observations_and_timed() -> None:
    """observe records samples; timed records one duration sample (ms)."""
    reg = MetricsRegistry()
    reg.observe("latency", 12.5, stage="map")
    with timed("latency", into=reg, stage="map"):
        pass
    samples = reg.observations("latency", stage="map")
    assert len(samples) == 2
    assert samples[0] == 12.5
    assert samples[1] >= 0.0


def test_log_context_binds_and_resets() -> None:
    """log_context binds fields within the block and restores on exit."""
    assert get_context() == {}
    with log_context(tenant_id="t1", job_id="j1"):
        ctx = get_context()
        assert ctx == {"tenant_id": "t1", "job_id": "j1"}
        assert "tenant_id=t1" in context_str()
        with log_context(job_id="j2"):
            assert get_context()["job_id"] == "j2"
            assert get_context()["tenant_id"] == "t1"  # inherited
    assert get_context() == {}
