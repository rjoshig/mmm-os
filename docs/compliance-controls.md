# Compliance Controls Matrix (Phase 08.1)

The **technical** controls backing a SOC 2-aligned posture. **Certification itself
is an organizational process** (auditor, evidence period, policies) — this document
+ the code it references make the posture **auditable**. Generated from
`src/mmm_os/governance/compliance.py` (`controls_matrix()`), with a
least-privilege self-check (`verify_least_privilege()`).

| Control | Description | Implemented by |
|---|---|---|
| AC-1 | Authenticated access to every endpoint | Phase 00.5 (CC-11) |
| AC-2 | Role-based least-privilege authorization | Phase 8 (P8-1) |
| AU-1 | Audit log of sensitive actions | Phase 8 (P8-2) |
| AU-2 | Per-job event timeline + metrics | Phases 1 / 07.1 (CC-7) |
| SC-1 | Secrets encrypted at rest, never logged | Phase 00.6 (CC-12) |
| SC-2 | Partner credentials encrypted + tenant-scoped | Phase 9 (CC-10) |
| CM-1 | Config/rule changes versioned + attributable | Phases 2/3 + 8 (CC-4) |
| SI-1 | Idempotent, retry-safe processing | Phases 1 / 07.2 (CC-6) |
| DI-1 | Row-level tenant isolation | Phases 0 / 7 (CC-1) |

## Enforced now

- **Authentication (AC-1):** `require_auth` guards every feature router; enforced
  when `AUTH_ENABLED=true` (Phase 00.5).
- **Authorization (AC-2):** deny-by-default role→permission matrix + `require_permission`;
  admin routes gate on `Permission.ADMIN`. A **least-privilege self-check** asserts
  no role exceeds `admin`.
- **Audit (AU-1):** `record_audit` writes append-only entries for logins, mapping/
  rule saves, flag reviews, and suggestion accept/reject; admins read them at
  `GET /tenants/{id}/audit-log`.
- **Access review:** `GET /tenants/{id}/access-review` lists each user's role +
  effective permissions.
- **Secrets (SC-1):** all secret material flows through the `SecretStore`
  (encrypted at rest, never logged, Phase 00.6).

## Deferred / process (not code)

- Encryption **in transit** (TLS) is a deployment concern (Phase 11).
- The managed KMS/vault backend (SC-1 hardening) is deferred (OQ-00.6-2).
- The SOC 2 audit engagement, policies, and evidence collection are organizational
  (OQ-08.1-1) — this matrix supports them.
