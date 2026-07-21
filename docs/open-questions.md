# Open Questions

**Status:** Draft v0.1 (Appendix E of the Build Plan + questions surfaced during
repo initialization).
**Rule:** where an open question exists, **stop and ask rather than assuming**
(see [`../CLAUDE.md`](../CLAUDE.md), golden rule 4). Resolve the relevant
questions before implementing the phase they belong to.

---

## Appendix E — Consolidated Open Questions (from the source docs)

| ID | Question | Phase | Status |
|---|---|---|---|
| OQ-0.1 | Tenant isolation: row-level (`tenant_id`) vs schema/DB-per-tenant. Default recommendation is row-level (see ADR-003). | 0 | Open |
| OQ-0.2 | Warehouse choice for clean output (Postgres schema vs dedicated warehouse). | 0 | Open |
| OQ-1.1 | Max supported file size / row count for v1. | 1 | Open |
| OQ-1.2 | Behaviour when a sheet has multiple header-like rows (pick vs ask). | 1 | Open |
| OQ-2.1 | Column-signature definition (exact names vs fuzzy vs position-tolerant). | 2 | Open |
| OQ-2.2 | Required vs optional canonical fields / measures for v1. | 2 | Open |
| OQ-3.1 | How far the `custom` escape-hatch rule goes (expression language? sandboxed code? none for v1?). | 3 | Open |
| OQ-3.2 | Reshape (wide→long) rules — exact configuration model. | 3 | Open |
| OQ-4.1 | Default severity / blocking policy (what blocks vs warns). | 4 | Open |
| OQ-4.2 | Anomaly method for v1 (simple z-score / IQR vs more). | 4 | Open |
| OQ-5.1 | LLM provider / model + cost ceiling per file. | 5 | Open |
| OQ-5.2 | Confidence calibration approach. | 5 | Open |
| OQ-6.1 | Design system / component library. | 6 | Partially addressed — the front-end adopts the design language extracted from the reference UI (`front-end/CLAUDE.md`); confirm whether to formalize a component library on top. |
| OQ-7.1 | Queue tech (Celery vs RQ vs managed) and worker hosting. | 7 | Open |
| OQ-8.1 | Target compliance framework (e.g. SOC 2) and required controls. | 8 | Open |

---

## Questions surfaced during repository initialization

These were raised while scaffolding the repo. They are documented here rather
than assumed; confirm before the relevant phase.

| ID | Question | Phase | Status |
|---|---|---|---|
| OQ-INIT.1 | Object-storage provider and local-dev substitute (e.g. S3 vs GCS vs MinIO / local filesystem for dev). Needed before Phase 1's immutable raw-file store. | 1 | Open |
| OQ-INIT.2 | Whether the clean-output "warehouse" is, for v1, just a table in the backend database (SQLite→Postgres) or a separate system. Overlaps OQ-0.2; affects the `output_row` entity. | 0/1 | Open |
| OQ-INIT.3 | Whether the UI (Prisma) database stores anything beyond front-end concerns (e.g. session/UI state) or remains effectively empty until Phase 6. Currently scaffolded empty. | 6 | Open |
| OQ-INIT.4 | LLM provider/SDK choice and how credentials are injected (env only) — narrower than OQ-5.1 but blocks the `ai/` package wiring. | 5 | Open |

---

## Decisions already locked (for reference)

These are **not** open — they were decided during initialization and are recorded
in [`architecture.md`](./architecture.md):

- Two independent databases (backend + UI), each SQLite now / Postgres later, swappable by config only (ADR-001, ADR-002).
- Python targets **3.10+**; code must run on 3.10.
- Backend uses SQLAlchemy 2.0 + Alembic (batch mode + MetaData naming convention); UI uses Prisma.
- Front-end design language is replicated from the reference UI (see `front-end/CLAUDE.md`).

---

_Living document — move a row's status to "Resolved (see …)" with a pointer when
a question is answered._
