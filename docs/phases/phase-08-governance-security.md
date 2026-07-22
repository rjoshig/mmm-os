# Phase 8 — Governance & Security

**Depends on:** Phase 7 · **Status:** Not started

Cross-cutting: multi-tenant (CC-1), traceability/audit (CC-3, CC-7).

## Objective

Meet enterprise requirements: roles, audit, encryption, compliance posture.

## Scope

- **In:** RBAC; audit logging; encryption at rest/in transit; access-scoped
  configs; admin UI.
- **Out:** external compliance certification (process, not build).

## Functional Requirements

- **P8-1 RBAC:** admin-controlled roles determining who can view/edit/approve within a tenant.
- **P8-2 Audit log:** every config change, approval, override, and data export recorded (who/what/when).
- **P8-3 Encryption:** data encrypted at rest and in transit.
- **P8-4 Access-scoped output:** users see only what their role permits.
- **P8-5 Admin UI:** manage users, roles, and view audit trail.

## Deliverables

- RBAC + audit + encryption + admin UI.

## Acceptance Criteria

- A viewer-role user cannot edit configs or approve suggestions.
- Every sensitive action appears in the audit log.
- Data verified encrypted at rest and in transit.

## Dependencies

Phase 7.

## Open Questions

- **OQ-8.1** — ⏸️ Deferred: working target **SOC 2 Type II** (per PRD); specific controls/scope to be confirmed with legal before this phase.

See [`../open-questions.md`](../open-questions.md) for status.

## Sub-phases

TBD — to be broken down before implementation.
