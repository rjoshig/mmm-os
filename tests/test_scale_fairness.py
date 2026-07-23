"""Scale + fairness proofs (Phase 12 — noisy-neighbor + concurrency).

Fast, deterministic checks of the mechanisms the load plan relies on: per-tenant
round-robin fairness (one heavy tenant cannot starve others, ADR-007 / P12-3) and
tenant isolation under concurrent ingest (CC-1 holds when many tenants work at once).
The full-scale harness lives in ``loadtest/`` and runs against a stage environment.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from mmm_os.workers import EagerTaskQueue, Task


def test_per_tenant_fairness_no_starvation() -> None:
    """A tenant flooding the queue does not delay other tenants' first task."""
    queue = EagerTaskQueue()
    processed: list[uuid.UUID] = []

    heavy = uuid.uuid4()
    light = [uuid.uuid4() for _ in range(4)]

    # Heavy tenant enqueues 100 tasks; each light tenant enqueues 1 — all before drain.
    for _ in range(100):
        queue.enqueue(Task(tenant_id=heavy, run=lambda t=heavy: processed.append(t)))
    for lid in light:
        queue.enqueue(Task(tenant_id=lid, run=lambda t=lid: processed.append(t)))

    result = queue.drain()
    assert result.processed == 104

    # Round-robin means each light tenant's single task completes within the first
    # rotation (one task per tenant), never starved behind the heavy backlog.
    first_rotation = processed[: len(light) + 1]
    for lid in light:
        assert lid in first_rotation, "a light tenant was starved by the heavy tenant"


def test_concurrent_ingest_keeps_tenants_isolated(client: TestClient) -> None:
    """Many tenants ingesting concurrently each see only their own file (CC-1)."""
    tenants = [uuid.uuid4() for _ in range(12)]

    def ingest(tid: uuid.UUID) -> tuple[uuid.UUID, int, str]:
        content = f"date,spend\n2026-01-01,{tid.int % 1000}\n".encode()
        up = client.post(
            f"/api/v1/tenants/{tid}/files",
            files={"upload": (f"{tid}.csv", content, "text/csv")},
        )
        assert up.status_code == 201, up.text
        client.post(f"/api/v1/tenants/{tid}/files/{up.json()['file']['id']}/process")
        listing = client.get(f"/api/v1/tenants/{tid}/files")
        names = [f["file"]["filename"] for f in listing.json()]
        return tid, len(names), names[0] if names else ""

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(ingest, tenants))

    for tid, count, name in results:
        assert count == 1, f"tenant {tid} saw {count} files (cross-tenant leak?)"
        assert name == f"{tid}.csv"
