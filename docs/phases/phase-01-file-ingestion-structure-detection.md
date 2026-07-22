# Phase 1 — File Ingestion & Structure Detection

**Depends on:** Phase 0 · **Status:** Not started · **MVP:** yes (Phases 0–4)

Cross-cutting: immutable raw files (CC-2), traceability (CC-3), observability (CC-7).

## Objective

Accept files, store them immutably, parse CSV/XLSX (including multi-tab), and
profile their structure so downstream phases have clean, described tables to work
on.

## Scope

- **In:** upload/landing; object storage; job record creation; CSV + XLSX
  (multi-tab) parsing; header-row detection; type inference; profiling.
- **Out:** mapping, transformation, AI, connectors, PDF/email.

## Functional Requirements

- **P1-1 Ingest** files via upload endpoint (watched-folder/email drop MAY be stubbed for later). Store the raw file immutably in object storage; create a `file` record + `job`.
- **P1-2 Multi-tab split:** for XLSX/XLS, treat each **sheet** as a candidate table; detect and skip empty sheets; record each as a `sheet` row.
- **P1-3 Header detection:** locate the real header row per sheet, skipping title rows, blank rows, notes, and handling merged cells.
- **P1-4 Type inference:** infer per-column data types (date, number, currency, string, boolean) and detect date formats.
- **P1-5 Profiling:** compute per-column stats — distinct value count, sample values, null rate, min/max — and store as a profile artifact. *(This profile is what the AI layer will consume in Phase 5 — distinct values + stats, never raw dumps.)*
- **P1-6 Large-file safety:** stream/chunk parsing; MUST NOT load an entire large file into memory at once.
- **P1-7 Failure handling:** malformed files produce a clear, recorded error on the job (not a crash).

## Deliverables

- Ingestion endpoint + object-storage integration.
- Parser supporting CSV and multi-tab XLSX/XLS.
- Structure-detection + profiling module.
- Persisted `file`, `sheet`, and `profile` records.

## Acceptance Criteria

- Upload a 3-sheet XLSX (one empty, one with 2 title rows above the header, one clean) → system creates 2 non-empty sheet records, correctly locates each header row, infers types, and produces a profile.
- Upload a CSV → single sheet, profiled correctly.
- A deliberately malformed file → job marked failed with a readable reason, no crash.
- Raw file retrievable, byte-identical to what was uploaded.

## Dependencies

Phase 0.

## Open Questions

- **OQ-1.1** — ✅ Resolved: v1 ceiling **~200 MB / ~5M rows per sheet**, streamed/chunked, configurable; over-limit files fail the job with a clear reason.
- **OQ-1.2** — ✅ Resolved: **pick + flag** — auto-select the highest-scoring header deterministically; below a confidence threshold, flag `needs-review` (AI assists in Phase 5).
- **OQ-INIT.1** — ✅ Resolved: object storage via an **abstraction** — local filesystem in dev, S3-compatible (S3/MinIO) in prod. See ADR-006.

_All Phase-1 open questions resolved. See [`../open-questions.md`](../open-questions.md)._

## Sub-phases

Phase 1 is implemented as three PR-sized sub-phases (one per branch/PR):

- [`phase-01.1-object-storage-ingestion.md`](./phase-01.1-object-storage-ingestion.md) — object-storage abstraction + upload endpoint + file/job records (P1-1). **In progress.**
- [`phase-01.2-parsing-structure-detection.md`](./phase-01.2-parsing-structure-detection.md) — CSV/multi-tab XLSX parsing, sheet split, header detection, type inference (P1-2, P1-3, P1-4). **Not started.**
- [`phase-01.3-profiling.md`](./phase-01.3-profiling.md) — per-column profiling stats persisted as a profile artifact (P1-5). **Not started.**
