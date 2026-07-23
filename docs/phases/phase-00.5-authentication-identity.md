# Phase 00.5 — Authentication & Identity

**Inserted phase** (standalone, not a sub-phase) · **Depends on:** Phase 0 ·
**Status:** Done (password auth + sessions + endpoint guard + seed; MFA/SSO deferred) — pending PR merge.

> **Delivered now:** email/password login (PBKDF2), DB-backed sessions (tokens
> stored hashed via the SecretStore, CC-12), a `require_auth` guard on every
> feature router (enforced when `AUTH_ENABLED=true`), and a seeded default admin
> (`admin` / `admin123`). **Deferred to a follow-up:** MFA, OIDC/SAML SSO, and
> moving `tenant_id` out of the URL path onto the session.

Cross-cutting: multi-tenant (CC-1), authenticated access (CC-11), secrets via
store (CC-12).

> **Scope boundary:** this is **application-level** identity and access — who may
> use the platform. It is distinct from **partner-connector credentials** (Phase 9,
> CC-10), which are third-party API tokens. Both store their secrets through the
> `SecretStore` (Phase 00.6).

## Objective

Give every request an authenticated, tenant-scoped identity so no API endpoint is
reachable anonymously (CC-11) and every query is naturally tenant-isolated (CC-1).
Provide enterprise sign-in (SSO/MFA) so a tenant can bring its own IdP.

## Scope

- **In:** tenant-user model; email/password auth (secure hashing, sessions, secure
  cookies/tokens, logout, password reset); MFA; SSO via OIDC + SAML (pluggable
  per-tenant IdP); an authorization hook on every endpoint; a portable
  session/token store.
- **Out:** the RBAC role *definitions* and permission matrix (Phase 8 — this phase
  provides the hook that consumes them); partner-connector credentials (Phase 9);
  the Review-UI screens that sit on top (Phase 6).

## Functional Requirements

- **P0.5-1 Tenant-user model:** users belong to a `tenant`; every authenticated
  request MUST carry a resolved `(user, tenant_id)` and MUST be tenant-scoped (CC-1).
- **P0.5-2 Password auth:** email/password with a strong adaptive hash (e.g.
  bcrypt/argon2); session management; secure, http-only, same-site cookies or
  signed tokens; explicit logout; secure password-reset flow (expiring,
  single-use tokens).
- **P0.5-3 MFA:** users MUST be able to enrol a second factor; MFA-required tenants
  MUST be enforceable.
- **P0.5-4 SSO:** SHOULD support **OIDC** and **SAML** for enterprise IdPs,
  **pluggable per tenant** (a tenant configures its own IdP; local login can be
  disabled per tenant).
- **P0.5-5 Authorization hook:** every API endpoint MUST require authenticated +
  authorized access; the hook integrates with Phase 8 RBAC roles (deny by default).
- **P0.5-6 Portable session/token store:** the session/token store MUST work on
  SQLite now and port to Postgres by config only (dialect-agnostic types, no raw
  dialect SQL — see architecture portability rules).
- **P0.5-7 Secrets:** signing keys, IdP client secrets, and password-reset secrets
  MUST flow through the `SecretStore` (Phase 00.6, CC-12); never plaintext at rest,
  never logged.

## Deliverables

- Tenant-user auth model + migration (`user`, `session`, `identity_provider_config`).
- Password login/logout/reset + MFA + session middleware.
- OIDC/SAML integration behind a pluggable provider interface.
- An endpoint authorization dependency wired into the API layer.

## Acceptance Criteria

- An unauthenticated request to any protected endpoint is rejected (401/403).
- A logged-in user only ever sees their own tenant's data (verified by a
  cross-tenant access test).
- Password reset and MFA enrolment/challenge work end-to-end.
- A tenant can be configured to sign in via an external OIDC (and SAML) IdP.
- Switching the backend DB URL to Postgres requires no auth-code changes.

## Dependencies

Phase 0 (tenant model, DB, portability). Phase 00.6 (SecretStore) for secret
material. **Phase 6 (Review UI) and all API phases depend on this.** RBAC role
definitions arrive in Phase 8 (this phase ships the enforcement hook).

## Open Questions

- **OQ-00.5-1** Session store choice (DB-backed sessions vs signed stateless tokens vs both).
- **OQ-00.5-2** OIDC/SAML library selection (maintained, audited).
- **OQ-00.5-3** Per-tenant IdP config model (discovery URL, cert rotation, attribute mapping).
- **OQ-00.5-4** MFA method(s) for v1 (TOTP vs WebAuthn vs email/SMS OTP).

## Sub-phases

TBD — to be broken down before implementation.
