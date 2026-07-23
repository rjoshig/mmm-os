"""Tests for the Phase-7 task queue + batch orchestration."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mmm_os.models import File
from mmm_os.storage.local import LocalObjectStorage
from mmm_os.workers import EagerTaskQueue, Task, enqueue_batch


def test_per_tenant_round_robin_fairness() -> None:
    """Tasks run one-per-tenant in rotation so no tenant monopolises the worker."""
    order: list[str] = []
    t1, t2, t3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    q = EagerTaskQueue()
    for tid, label in [(t1, "a"), (t1, "a"), (t2, "b"), (t2, "b"), (t3, "c"), (t3, "c")]:
        q.enqueue(Task(tenant_id=tid, run=lambda label=label: order.append(label)))

    result = q.drain()
    assert result.processed == 6
    # Round-robin: a, b, c, a, b, c — not a, a, b, b, c, c.
    assert order == ["a", "b", "c", "a", "b", "c"]


def test_retry_then_succeed() -> None:
    """A transient failure is retried and then succeeds (no dead letter)."""
    calls = {"n": 0}

    def flaky() -> None:
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("transient")

    q = EagerTaskQueue()
    q.enqueue(Task(tenant_id=uuid.uuid4(), run=flaky, max_retries=2))
    result = q.drain()
    assert result.processed == 1
    assert result.retried == 1
    assert result.dead_letters == []


def test_dead_letter_after_exhausting_retries() -> None:
    """A permanently failing task is dead-lettered, not lost or looped forever."""

    def boom() -> None:
        raise ValueError("nope")

    q = EagerTaskQueue()
    q.enqueue(Task(tenant_id=uuid.uuid4(), run=boom, max_retries=1, name="boom"))
    result = q.drain()
    assert result.processed == 0
    assert len(result.dead_letters) == 1
    assert result.dead_letters[0].task.attempts == 2
    assert "nope" in result.dead_letters[0].error


def test_batch_is_idempotent(
    client: TestClient, engine: Engine, storage: LocalObjectStorage
) -> None:
    """A file already processed successfully is skipped on a re-run (CC-6)."""
    tenant_id = uuid.uuid4()
    up = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={"upload": ("d.csv", b"date,channel,spend\n2026-01-01,FB,10\n", "text/csv")},
    )
    file_id = up.json()["file"]["id"]
    client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")

    with Session(engine) as session:
        file = session.get(File, uuid.UUID(file_id))
        assert file is not None
        enqueued = enqueue_batch(EagerTaskQueue(), session, storage, [file])
        assert enqueued == 0  # already succeeded → skipped
