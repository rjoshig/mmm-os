# Phase 19 — RBAC Enhancements + Role Management UI

**Depends on:** 00.5 (auth), 8 (RBAC + audit), 6 (Admin console)
· **Status:** Build · **Cycle:** 5 (Usability, Reuse & Model-Readiness)

Cross-cutting: authenticated access (CC-11), multi-tenant (CC-1), audit (CC-5/audit).

See the umbrella design: [`../design/usability-reuse-model-readiness.md`](../design/usability-reuse-model-readiness.md) §4.6.

## Objective

Strengthen access control with a distinct **approver** role, a **platform-admin**
role, an optional **approve/publish** permission, and a **role-management UI** —
keeping the model small, documented, and deny-by-default.

## Scope

- **In:** new roles (`approver`, `platform_admin`); an optional `APPROVE` permission
  distinct from `WRITE_CONFIG`; a role-management UI in the Admin console; keeping
  the role→permission matrix small and audited.
- **Out:** custom per-resource ACLs / attribute-based access (deferred to avoid role
  explosion); SSO/SCIM provisioning (Phase 00.5 extension, tracked separately).

## Cross-cutting

- **CC-11** every endpoint stays authenticated + tenant-authorized; new roles slot
  into the existing `require_permission` matrix (`authz.py`), deny-by-default.
- **CC-1** roles are tenant-scoped (a `platform_admin` in one tenant is not elevated
  in another).
- **audit** role changes are written to `audit_log` (actor, target, before/after).

## Functional Requirements

- **P19-1 Approver role** — a role with `review`/publish rights but **not**
  `write_config`, so segregation of duties is possible (author ≠ approver).
  Extends `ROLE_PERMISSIONS` in `authz.py`.
- **P19-2 Platform-admin role** — a role for customer/tenant management, replacing
  the current reuse of `ADMIN` for customer management (documented follow-up at
  `api/routers/customers.py`). Scoped and audited.
- **P19-3 Approve/publish permission (optional)** — an `APPROVE` permission
  distinct from `WRITE_CONFIG` for draft→publish and Stack-publish gating (ties to
  Phase 16/13). Behind a decision on whether to split now (OQ-19.1).
- **P19-4 Small matrix** — keep to ≤6 roles; document each role's purpose and its
  permission set so two roles are never ambiguous.
- **P19-5 Role-management UI** — in the Admin console (`app/admin/page.tsx` Users
  tab): assign/change a user's role, view the role→permission matrix, and see
  per-user audit. `admin`/`platform_admin` gated.

## Deliverables

- Extended `ROLE_PERMISSIONS` (+ `APPROVE` permission if adopted) in `authz.py`,
  with tests proving least-privilege (Phase 08.1 self-check still holds).
- Role-management endpoints (assign role; read matrix) — RBAC-gated, audited.
- Admin-console role-management UI.
- Docs: role catalog + permission matrix in this spec + data-model/authz docs.

## Acceptance Criteria

- An `approver` can publish/approve but cannot author configs; a `member` can author
  but (if `APPROVE` is split) cannot self-publish — per policy.
- A `platform_admin` can manage customers; a plain `admin` scope is unchanged.
- Assigning a role writes an audit entry; a viewer cannot change roles (403).
- The 08.1 least-privilege self-check passes (no role exceeds `admin`).
- Backend `ruff`/`mypy`/`pytest` and front-end `typecheck`/`lint`/`build` pass.

## Dependencies

Phase 00.5, Phase 8, Phase 6; coordinates with Phase 16 (Stack publish permission).

## Open Questions

- **OQ-19.1** approve/publish as a permission distinct from `write_config` — adopt
  now (enables author≠approver) or keep collapsed? Default: add `approver` role now;
  make the second-approver requirement a per-tenant setting (parallels OQ-13.1).

## Sub-phases

TBD (per the sub-phase convention in [`README.md`](./README.md)).
