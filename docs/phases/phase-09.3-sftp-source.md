# Phase 9.3 — SFTP File Source

**Parent:** [`phase-09`](./phase-09-future-connectors-extraction.md) ·
**Depends on:** 09.1, 09.2 · **Status:** Deferred (designed).

## Objective

Add SFTP as a **file source**: fetch dropped files from per-tenant directories and
land them through the same file parsing that uploads use.

## Scope

- **In:** SFTP connection + per-tenant directory layout; file-naming contract;
  optional PGP decryption; landing fetched files as `LandedDataset` via the
  existing file parsing (reusing `FileSource`-style logic).
- **Out:** API partners; scheduling internals (09.6).

## Functional Requirements

- **P9.3-1** Connect to a tenant's SFTP location with tenant-scoped credentials
  (CC-10) and enumerate new files by a documented naming convention.
- **P9.3-2** Fetch files immutably into object storage (CC-2), then land them via
  the file-parsing path — SFTP is just another file source (CC-9).
- **P9.3-3** Optional **PGP** decryption before parsing.
- **P9.3-4** Idempotent re-processing: re-fetching an already-seen file does not
  duplicate output (CC-6).

## Deliverables

- `src/mmm_os/connectors/sftp/` implementation (currently a placeholder).
- Per-tenant directory + naming contract documentation.

## Acceptance Criteria

- A file dropped in a tenant's SFTP dir is fetched, (optionally) decrypted, stored
  immutably, and lands identically to an equivalent upload.
- Re-seeing the same file produces no duplicate output.

## Dependencies

09.1 (landed dataset), 09.2 (credentials), Phase 1 (file parsing/storage).

## Open Questions

OQ-9.8 (per-tenant directory layout, file-naming contract, PGP).

## Sub-phases

N/A (leaf sub-phase).
