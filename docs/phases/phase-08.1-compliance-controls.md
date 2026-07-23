# Phase 08.1 — Compliance Controls

**Inserted phase** (standalone, not a sub-phase) · **Depends on:** Phase 8 ·
**Status:** Done (access review + least-privilege self-check + controls matrix) — pending PR merge. See [`../compliance-controls.md`](../compliance-controls.md). Certification remains an organizational process.

Cross-cutting: authenticated access (CC-11), secrets via store (CC-12), credential
security (CC-10), observability (CC-7).

> **Build the controls, not the certificate.** Certification (e.g. SOC 2 Type II)
> is an organizational **process** (auditor, evidence period, policies) — **not a
> build artifact**. This phase delivers the **technical controls** that make
> certification achievable. Cross-references — not duplicates — Phase 8
> (governance/RBAC/audit) and Phase 10 (data-governance policy).

## Objective

Implement the SOC 2-aligned **technical** controls: complete audit logging,
enforced encryption, access reviews, change-management traceability,
least-privilege verification, and secrets handling — so the platform is
audit-ready.

## Scope

- **In:** audit logging of sensitive actions; enforced encryption in transit + at
  rest; access-review tooling; change-management traceability; least-privilege
  verification; secrets via Phase 00.6.
- **Out:** the certification process itself; retention/DR/erasure **policy** (Phase
  10 designs these); the RBAC model (Phase 8 owns it — consumed here).

## Functional Requirements

- **P8.1-1 Audit logging:** all sensitive actions (auth events, permission changes,
  config/rule commits, credential access, data exports) MUST be recorded in an
  append-only audit log with actor + tenant + timestamp (extends Phase 8 audit).
- **P8.1-2 Encryption enforced:** TLS in transit and encryption at rest MUST be
  enforced (secrets via Phase 00.6; partner tokens per CC-10).
- **P8.1-3 Access reviews:** tooling MUST support periodic review of who has which
  role/access per tenant (least-privilege verification, ties to Phase 8 RBAC).
- **P8.1-4 Change-management traceability:** config/rule/mapping changes MUST be
  traceable to actor + version (reuses config-as-data versioning, CC-4).
- **P8.1-5 Least privilege:** default-deny access; verify no path grants more than
  required (integrates the Phase 00.5 authorization hook).
- **P8.1-6 Secrets handling:** all secret material MUST route through the
  `SecretStore` (CC-12); verified as part of controls.

## Deliverables

- Audit-log surface for sensitive actions (built on Phase 8 audit).
- Encryption-enforcement checks (transit + at rest).
- Access-review report + least-privilege verification tooling.
- A controls matrix mapping each control to its implementing phase.

## Acceptance Criteria

- Sensitive actions produce immutable audit entries with actor/tenant/time.
- Encryption in transit and at rest is verifiably enforced; no plaintext secrets.
- An access-review report lists per-tenant role assignments for review.
- Every config/rule change is attributable to an actor + version.

## Dependencies

Phase 8 (RBAC, audit baseline), Phase 00.5 (auth hook), Phase 00.6 (secrets).
Cross-references Phase 10 (governance policy).

## Open Questions

- **OQ-08.1-1** Target framework(s) — SOC 2 Type II (per PRD/OQ-8.1); any others
  (ISO 27001, GDPR-specific)?
- **OQ-08.1-2** Which controls are in-scope for v1 vs later.

## Sub-phases

TBD — to be broken down before implementation.
