# Phase 11 — Deployment & Infrastructure

**Tail phase** · **Depends on:** Phases 0–8 · **Status:** Spec-only — **design
only, not scheduled to build.**

> **Design-only.** Documents the deployment/infra approach; **not** scheduled for
> implementation. Keep the two-DB strategy and portability rules intact.

## Objective

Design how the platform is deployed and operated: environments, CI/CD,
infrastructure-as-code, hosting, worker autoscaling, containers, and secret
injection at deploy time.

## Scope

- **In (design):** dev/stage/prod environments; CI/CD pipeline; infrastructure-as-
  code; hosting model; worker autoscaling (Celery, ADR-007); container strategy;
  deploy-time secret injection (via Phase 00.6 `SecretStore`).
- **Out:** implementation; the Postgres migration (separate, Deferred — portability
  already designed).

## Functional Requirements (design targets)

- **P11-1 Environments:** SHOULD define dev/stage/prod with parity and promotion.
- **P11-2 CI/CD:** SHOULD define the pipeline (lint/type/test gates already exist:
  ruff/mypy/pytest; add build/deploy) and release flow.
- **P11-3 IaC:** SHOULD define infrastructure-as-code for reproducible provisioning.
- **P11-4 Autoscaling:** SHOULD define worker autoscaling + per-tenant fairness
  (extends Phase 7/ADR-007).
- **P11-5 Containers:** SHOULD define the container/image strategy for API + workers
  + front-end.
- **P11-6 Secret injection:** SHOULD define how secrets are injected at deploy
  without landing in images/logs (Phase 00.6, CC-12).

## Deliverables (design artifacts)

- Environment + promotion design.
- CI/CD + IaC + container strategy notes.
- Autoscaling + secret-injection design.

## Acceptance Criteria

- The design is sufficient to scope an implementation phase and stand up
  environments. *(No runtime acceptance — spec-only.)*

## Dependencies

Builds conceptually on all prior phases; relies on Phase 00.6 for secret injection
and ADR-007 for workers. No build dependency (design-only).

## Open Questions

- **OQ-11-1** Hosting/cloud target + container orchestration.
- **OQ-11-2** IaC tooling.
- **OQ-11-3** CI/CD platform + release/rollback strategy.

## Sub-phases

N/A (spec-only; break down if/when scheduled to build).
