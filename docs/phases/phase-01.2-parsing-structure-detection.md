# Phase 1.2 — Parsing & Structure Detection

**Parent:** [`phase-01`](./phase-01-file-ingestion-structure-detection.md) ·
**Depends on:** 01.1 · **Status:** Done (pending PR merge)

Covers **P1-2, P1-3, P1-4** and the streaming/failure aspects of **P1-6, P1-7**.

## Objective

Parse an ingested file into per-sheet tables and detect their structure: split
multi-tab workbooks, locate the real header row, and infer column types.

## Scope

- **In:** CSV + multi-tab XLSX/XLS parsing; empty-sheet detection/skip; `sheet`
  record creation; header-row detection (skip title/blank/merged rows); per-column
  type + date-format inference; streamed/chunked reads; recorded parse errors.
- **Out:** profiling stats (01.3); mapping/transform/AI.

## Functional Requirements

- **P1.2-1 Multi-tab split (P1-2):** for XLSX/XLS, each sheet is a candidate table; empty sheets are detected and skipped; each non-empty sheet is recorded as a `sheet` row.
- **P1.2-2 Header detection (P1-3, OQ-1.2):** locate the real header row per sheet, skipping title rows, blank rows, notes, and handling merged cells. Deterministically pick the best-scoring header; when confidence is below threshold, mark the sheet `needs-review` (AI assists in Phase 5).
- **P1.2-3 Type inference (P1-4):** infer per-column types (date, number, currency, string, boolean) and detect date formats.
- **P1.2-4 Large-file safety (P1-6):** stream/chunk parsing; never load an entire large file into memory at once.
- **P1.2-5 Failure handling (P1-7):** malformed files record a clear error on the `job` (and sheet where applicable) — no crash.

## Deliverables

- Parser module supporting CSV and multi-tab XLSX/XLS.
- Structure-detection module (header detection + type inference).
- `sheet` records with header location + status; recorded parse errors on failure.
- Tests covering the acceptance scenarios below.

## Acceptance Criteria

- A 3-sheet XLSX (one empty, one with 2 title rows above the header, one clean) → 2 non-empty `sheet` records, each with the correct header row located and types inferred.
- A CSV → a single sheet, parsed correctly.
- A malformed file → job marked failed with a readable reason, no crash.

## Dependencies

Phase 1.1 (raw files + file/job records).

## Open Questions

OQ-1.2 resolved (pick + flag). Library choice (pandas/polars/openpyxl) to be
fixed during implementation.

## Sub-phases

N/A (leaf sub-phase).
