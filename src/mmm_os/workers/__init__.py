"""Async background workers (Phase 7).

A ``TaskQueue`` abstraction with an in-process, per-tenant-fair backend
(``EagerTaskQueue``) for dev/tests; production uses Celery + Redis behind the same
contract (ADR-007). ``orchestration`` fans a batch of files out into per-file
tasks, idempotently (CC-6).
"""

from mmm_os.workers.orchestration import already_succeeded, enqueue_batch, process_batch
from mmm_os.workers.queue import (
    DeadLetter,
    DrainResult,
    EagerTaskQueue,
    Task,
    TaskQueue,
)

__all__ = [
    "DeadLetter",
    "DrainResult",
    "EagerTaskQueue",
    "Task",
    "TaskQueue",
    "already_succeeded",
    "enqueue_batch",
    "process_batch",
]
