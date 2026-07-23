# Phase 12 — Load & Scale Testing

**Tail phase** · **Depends on:** Phases 0–8 (+ 11 for environments) · **Status:**
Built (plan + runnable harness + fairness/isolation proofs) — full-scale run is a
stage-environment activity.

> **Now built:** the load/scale plan is written **and** backed by a runnable
> harness and fast mechanism proofs. Executing it at full 200–500-tenant scale is
> a stage-environment activity (managed Postgres + horizontal replicas), gated by
> the SLA thresholds below.

## Implemented artifacts

- **Plan:** [`loadtest/PLAN.md`](../../loadtest/PLAN.md) — scenarios S1–S6, target
  SLAs + pass/fail thresholds, noisy-neighbor + saturation + LLM-under-load designs.
- **Harness (executable):** [`loadtest/run_load.py`](../../loadtest/run_load.py) —
  drives N tenants × M files ingest→process concurrently, in-process (SQLite) or
  against a live server (`--base-url`), reporting p50/p95/p99 + throughput.
- **Mechanism proofs (CI, fast):** `tests/test_scale_fairness.py` — per-tenant
  round-robin fairness (no starvation, P12-3) and tenant isolation under concurrent
  ingest (CC-1 under load).
- **Baseline captured:** 50 tenants × 3 files = 150 pipelines, 0 failures,
  ≈103 pipelines/s in-process (a mechanism/regression baseline, not a capacity
  number — real capacity is measured on stage; see PLAN §"Observed baseline").

Still open: concrete per-stage SLA numbers (OQ-12-1) and the full-scale stage run
(OQ-12-3) are set/executed against the deployed stage environment.

## Objective

Design a load/scale test plan that validates the platform at target scale —
**200–500 tenants** and large batch concurrency — before it is relied on in
production.

## Scope

- **In (design):** test scenarios; target SLAs; noisy-neighbor (per-tenant
  fairness) tests; worker-saturation tests; LLM throughput/cost under load.
- **Out:** running the tests; building the harness (design the plan only).

## Functional Requirements (design targets)

- **P12-1 Scenarios:** SHOULD define representative scenarios (batch ingest of
  50–60 files/tenant across many tenants; concurrent mapping/transform/validation;
  connector sync fan-out).
- **P12-2 Target SLAs:** SHOULD define latency/throughput SLAs per stage and
  end-to-end.
- **P12-3 Noisy-neighbor:** SHOULD test that one heavy tenant cannot starve others
  (per-tenant fairness, ADR-007).
- **P12-4 Worker saturation:** SHOULD test queue depth/backpressure and autoscaling
  behaviour under saturation.
- **P12-5 LLM under load:** SHOULD test LLM throughput + cost under load, validating
  the Phase 05.1 budgets/caps hold (CC-13).

## Deliverables (design artifacts)

- A load/scale test plan (scenarios + SLAs + pass/fail thresholds).
- A noisy-neighbor + saturation test design.

## Acceptance Criteria

- The plan is complete enough to execute against a stage environment and judge
  readiness for 200–500 tenants. *(No runtime acceptance — spec-only.)*

## Dependencies

Conceptually depends on Phases 7 (async/scale), 05.1 (LLM budgets), 11
(environments). No build dependency (design-only).

## Open Questions

- **OQ-12-1** Concrete SLA targets per stage.
- **OQ-12-2** Load-testing tooling + traffic modelling.
- **OQ-12-3** Scale ceiling to validate (confirm 200–500 tenants + batch sizes).

## Sub-phases

N/A (spec-only; break down if/when scheduled to build).
