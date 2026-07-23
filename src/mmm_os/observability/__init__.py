"""Observability (Phase 07.1, CC-7).

The platform standard for metrics + structured context. Defined here and
instrumented incrementally from Phase 1 onward; a production deployment exports
the same signals to a real metrics/tracing backend behind these interfaces.
"""

from mmm_os.observability.context import context_str, get_context, log_context
from mmm_os.observability.metrics import MetricsRegistry, registry, timed

__all__ = [
    "MetricsRegistry",
    "context_str",
    "get_context",
    "log_context",
    "registry",
    "timed",
]

# Metric name constants (stable across the codebase).
JOBS_PROCESSED = "jobs.processed"
JOBS_RETRIED = "jobs.retried"
JOBS_DEAD_LETTERED = "jobs.dead_lettered"
BATCH_QUEUE_DEPTH = "batch.queue_depth"
