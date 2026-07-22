# Phase 07.2 — Resilience & Error Handling

**Inserted phase** (standalone, not a sub-phase) · **Depends on:** Phase 7 ·
**Status:** Build — extends Phase 7.

Cross-cutting: idempotent jobs (CC-6), observability (CC-7), source-agnostic
pipeline (CC-9).

## Objective

Make the async pipeline robust under partial failure: retry transient errors, quarantine
poison jobs, and ensure retries never duplicate output (CC-6) — so one bad file or
one failing partner never takes down a batch.

## Scope

- **In:** retry with backoff; dead-letter queue (DLQ) for poison jobs; idempotency
  hardening; partner-API failure handling (rate-limit/backoff, partial-failure
  isolation); circuit-breaker / graceful degradation.
- **Out:** the observability *signals* themselves (Phase 07.1 — this phase reacts to
  them); connector pull logic (Phase 9).

## Functional Requirements

- **P7.2-1 Retry/backoff:** transient failures MUST retry with bounded exponential
  backoff; limits are configurable.
- **P7.2-2 DLQ:** jobs that exhaust retries (poison jobs) MUST move to a
  dead-letter queue with the failure recorded (CC-7), not silently dropped or
  infinitely retried.
- **P7.2-3 Idempotency hardening (CC-6):** re-running/retrying a job on the same
  input MUST NOT duplicate output — keyed idempotent writes (ties to connector
  re-pull "replace, never duplicate").
- **P7.2-4 Partner-API failures:** rate-limit/backoff per partner; a single
  connector or file failing MUST be **isolated** — the rest of the batch proceeds;
  errors are surfaced clearly.
- **P7.2-5 Circuit breaker / degradation:** repeated failures to a dependency
  (partner API, LLM, storage) SHOULD trip a breaker and degrade gracefully rather
  than hammering a failing service.

## Deliverables

- Retry/backoff policy + DLQ wiring on the worker queue (ADR-007).
- Idempotency keys/guards on output writes.
- Per-connector isolation + circuit-breaker utilities.

## Acceptance Criteria

- A transient failure retries and then succeeds; a permanent failure lands in the
  DLQ with a readable reason.
- Re-running a completed/failed job produces no duplicate output rows.
- One connector failing in a multi-source batch does not fail the others.
- A repeatedly-failing dependency trips the breaker instead of retrying endlessly.

## Dependencies

Phase 7 (Celery+Redis, ADR-007). Coordinates with Phase 07.1 (signals) and Phase 9
(connector failures). Reinforces CC-6 established in Phases 1–4.

## Open Questions

- **OQ-07.2-1** Retry limits/policy per failure class.
- **OQ-07.2-2** DLQ handling workflow (alert, manual replay, auto-expiry).

## Sub-phases

TBD — to be broken down before implementation.
