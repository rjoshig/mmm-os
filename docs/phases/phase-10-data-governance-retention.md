# Phase 10 — Data Governance & Retention

**Tail phase** · **Depends on:** Phases 0–8 · **Status:** Build (in progress) —
retention purge engine + admin endpoints shipped (P10-1); right-to-erasure (P10-3)
+ PII/backup-DR design next.

> Now being built (was spec-only). Implements the enforceable pieces (retention
> purge + erasure) and keeps the policy/design parts (backup-DR, residency) as
> documented design. Cross-references — not duplicates — Phase 08.1 (technical
> compliance controls).

## Objective

Design the data-governance posture: how long data is kept, how it is backed up and
recovered, how a tenant's data is deleted, where it may reside, and how PII is
handled — so the technical controls (Phase 08.1) have policies to enforce.

## Scope

- **In (design):** retention policies per data class; backup + disaster recovery
  (RPO/RTO targets); tenant data deletion / right-to-erasure; data residency; PII
  handling posture (noting partner data is **aggregate**, not user-level PII).
- **Out:** implementation of any of the above; the technical controls themselves
  (Phase 08.1).

## Retention matrix (P10-1 — implemented)

Retention windows are app-configurable (`RETENTION_*` settings; 0 = keep forever)
with defensible defaults. A **raw file's** purge cascades all data derived from it;
other classes are purged standalone. Purge runs on demand
(`POST /tenants/{id}/retention/run`, admin, audited, idempotent CC-6).

| Data class | Default | Deletion rule |
|---|---|---|
| Raw file (+ derived: sheets, profiles, jobs, events, flags, suggestions, output rows, storage bytes) | 365 d | Cascade-delete files older than the window; removes immutable-raw bytes (governance exception to CC-2). |
| LLM usage (`llm_usage`) | 90 d | Delete rows past the window. |
| Sync runs (`sync_run`) | 180 d | Delete rows past the window. |
| Notifications (read) | 90 d | Delete **read** notifications past the window. |
| Audit log (`audit_log`) | 0 (keep) | Retained by default; configurable window if a shorter policy is required. |

## Functional Requirements (design targets)

- **P10-1 Retention:** ✅ **Built** — `governance/retention.py` (`RetentionPolicy`,
  `run_retention`, shared `delete_file_data` cascade) + admin endpoints
  (`/retention/policy`, `/retention/run`). See the matrix above.
- **P10-3 Deletion / erasure:** ✅ **Built** — `governance/erasure.py`. Reconciles
  OQ-10-3: **erase_file** removes one file + its derived data + immutable-raw bytes
  (the CC-2 exception); **erase_tenant** wipes every data-bearing tenant-scoped table
  + all raw bytes, **keeping** user identities, the `audit_log`, and the tenant
  shell — and records the erasure event, so *what was erased* stays provable while the
  *data* is gone. Endpoints: `POST /erase/files/{id}`, `POST /erase` (requires
  `{"confirm":"ERASE"}`), both admin + audited.
- **P10-2 Backup & DR:** 📝 **Design** (see Design notes) — RPO/RTO + backup/restore
  approach for both DBs + object storage. Not implemented (infra concern, Phase 11).
- **P10-4 Residency:** 📝 **Design** (see Design notes) — data-residency options.
- **P10-5 PII posture:** 📝 **Documented** (see Design notes) — file sources may carry
  PII; partner connector data is aggregate-only (no user-level PII, CC-10/OQ-9.6).

## Design notes (P10-2 / P10-4 / P10-5)

**Backup & DR (P10-2, OQ-10-2).** Targets: **RPO ≤ 24 h**, **RTO ≤ 4 h** for the
managed offering. Approach — *Backend + UI databases:* on Postgres (the production
target), daily full + WAL/PITR continuous archiving to object storage in a second
region; nightly logical dumps as a portable fallback. *Object storage (raw files +
output):* versioning + cross-region replication; lifecycle rules aligned to the
retention matrix. *Restore drills:* quarterly; a restore runbook lives with the
deployment phase (Phase 11). SQLite (dev) is out of scope for DR. Implementation is
an **infrastructure** concern owned by Phase 11 — this phase sets the targets.

**Residency (P10-4, OQ-10-4).** A tenant declares a home **region**; its two DBs +
object-storage buckets are provisioned in that region and never replicated outside it
except to same-jurisdiction DR regions. Partner-connector egress uses region-local
endpoints where the partner offers them. Cross-region access is denied at the
infra/network layer (Phase 11). v1 default: single region; multi-region is a
deployment-time option, not app code.

**PII posture (P10-5).** *Uploaded file sources may contain PII* (campaign data can
include emails, user ids). Treatment: raw files are immutable + encrypted at rest,
tenant-scoped, access-controlled (CC-1/CC-11), retained per the matrix, and erasable
(P10-3). *Partner-connector data is aggregate-only* — no user-level PII (CC-10,
OQ-9.6); credentials never logged (CC-10/CC-12). LLM inputs are **profiles, not raw
rows** (P5-1), reducing PII exposure to the model. The platform does **not** attempt
automatic PII detection/redaction in v1 — that is a future enhancement.

## Deliverables

- ✅ A retention matrix (data class → retention → deletion rule) + **implemented**
  purge engine (P10-1).
- ✅ A deletion/erasure design reconciling immutability + audit + **implemented**
  erasure (P10-3).
- 📝 A backup/DR design note with RPO/RTO; a residency design; a PII posture (above).

## Acceptance Criteria

- ✅ Retention purge + right-to-erasure are implemented, admin-gated, audited, and
  tenant-scoped, with tests (P10-1, P10-3).
- ✅ The backup/DR + residency + PII designs are complete enough for Phase 08.1 to
  reference and Phase 11 to implement the infra pieces.

## Dependencies

Builds on Phases 0–8; the backup/DR + residency *implementation* is owned by Phase 11
(deployment/infra). Consumed by Phase 08.1 (compliance controls).

## Open Questions

- **OQ-10-1** ✅ Resolved — retention per data class (see the matrix); app-configurable.
- **OQ-10-2** ✅ Resolved (targets) — RPO ≤ 24 h, RTO ≤ 4 h; implementation in Phase 11.
- **OQ-10-3** ✅ Resolved — erasure deletes raw (CC-2 exception) + data; keeps audit +
  identity and records the erasure (see P10-3).
- **OQ-10-4** ✅ Resolved (design) — per-tenant home region; multi-region is a
  deployment option (Phase 11).

## Sub-phases

Built in slices: **1** retention purge engine (P10-1), **2** right-to-erasure (P10-3),
**3** design notes for backup/DR + residency + PII (P10-2/4/5) + governance admin UI.
