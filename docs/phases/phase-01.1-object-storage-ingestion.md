# Phase 1.1 — Object Storage & File Ingestion

**Parent:** [`phase-01`](./phase-01-file-ingestion-structure-detection.md) ·
**Depends on:** Phase 0 · **Status:** Done (pending PR merge)

Covers **P1-1** (and the immutable-raw part of P1-6/P1-7). Realises ADR-006
(object-storage abstraction) and OQ-1.1 (v1 size ceiling).

## Objective

Accept file uploads, store the raw bytes immutably behind a storage abstraction,
and create the `file` + `job` records — the entry point for the pipeline.

## Scope

- **In:** object-storage abstraction (local filesystem backend for dev,
  S3-compatible for prod); chunked/streamed write with a size guard; ingestion
  service; upload endpoint; `file` + `job` record creation.
- **Out:** parsing, sheet split, header detection, type inference (01.2);
  profiling (01.3); async job execution (Phase 7).

## Functional Requirements

- **P1.1-1 Storage abstraction:** an `ObjectStorage` interface with a local-filesystem backend (dev) selected by env; an S3-compatible backend is the prod target (ADR-006). Writes are **immutable** — a key is never overwritten.
- **P1.1-2 Streamed write (P1-6):** the raw bytes are written in chunks; the whole file is never loaded into memory at once. A SHA-256 checksum and byte size are computed during the stream.
- **P1.1-3 Size guard (OQ-1.1):** uploads over the configured ceiling (`max_upload_bytes`, default ~200 MB) are rejected with a clear error and no persisted partial object.
- **P1.1-4 Ingest:** an upload endpoint stores the raw file and creates a `file` record (immutable pointer + metadata) and a `job` record (status `pending`), tenant-scoped (CC-1).
- **P1.1-5 Immutability (CC-2):** the stored raw bytes are retrievable byte-identical to what was uploaded.
- **P1.1-6 Config via env (P1-6/CC-8):** storage backend, local path, and size ceiling are read from settings/env — nothing hardcoded.

## Deliverables

- `src/mmm_os/storage/` — `ObjectStorage` interface + `LocalObjectStorage` + a backend factory.
- `src/mmm_os/ingestion/service.py` — `ingest_file(...)`.
- `src/mmm_os/api/routers/files.py` + `api/deps.py` — the upload route wired into the app.
- `src/mmm_os/schemas/file.py` — file/job read schemas.
- Settings additions (`storage_backend`, `storage_local_path`, `max_upload_bytes`).
- Tests: upload → 201 with file+job; raw bytes byte-identical; checksum/size correct; oversize rejected; storage refuses overwrite.

## Acceptance Criteria

- Uploading a file returns a `file` + `job` (job `pending`), tenant-scoped.
- The stored raw file is retrievable byte-identical to the upload (CC-2).
- An over-ceiling upload is rejected with a readable error and leaves no partial object.
- The storage backend, path, and size ceiling come from env; a key is never overwritten.

## Dependencies

Phase 0 (models, tenancy).

## Open Questions

None outstanding (OQ-1.1 and OQ-INIT.1 resolved). The S3-compatible backend
implementation itself is deferred to first prod deploy (interface in place now).
