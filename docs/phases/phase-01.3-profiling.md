# Phase 1.3 — Profiling

**Parent:** [`phase-01`](./phase-01-file-ingestion-structure-detection.md) ·
**Depends on:** 01.2 · **Status:** Done (pending PR merge)

Covers **P1-5**.

## Objective

Compute per-column statistics for each parsed sheet and persist them as a
`profile` artifact — the input the AI layer consumes in Phase 5 (distinct values
+ stats, never raw dumps).

## Scope

- **In:** per-column stats (distinct value count, sample values, null rate,
  min/max) computed over parsed sheet data; `profile` record creation.
- **Out:** sending anything to an LLM (Phase 5); mapping/transform.

## Functional Requirements

- **P1.3-1 Profiling (P1-5):** for each non-empty sheet, compute per-column stats — distinct value count, a bounded sample of values, null rate, and min/max — and store them as a `profile` artifact keyed to the sheet.
- **P1.3-2 Privacy-preserving shape:** the profile stores **distinct values + stats**, not full row dumps, so it can be safely fed to the AI layer later.
- **P1.3-3 Bounded:** sample sizes and distinct-value collection are bounded so profiling a wide/large sheet stays cheap.

## Deliverables

- Profiling module computing per-column stats from parsed sheet data.
- Persisted `profile` records (one per non-empty sheet).
- Tests: profile has expected stats per column; samples/distincts are bounded.

## Acceptance Criteria

- Each non-empty sheet produces a `profile` with per-column distinct counts, sample values, null rate, and min/max.
- Profiles contain distinct values + stats only (no full row dumps).

## Dependencies

Phase 1.2 (parsed sheets + detected structure).

## Open Questions

None outstanding.

## Sub-phases

N/A (leaf sub-phase).
