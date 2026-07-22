# Phase 00.6 — Secrets Management

**Inserted phase** (standalone, not a sub-phase) · **Depends on:** Phase 0 ·
**Status:** Build — foundational.

Cross-cutting: secrets via store (CC-12), credential security (CC-10).

## Objective

Provide **one** abstraction through which *all* sensitive material flows — app
signing keys, auth/IdP secrets (Phase 00.5), partner OAuth tokens (Phase 9,
CC-10), and DB credentials — so nothing sensitive is ever stored in plaintext at
rest or written to logs (CC-12).

## Scope

- **In:** a `SecretStore` interface; a local **encrypted-dev** implementation
  (encrypted at rest with a key from the environment); a pluggable **KMS/vault**
  backend seam for later; a `secret_ref` pointer model (the DB stores *references*
  + metadata, never secret values).
- **Out:** the concrete managed KMS/vault integration (deferred — seam only); key
  material provisioning/rotation automation (design the policy, defer the plumbing).

## Functional Requirements

- **P0.6-1 Interface:** a `SecretStore` with `put` / `get` / `delete` / `rotate`
  over named, tenant-scoped (where applicable) secrets. Callers depend on the
  interface, never a concrete backend.
- **P0.6-2 No plaintext at rest:** secrets MUST be encrypted at rest; the dev
  backend encrypts with an env-provided key. The application DB stores only a
  `secret_ref` (pointer + metadata: type, scope, created/expiry), **never** the
  value.
- **P0.6-3 Never logged:** secret values MUST NOT appear in logs, errors, traces,
  or API responses (CC-10/CC-12).
- **P0.6-4 Pluggable backend:** the store MUST be swappable to a managed KMS/vault
  by config only, with no caller changes.
- **P0.6-5 Consumers:** Phase 00.5 auth secrets and Phase 9 partner credentials
  MUST use this store — no bespoke secret storage elsewhere.
- **P0.6-6 Rotation:** the interface MUST support rotation without breaking
  existing references (versioned secrets).

## Deliverables

- `SecretStore` interface + local encrypted-dev backend.
- `secret_ref` entity + migration (pointer/metadata only).
- Consumption hooks documented for Phase 00.5 and Phase 9.

## Acceptance Criteria

- A secret written via the store round-trips; the DB row holds only a reference,
  not the value.
- Secret values never appear in logs or API output (verified).
- Swapping the backend (dev → a stub KMS) requires config only, no caller edits.
- A rotated secret is retrievable by reference without breaking consumers.

## Dependencies

Phase 0 (DB, portability). Consumed by Phase 00.5 (auth) and Phase 9 (connectors).

## Open Questions

- **OQ-00.6-1** Dev backend choice (library + at-rest encryption scheme).
- **OQ-00.6-2** Target managed KMS/vault (e.g. cloud KMS vs HashiCorp Vault).
- **OQ-00.6-3** Key rotation policy (cadence, envelope encryption, re-wrap flow).

## Sub-phases

TBD — to be broken down before implementation.
