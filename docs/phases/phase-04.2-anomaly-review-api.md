# Phase 4.2 — Anomaly Detection, Review Lifecycle & API

**Parent:** [`phase-04`](./phase-04-validation-anomaly-detection.md) ·
**Depends on:** 04.1 · **Status:** Done (pending PR merge)

Covers **P4-2, P4-5** and realises OQ-4.2 (anomaly method).

## Objective

Add statistical anomaly detection on measures, a human review lifecycle for flags,
and the API that runs validation + anomaly checks and manages flag review.

## Scope

- **In:** z-score / IQR anomaly detection per dimension slice; flag review status
  lifecycle (acknowledge / resolve / override, recording who/when); API to run
  validation and to review flags.
- **Out:** AI anomaly *explanations* (Phase 5); UI (Phase 6).

## Functional Requirements

- **P4.2-1 Anomaly detection (P4-2, OQ-4.2):** z-score and IQR outlier detection on a measure, optionally per dimension slice; outliers become flags.
- **P4.2-2 Review lifecycle (P4-5):** a flag can be acknowledged / resolved / overridden by a human; the decision records who and when.
- **P4.2-3 API:** run validation (+ anomaly) over records for a job and persist flags; list a job's flags; review a flag.

## Deliverables

- `src/mmm_os/validation/anomaly.py` + review helpers in the validation service.
- `schemas/validation.py` + `api/routers/validation.py`.
- Tests: anomaly detection flags a spike; the acceptance scenario (spike + duplicate + missing date → 3 flags); review transitions record who/when; blocking gate via API.

## Acceptance Criteria

- A 400% one-day spend spike, a duplicate row, and a missing date produce 3 distinct correctly-located flags.
- A blocking flag prevents output until resolved/overridden; resolving records who/when and unblocks per policy.
- Anomaly detection uses z-score / IQR.

## Dependencies

Phase 4.1.

## Open Questions

OQ-4.2 resolved (z-score + IQR).

## Sub-phases

N/A (leaf sub-phase).
