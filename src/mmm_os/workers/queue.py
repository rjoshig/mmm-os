"""Task queue abstraction with a per-tenant-fair in-process backend (Phase 7).

The pipeline runs work as background **tasks** rather than inline (P7-1). This
module defines the ``TaskQueue`` contract plus an ``EagerTaskQueue`` — an
in-process backend that provides **per-tenant round-robin fairness** (P7-3),
**retry with bounded attempts** and a **dead-letter queue** (P7-5, CC-6) — so the
orchestration, fairness, and retry semantics are real and testable without
external infrastructure.

Production swaps in a **Celery + Redis** backend (ADR-007) behind this same
contract: autoscaling workers, a Redis broker/result backend, and the same
per-tenant fairness + retry policy. Callers depend on ``TaskQueue``, never on a
concrete backend.
"""

from __future__ import annotations

import abc
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Task:
    """A unit of work bound to a tenant (for fair scheduling).

    Attributes:
        tenant_id: The owning tenant — the fairness key.
        run: The callable performing the work (no args; close over context).
        name: A human-readable label for observability/logs.
        max_retries: Retries after the first attempt before dead-lettering.
        attempts: Attempts made so far (managed by the queue).
    """

    tenant_id: uuid.UUID
    run: Callable[[], None]
    name: str = "task"
    max_retries: int = 2
    attempts: int = 0


@dataclass
class DeadLetter:
    """A task that exhausted its retries, with the last error (P7-5)."""

    task: Task
    error: str


@dataclass
class DrainResult:
    """Outcome of draining the queue."""

    processed: int = 0
    retried: int = 0
    dead_letters: list[DeadLetter] = field(default_factory=list)


class TaskQueue(abc.ABC):
    """Abstract queue: enqueue tenant-bound tasks; a worker runs them."""

    @abc.abstractmethod
    def enqueue(self, task: Task) -> None:
        """Add ``task`` to the queue."""

    @abc.abstractmethod
    def drain(self) -> DrainResult:
        """Run all queued tasks to completion (fairly), returning the outcome."""


class EagerTaskQueue(TaskQueue):
    """In-process queue: per-tenant round-robin, bounded retries, dead-lettering.

    Not for production (single process, no durability). It exists so batch
    fan-out, fairness, and retry behaviour are real and unit-testable; the Celery
    backend (ADR-007) is the production implementation of the same contract.
    """

    def __init__(self) -> None:
        """Initialise empty per-tenant queues and rotation order."""
        self._queues: dict[uuid.UUID, deque[Task]] = {}
        self._order: deque[uuid.UUID] = deque()

    def enqueue(self, task: Task) -> None:
        """Add ``task`` to its tenant's queue, registering the tenant for rotation."""
        if task.tenant_id not in self._queues:
            self._queues[task.tenant_id] = deque()
            self._order.append(task.tenant_id)
        self._queues[task.tenant_id].append(task)

    def _next_tenant(self) -> uuid.UUID | None:
        """Return the next tenant with pending work (round-robin), or ``None``."""
        for _ in range(len(self._order)):
            tenant_id = self._order[0]
            self._order.rotate(-1)
            if self._queues.get(tenant_id):
                return tenant_id
        return None

    def drain(self) -> DrainResult:
        """Process tasks one per tenant in rotation until all queues are empty.

        A task that raises is retried (re-enqueued to the back of its tenant's
        queue) until ``max_retries`` is exceeded, then dead-lettered — never lost
        and never left to spin forever (P7-5).
        """
        result = DrainResult()
        while True:
            tenant_id = self._next_tenant()
            if tenant_id is None:
                break
            task = self._queues[tenant_id].popleft()
            task.attempts += 1
            try:
                task.run()
                result.processed += 1
            except Exception as exc:  # noqa: BLE001 - queue must survive task failure
                if task.attempts <= task.max_retries:
                    result.retried += 1
                    self._queues[tenant_id].append(task)
                else:
                    result.dead_letters.append(DeadLetter(task=task, error=str(exc)))
        return result
