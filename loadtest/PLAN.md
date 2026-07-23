# Load & Scale Test Plan (Phase 12)

Executable plan for validating `mmm-os` at the target scale of **200–500 tenants**
with large batch concurrency, before it is relied on in production. The runnable
harness is [`loadtest/run_load.py`](./run_load.py); the fairness/isolation
mechanisms are also proven fast in `tests/test_scale_fairness.py`.

## Scenarios (P12-1)

| # | Scenario | Shape | What it stresses |
|---|---|---|---|
| S1 | Batch ingest | 200–500 tenants × 50–60 files each, ingest→process | Parser/detector throughput; DB write contention; storage |
| S2 | Concurrent mapping/transform/validation | Many tenants running the pipeline stages at once | CPU-bound stages; session/engine pool limits |
| S3 | Connector sync fan-out | Many scheduled connectors due at once | Scheduler routing (pool + silos, 7.6); SyncRun writes |
| S4 | Noisy neighbor | 1 tenant floods; N others send light load | Per-tenant fairness (ADR-007, P12-3) |
| S5 | Worker saturation | Enqueue beyond worker capacity | Queue depth, backpressure, retries/DLQ (P12-4) |
| S6 | LLM under load | Suggestions across tenants with budgets set | Throughput + Phase 05.1 budget/cap enforcement (P12-5, CC-13) |

## Target SLAs (P12-2) — pass/fail thresholds

Set against a stage environment on managed Postgres (tune with OQ-12-1). Initial
targets:

| Metric | Target |
|---|---|
| Ingest (per file) p95 | ≤ 750 ms |
| Process/detect (per sheet) p95 | ≤ 1.0 s |
| End-to-end pipeline p95 | ≤ 5 s |
| Error rate under S1–S3 | < 0.1% |
| Fairness (S4): light-tenant first-task latency | not worse than ~1 rotation regardless of heavy backlog |
| Saturation (S5): tasks lost | 0 (retried then dead-lettered, never dropped) |
| LLM (S6): over-budget calls | 0 (429 enforced; CC-13) |

## Noisy-neighbor design (P12-3)

The batch queue is **per-tenant round-robin** (`EagerTaskQueue` in dev; Celery+Redis
in prod, same contract). One tenant's backlog is drained one task per rotation, so
other tenants' first tasks are never starved. Proven deterministically in
`tests/test_scale_fairness.py::test_per_tenant_fairness_no_starvation`; at scale,
run S4 and assert light-tenant latency percentiles are flat as the heavy tenant's
backlog grows.

## Saturation design (P12-4)

Drive S5 past worker capacity and observe: queue depth rises then drains (no loss);
failed tasks are retried up to `max_retries` then dead-lettered (`DrainResult`);
autoscaling adds workers on queue depth (ADR-007). Pass = zero lost tasks, bounded
dead letters, recovery to steady state after load stops.

## LLM-under-load design (P12-5)

With per-tenant daily token/call caps set (Phase 05.1), run S6 concurrently and
assert over-budget calls receive 429 and metered usage never exceeds the cap
(CC-13). The LLM is off by default, so this scenario runs only where enabled.

## Running the harness

```bash
# Scaled proof (self-contained, in-process SQLite):
uv run python loadtest/run_load.py --tenants 50 --files 3 --concurrency 16

# Full scale against a stage server (managed Postgres):
uv run python loadtest/run_load.py --base-url https://stage.example \
    --tenants 300 --files 20 --concurrency 64
```

It reports per-stage p50/p95/p99 + throughput and fails loudly on non-2xx.

## Observed baseline (in-process SQLite, dev laptop)

A smoke run of **50 tenants × 3 files = 150 pipelines** at concurrency 16:

```
ingest   n=150 fails=0  p50=20ms  p95=190ms  p99=875ms
process  n=150 fails=0  p50=24ms  p95=263ms  p99=862ms
throughput ≈ 103 pipelines/s
```

This is a **mechanism proof**, not a capacity number: in-process SQLite serializes
writes and shares one process. Real capacity is measured on stage (managed Postgres
+ horizontal API/worker replicas) against the SLAs above. Use this baseline only to
catch regressions in the harness + pipeline hot path.

## Scale ceiling (OQ-12-3)

Confirm 200–500 tenants with 50–60 files/tenant per cycle and the batch sizes S1
implies. Revisit engine-registry + connection-pool limits when many **silos** are
active (each dedicated DB is a separate pool; see architecture §3.1).
