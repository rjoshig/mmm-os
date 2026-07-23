# Phase 01.4 — Large-File / Path-Based Ingestion (Landing Zone)

**Parent:** [`phase-01`](./phase-01-file-ingestion-structure-detection.md) ·
**Depends on:** 01.1 (object storage + source seam), 09.1 (`SourceConnector`) ·
**Status:** Build (scoped; not yet implemented).

## Objective

Let the backend ingest a file **by reference to a path/URI** instead of receiving a
browser upload — so very large files (millions of rows) are consumed directly from a
landing zone (a mounted directory / NFS share / object-storage URI / SFTP) without
streaming the bytes through the browser and HTTP.

## Why (the gap this closes)

Processing is already fully server-side: once a file is landed in object storage, all
detection/mapping/transform/validation/output read from storage, and the UI only ever
pulls **bounded samples** (`GET …/sheets/{id}/rows?limit=N`). The one browser-bound
step is the **initial upload**. For big files that is wasteful and fragile. This
sub-phase adds a **path/URI ingestion entry** that reuses the existing source seam —
the browser never transfers the bytes.

**Not a rework:** the source-agnostic seam already exists (`SourceConnector` →
`LandedDataset`; `FileSource` reads `storage.open(storage_key)`; SFTP already ingests
by server path). This adds a *local/URI landing-zone source* + an ingest-by-reference
endpoint on top of that seam.

## Scope

- **In:** a `LandingZoneSource` (local mounted path + object-storage URI) implementing
  `SourceConnector`; an **ingest-by-path** API that registers a file record + job from
  a server-accessible path/URI (copy-into-storage **or** reference-in-place per config)
  and runs the same parsing/profiling as upload; an allowlisted, tenant-scoped set of
  landing roots (no arbitrary filesystem reach); a UI "Add by path" option in the
  add-source wizard for operators.
- **Out:** partner API connectors (Phase 9.2–9.5); PDF/email extraction (deferred);
  streaming-parse re-architecture of the parser itself (large files are handled by
  bounded previews + chunked reads, not by loading whole files into memory).

## Functional Requirements

- **P1.4-1** Ingest-by-path endpoint: `POST …/files/ingest-by-path` accepting a
  path/URI within an **allowlisted landing root** (per-tenant config); creates the
  `file` + `job` records and lands the dataset via the source seam — no upload stream.
- **P1.4-2** `LandingZoneSource` (`SourceConnector`, `source_type="landing_zone"`):
  resolve local paths and object-storage URIs; either copy the bytes into immutable
  storage (CC-2) or register a **by-reference** pointer when the landing store is
  already the immutable store (no duplication for huge files).
- **P1.4-3** Safety: paths are validated against the tenant's allowlisted roots
  (canonicalized, no traversal); nothing outside a configured root is reachable
  (CC-1/CC-11). Credentials for remote URIs go through the `SecretStore` (CC-12).
- **P1.4-4** Parsing parity: detection/profiling use **bounded previews** and chunked
  reads so memory stays flat regardless of file size; the UI keeps reading bounded
  samples (never the whole file).
- **P1.4-5** Traceability: landed rows trace to `source`/path + job as usual (CC-3).

## Deliverables

- `sources/landing_zone_source.py` (+ registration in the source registry).
- Ingest-by-path router + schema; per-tenant landing-root config (reuse
  `tenant_settings` or connector config).
- Add-source wizard "Add by path" branch (operator-facing).
- Docs + tests (path allowlist enforcement, by-reference vs copy, large-file preview).

## Acceptance Criteria

- A file placed in an allowlisted landing root is ingested via `ingest-by-path` with
  **no browser upload**; it processes identically to an uploaded file.
- A path outside the allowlist (or with traversal) is rejected (403/400), tenant-scoped.
- A large file ingests with flat memory (bounded preview), and the UI shows only
  sampled rows.
- Backend `ruff`/`mypy`/`pytest` and front-end `typecheck`/`lint`/`build` pass.

## Dependencies

Phase 01.1 (storage + seam), 09.1 (`SourceConnector` contract). Coordinates with
Phase 9 (SFTP is a sibling path source) and Phase 00.6 (`SecretStore` for remote URIs).

## Open Questions

- **OQ-1.4.1** Copy-into-storage vs reference-in-place default: copy (safest, honors
  CC-2 immutability explicitly) vs reference (no duplication for huge files). Default:
  **copy**, with reference-in-place allowed when the landing store *is* the configured
  immutable object store.
- **OQ-1.4.2** Landing-root configuration home: `tenant_settings` vs a dedicated
  connector config. Default: a `landing_zone` connector config (reuses Phase 9 admin).
