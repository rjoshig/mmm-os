# Phase 07.1 — Observability & Monitoring

**Inserted phase** (standalone, not a sub-phase) · **Depends on:** Phase 7 ·
**Status:** Done (metrics registry + structured context + pipeline wiring) — pending PR merge. The standard is defined here and instrumented incrementally; a production metrics/tracing backend exports the same signals (OQ-07.1-1).

Cross-cutting: observability (CC-7), multi-tenant (CC-1).

## Objective

Define the platform-wide observability standard — structured logging, metrics,
tracing, alerting, dashboards — so every phase emits consistent, tenant-aware
signals and operators can see health, throughput, and failures.

## Scope

- **In:** structured logging with context (`tenant_id`/`job_id`); metrics
  (throughput, latency, failures, queue depth); tracing across API→worker;
  alerting; dashboards; per-job event timeline (extends `job_event`); per-connector
  sync health.
- **Out:** the resilience *responses* to failures (Phase 07.2); the metrics/logging
  vendor decision (open question).

## Functional Requirements

- **P7.1-1 Structured logging:** logs MUST be structured and carry context
  (`tenant_id`, `job_id`, stage) where available; **no secrets** in logs (CC-12).
- **P7.1-2 Metrics:** the system MUST expose throughput, latency, error rates, and
  queue depth, dimensioned by tenant/stage where meaningful.
- **P7.1-3 Tracing:** requests MUST be traceable across the API→worker boundary
  (correlation/trace IDs propagated through jobs).
- **P7.1-4 Job timeline:** the per-job event record (`job_event`, CC-7) MUST give a
  stage-by-stage timeline with timing + outcome.
- **P7.1-5 Connector health:** each connector's sync health (last success, row
  counts, errors) MUST be observable (ties to Phase 09.8).
- **P7.1-6 Alerting + dashboards:** operational dashboards and alerts on key
  failure/latency/queue conditions MUST be definable.
- **P7.1-7 Incremental instrumentation:** each earlier phase instruments against
  this standard as it is built (Phase 1 onward), rather than retrofitting at the end.

## Deliverables

- Logging/metrics/tracing conventions + a shared instrumentation helper.
- Dashboards + alert definitions for core pipeline + workers + connectors.
- Extended `job_event` timeline surface.

## Acceptance Criteria

- A processing run emits a complete, tenant-tagged event timeline with timings.
- Metrics for throughput/latency/failures/queue-depth are visible on a dashboard.
- A request can be traced end-to-end from API call through worker completion.
- No secret material appears in any log/trace.

## Dependencies

Phase 7 (workers/queue). Instrumented incrementally from Phase 1. Feeds Phase 05.1
(LLM usage visibility) and Phase 09.8 (connector observability).

## Open Questions

- **OQ-07.1-1** Metrics/logging/tracing stack choice (e.g. OpenTelemetry +
  Prometheus/Grafana vs a hosted APM).

## Sub-phases

TBD — to be broken down before implementation.
