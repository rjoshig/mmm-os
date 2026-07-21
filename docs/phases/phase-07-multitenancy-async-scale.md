# Phase 7 — Multi-Tenancy, Async & Scale

**Depends on:** all prior phases · **Status:** Not started

Cross-cutting: multi-tenant (CC-1), idempotent jobs (CC-6), observability (CC-7).

## Objective

Harden the system to process large batches (e.g. 50–60 files per customer)
reliably and concurrently across many tenants.

## Scope

- **In:** job queue + workers; async pipeline; per-tenant rate limiting;
  isolation hardening; observability dashboards; retries.
- **Out:** new features.

## Functional Requirements

- **P7-1 Async pipeline:** all ingestion/transformation runs as background jobs via the queue; API never processes files inline.
- **P7-2 Batch handling:** a 60-file upload fans out into per-file jobs with individual status, retries, and aggregate progress.
- **P7-3 Concurrency + fairness:** per-tenant rate limiting so one tenant's batch can't starve others.
- **P7-4 Isolation hardening:** verify no cross-tenant access paths; add tenant-scoping tests.
- **P7-5 Retries + idempotency:** transient failures retry safely without duplicate output (CC-6).
- **P7-6 Observability:** dashboards/metrics for job throughput, failures, latency, queue depth; per-job event timeline.
- **P7-7 Scale mechanics:** stream/chunk large files; workers autoscale.

## Deliverables

- Queue + worker deployment; batch orchestration; rate limiting; observability.

## Acceptance Criteria

- Submit 60 files across 3 tenants concurrently → all process, per-file status visible, no cross-tenant leakage, no single tenant monopolises workers.
- Kill a worker mid-job → job retries and completes without duplicate output.

## Dependencies

All prior phases.

## Open Questions

- **OQ-7.1** Queue tech (Celery vs RQ vs managed) and worker hosting.

## Sub-phases

TBD — to be broken down before implementation.
