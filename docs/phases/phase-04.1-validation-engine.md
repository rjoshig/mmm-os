# Phase 4.1 — Validation Engine & Flagging

**Parent:** [`phase-04`](./phase-04-validation-anomaly-detection.md) ·
**Depends on:** Phases 1–3 · **Status:** Done (pending PR merge)

Covers **P4-1, P4-3, P4-4** and realises OQ-4.1 (severity policy).

## Objective

Run rule-based quality checks over cleaned records, assign severities via a
configurable policy, and persist structured flags — gating output when a blocking
issue is found.

## Scope

- **In:** validation checks (missing required, date gaps, duplicate rows,
  negative/implausible measures, type mismatches); severity policy;
  `validation_flag` persistence; blocking gate.
- **Out:** statistical anomaly detection (04.2); review lifecycle + API (04.2);
  AI explanations (Phase 5).

## Functional Requirements

- **P4.1-1 Checks (P4-1):** missing required fields, date gaps, duplicate rows, negative measures, type mismatches.
- **P4.1-2 Findings → flags (P4-3):** each issue becomes a structured flag with `check`, `severity`, `description`, and `location`.
- **P4.1-3 Policy (P4-4, OQ-4.1):** a configurable severity policy — default BLOCK = missing/unmapped required field, negative measure, type mismatch on a required field; WARN = date gaps, duplicates, out-of-range non-required.
- **P4.1-4 Gate:** a blocking-severity flag blocks output; warnings pass with the warning recorded.
- **P4.1-5 Persistence:** flags persist as `validation_flag` rows (tenant + job scoped), review status `open`.

## Deliverables

- `src/mmm_os/validation/` — `flags`, `policy`, `checks`, `engine`, plus a persistence helper.
- Tests: each check; policy severity assignment; blocked vs warn gating.

## Acceptance Criteria

- A record set with a duplicate row, a missing date, and a negative measure produces distinct, correctly-located flags.
- A blocking flag reports `blocked`; warning-only does not.
- Flags persist against the job with review status `open`.

## Dependencies

Phases 1–3 (records + canonical schema).

## Open Questions

OQ-4.1 resolved (default severity policy).

## Sub-phases

N/A (leaf sub-phase).
