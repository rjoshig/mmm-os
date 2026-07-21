# Phase 4 — Validation & Anomaly Detection

**Depends on:** Phases 1–3 · **Status:** Not started · **MVP:** yes (Phases 0–4)

Cross-cutting: human-in-the-loop (CC-5), observability (CC-7), traceability (CC-3).

## Objective

Automatically check cleaned data for quality issues and flag them for human
review before output is trusted.

## Scope

- **In:** rule-based validation; anomaly detection; flagging; review status.
- **Out:** AI anomaly *explanations* (Phase 5), UI surfacing (Phase 6).

## Functional Requirements

- **P4-1 Validation checks (v1):** missing required fields, date gaps, duplicate rows, negative/implausible values (e.g. negative spend), type mismatches, out-of-range values.
- **P4-2 Anomaly detection:** statistical outlier detection on measures (e.g. sudden spend spikes) per dimension slice.
- **P4-3 Flagging:** issues recorded against the job as structured `validation_flag` records (severity, location, description).
- **P4-4 Gate:** severity thresholds determine whether output is blocked, or passes with warnings, per configurable policy.
- **P4-5 Review status:** flags can be acknowledged/resolved/overridden by a human; decisions recorded.

## Deliverables

- Validation engine + configurable check set.
- Anomaly detector.
- `validation_flag` storage + review-status lifecycle.

## Acceptance Criteria

- A file with a 400% one-day spend spike, a duplicate row, and a missing date → produces 3 distinct correctly-located flags.
- Blocking-severity flag prevents output until resolved/overridden; warning-severity allows output with the warning recorded.
- Resolving a flag records who/when and unblocks per policy.

## Dependencies

Phases 1–3.

## Open Questions

- **OQ-4.1** Default severity policy (what blocks vs warns).
- **OQ-4.2** Anomaly method for v1 (simple z-score/IQR vs more).

## Sub-phases

TBD — to be broken down before implementation.
