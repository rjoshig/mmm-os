"""Load / scale harness (Phase 12).

Drives the ingest→process pipeline for many tenants concurrently and reports
throughput + latency percentiles. Runs in-process against a fresh SQLite database
by default (a self-contained proof), or against a live server via ``--base-url``.

Scaled proof (default, in-process SQLite)::

    uv run python loadtest/run_load.py --tenants 50 --files 3 --concurrency 16

Against a running stage server::

    uv run python loadtest/run_load.py --base-url http://localhost:8000 \
        --tenants 200 --files 20 --concurrency 64

This is the executable counterpart to ``loadtest/PLAN.md`` (scenarios + SLAs).
"""

from __future__ import annotations

import argparse
import statistics
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import mkdtemp


@dataclass
class Sample:
    """One unit of work's timing + outcome."""

    stage: str
    seconds: float
    ok: bool


@dataclass
class Report:
    """Collected samples with percentile helpers."""

    samples: list[Sample] = field(default_factory=list)

    def add(self, stage: str, seconds: float, ok: bool) -> None:
        """Record one timing sample for a stage."""
        self.samples.append(Sample(stage, seconds, ok))

    def _pct(self, values: list[float], p: float) -> float:
        """Return the p-th percentile of ``values`` (nearest-rank)."""
        if not values:
            return 0.0
        ordered = sorted(values)
        k = min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))
        return ordered[k]

    def summary(self, stage: str) -> str:
        """Return a one-line p50/p95/p99 + mean summary for a stage."""
        vals = [s.seconds for s in self.samples if s.stage == stage and s.ok]
        fails = sum(1 for s in self.samples if s.stage == stage and not s.ok)
        if not vals:
            return f"{stage:10s} n=0 fails={fails}"
        return (
            f"{stage:10s} n={len(vals):5d} fails={fails:3d} "
            f"p50={self._pct(vals, 50) * 1000:7.1f}ms "
            f"p95={self._pct(vals, 95) * 1000:7.1f}ms "
            f"p99={self._pct(vals, 99) * 1000:7.1f}ms "
            f"mean={statistics.mean(vals) * 1000:7.1f}ms"
        )


def _make_inprocess_client() -> tuple[object, Callable[[], None]]:
    """Build a TestClient against a fresh SQLite DB + temp storage/secrets."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from mmm_os.api.deps import get_secret_store_dep, get_storage
    from mmm_os.api.main import app
    from mmm_os.db.base import Base
    from mmm_os.db.session import get_control_session, get_session
    from mmm_os.secrets.local import LocalEncryptedSecretStore
    from mmm_os.storage.local import LocalObjectStorage

    tmp = Path(mkdtemp())
    engine = create_engine(
        f"sqlite:///{tmp / 'load.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    make = sessionmaker(bind=engine)

    def override() -> object:
        session = make()
        try:
            yield session
        finally:
            session.close()

    storage = LocalObjectStorage(tmp / "storage")
    secrets = LocalEncryptedSecretStore(tmp / "secrets", b"load-key")
    app.dependency_overrides[get_session] = override
    app.dependency_overrides[get_control_session] = override
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_secret_store_dep] = lambda: secrets
    client = TestClient(app)

    def close() -> None:
        app.dependency_overrides.clear()
        client.close()

    return client, close


def run(tenants: int, files: int, concurrency: int, base_url: str | None) -> Report:
    """Drive ``tenants`` × ``files`` ingest→process cycles and collect timings."""
    report = Report()

    def close() -> None:
        """Default no-op teardown (overridden for the in-process client)."""

    if base_url:
        import httpx

        client = httpx.Client(base_url=base_url, timeout=60.0)
    else:
        client, close = _make_inprocess_client()  # type: ignore[assignment]

    def work(tid: uuid.UUID, seq: int) -> None:
        content = f"date,channel,spend\n2026-01-0{(seq % 9) + 1},meta,{seq}\n".encode()
        t0 = time.perf_counter()
        up = client.post(
            f"/api/v1/tenants/{tid}/files",
            files={"upload": (f"feed_{seq}.csv", content, "text/csv")},
        )
        report.add("ingest", time.perf_counter() - t0, up.status_code == 201)
        if up.status_code != 201:
            return
        file_id = up.json()["file"]["id"]
        t1 = time.perf_counter()
        pr = client.post(f"/api/v1/tenants/{tid}/files/{file_id}/process")
        ok = pr.status_code == 200 and pr.json().get("job", {}).get("status") == "succeeded"
        report.add("process", time.perf_counter() - t1, ok)

    jobs = [(uuid.uuid4(), s) for _ in range(tenants) for s in range(files)]
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            list(pool.map(lambda a: work(*a), jobs))
    finally:
        close()
    elapsed = time.perf_counter() - started

    total = len(jobs)
    print(f"\n=== load result: {tenants} tenants × {files} files = {total} pipelines ===")
    print(f"concurrency={concurrency}  target={'in-process SQLite' if not base_url else base_url}")
    print(report.summary("ingest"))
    print(report.summary("process"))
    print(f"wall={elapsed:.2f}s  throughput={total / elapsed:.1f} pipelines/s")
    return report


def main() -> None:
    """Parse CLI args and run the load scenario."""
    parser = argparse.ArgumentParser(description="mmm-os load/scale harness (Phase 12)")
    parser.add_argument("--tenants", type=int, default=50)
    parser.add_argument("--files", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--base-url", type=str, default=None, help="live server, else in-process")
    args = parser.parse_args()
    run(args.tenants, args.files, args.concurrency, args.base_url)


if __name__ == "__main__":
    main()
