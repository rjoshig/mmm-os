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
- **P10-2 Backup & DR:** SHOULD define RPO/RTO targets and a backup/restore +
  disaster-recovery approach for both databases + object storage.
- **P10-3 Deletion / erasure:** SHOULD define tenant data deletion and
  right-to-erasure, including immutable-raw (CC-2) and audit-log tensions.
- **P10-4 Residency:** SHOULD define data-residency options and how tenant region
  constraints are honoured.
- **P10-5 PII posture:** SHOULD document the PII stance — file sources may carry
  PII; partner connector data is aggregate-only (no user-level PII, CC-10/OQ-9.6).

## Deliverables (design artifacts)

- A retention matrix (data class → retention → deletion rule).
- A backup/DR design note with RPO/RTO.
- A deletion/erasure design reconciling immutability + audit needs.

## Acceptance Criteria

- The design is complete enough that Phase 08.1 controls can enforce it and an
  implementation phase could be scoped from it. *(No runtime acceptance — spec-only.)*

## Dependencies

Conceptually builds on Phases 0–8; consumed by Phase 08.1. No build dependency
(design-only).

## Open Questions

- **OQ-10-1** Retention periods per data class.
- **OQ-10-2** RPO/RTO targets.
- **OQ-10-3** Erasure vs immutable-raw (CC-2) / audit-log reconciliation.
- **OQ-10-4** Data-residency requirements + regions.

## Sub-phases

N/A (spec-only; break down if/when scheduled to build).
