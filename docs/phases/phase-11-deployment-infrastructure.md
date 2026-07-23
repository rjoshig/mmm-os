# Phase 11 — Deployment & Infrastructure

**Tail phase** · **Depends on:** Phases 0–8 · **Status:** Built (containers + CI/CD
+ runbook) — hosting/IaC target still open.

> **Now built:** the container strategy, CI/CD image builds, a prod-like compose
> stack, and an operations runbook are implemented (see below). The concrete
> cloud/IaC target (OQ-11-1/11-2) remains open and is chosen at deploy time. Keep
> the two-DB strategy and portability rules intact.

## Implemented artifacts

- **Containers (P11-5):** `Dockerfile` (API/worker, uv + Postgres driver, non-root,
  migrate-then-serve `deploy/entrypoint.sh`) and `front-end/Dockerfile` (Next.js
  standalone). `.dockerignore` keeps images lean + secret-free.
- **CI/CD (P11-2):** `.github/workflows/ci.yml` gains a **container-images** job
  (builds both Dockerfiles with buildx + GH cache) alongside the SQLite backend,
  Postgres portability, and front-end jobs.
- **Prod-like stack:** `docker-compose.yml` wires Postgres + API + front-end for
  parity testing (`docker compose up --build`).
- **Secret injection (P11-6):** all config via env; secrets via the `SecretStore`;
  documented in the runbook — never baked into images or logs.
- **Runbook:** [`deploy/RUNBOOK.md`](../../deploy/RUNBOOK.md) — environments +
  promotion, required env, secret injection, **enterprise silo provisioning**
  (ties to Slice 7.2/7.6), autoscaling/workers (ADR-007), health + rollout.

Still open (design-time choices, not code): the specific cloud/orchestrator
(OQ-11-1), IaC tooling (OQ-11-2), and managed CI/CD platform + release automation
(OQ-11-3).

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
