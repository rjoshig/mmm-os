# Phase 14 — Config-Driven I/O Paths & Destinations

**Depends on:** 1 (ingestion/storage), 6 (Review UI) · **Status:** Build
· **Cycle:** 5 (Usability, Reuse & Model-Readiness)

Cross-cutting: **CC-14 config-driven I/O** (new), immutable raw (CC-2),
traceability/observability (CC-3/CC-7), portability (dialect/host never hardcoded).

See the umbrella design: [`../design/usability-reuse-model-readiness.md`](../design/usability-reuse-model-readiness.md) §4.1.

## Objective

Let each tenant configure **where data comes from and goes to** — a root set of
logical paths (`input`, `output`, `temp`, `archive`, `error`, `reject`) and output
**destinations** — as versioned config, so output is *written to a configured
path* (not only downloaded), and processed files follow a defined lifecycle.

## Scope

- **In:** an `io_profile` config entity (global default + per-tenant override);
  writing generated output to the configured `output` destination via the storage
  abstraction; a processed-file lifecycle (archive on success / error on failure /
  reject for validation-rejected); a Settings UI to view/edit the profile.
- **Out:** new storage backends beyond the existing local/S3 abstraction (ADR-006);
  per-connector path overrides (follow-up, OQ-14.1); scheduled folder-watching
  ingestion beyond the existing landing-zone (Phase 01.4).

## Cross-cutting

- **CC-14** paths & destinations are versioned config data, never hardcoded; env
  vars provide defaults only.
- **CC-2** the immutable raw copy still lands in object storage first; the
  lifecycle acts on **copies**, never the original.
- **CC-3/CC-7** every file move (to archive/error/reject) is recorded on the
  `job` / `job_event` timeline.
- **CC-1** an `io_profile` override is `tenant_id`-scoped.

## Functional Requirements

- **P14-1 io_profile entity:** a config-as-data record declaring logical roots
  `input`, `output`, `temp`, `archive`, `error`, `reject`, each a storage URI/prefix.
  A **global default** resolves when a tenant has no override; a per-tenant row
  overrides it. Backed by env defaults in `core/config.py` (extend `Settings`,
  reusing the `landing_roots` / `storage_local_path` pattern).
- **P14-2 Resolution:** an `io_profile` resolver (global → tenant) exposed to the
  pipeline and output services; values are storage keys/prefixes resolved through
  the existing `ObjectStorage` abstraction — **never** a hardcoded dialect or host.
- **P14-3 Output-to-destination:** generating a Stack / job output **writes a file
  to the resolved `output` destination** (local path or S3 prefix) **in addition
  to** the existing browser CSV download (`api/routers/output.py`
  `StreamingResponse`). The written path is recorded on the job.
- **P14-4 File lifecycle:** on successful ingest→output, the processed input copy
  moves to `archive`; on job failure, to `error`; rows/files rejected by a
  validation gate are routed to `reject`; scratch artifacts use `temp`. Every move
  emits a `job_event`. Default action is **copy** (immutability-preserving);
  move-vs-copy is configurable (OQ-14.2).
- **P14-5 Settings UI:** a Settings → "Storage & I/O" panel to view and edit the
  tenant's `io_profile` (reuse `app/settings/page.tsx` patterns, `DataTable`,
  `inputCls`); values validated (must resolve within the configured storage root;
  no traversal — reuse the `ingestion/landing.py` validation approach).

## Deliverables

- `io_profile` model + migration (tenant-scoped, dialect-agnostic types) + a global
  default seed.
- Resolver service + `core/config.py` env defaults for each logical root.
- Output service writes to the resolved `output` destination; lifecycle mover with
  `job_event` records.
- Backend endpoints to read/update the profile (RBAC: `admin`); Settings UI panel.
- Tests: resolution precedence, path safety, lifecycle transitions, output-file
  written to destination, download still works.

## Acceptance Criteria

- With no tenant override, output writes under the **global default** `output` path;
  with an override, it writes under the **tenant** path.
- Generating output produces both a **downloadable CSV** and a **file at the
  configured `output` destination**; the written path is recorded on the job.
- A successful run archives the processed input copy; a failed run routes it to
  `error`; both emit `job_event`s. The immutable raw original is untouched (CC-2).
- A path outside the configured storage root / containing traversal is rejected.
- Backend `ruff`/`mypy`/`pytest` and front-end `typecheck`/`lint`/`build` pass.

## Dependencies

Phase 1 (storage + landing-zone path validation), Phase 6 (Settings UI). Unblocks
the destination export used by Phase 16.

## Open Questions

- **OQ-14.1** io_profile scope — global default + per-tenant override; per-connector
  path overrides in v1? Default: global + tenant only.
- **OQ-14.2** file lifecycle — move vs copy to archive/error/reject. Default: copy
  (preserve immutability); move configurable per tenant.

## Sub-phases

TBD — split into a config/entity slice and a lifecycle/destination slice at build
time if the phase proves too large for one PR (per the sub-phase convention in
[`README.md`](./README.md)).
