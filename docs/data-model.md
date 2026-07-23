# Data Model & Rule Schema

**Status:** Draft v0.1 (Appendix C + Appendix D of the Build Plan).
**Role:** the entity list and declarative rule shape the platform persists.
Created in Phase 0 (P0-3). Every domain table MUST carry `tenant_id` (CC-1), and
config entities (`mapping_config`, `rule_set`) MUST be **versioned** (CC-4, P0-5).

> **Portability note:** models are implemented with **dialect-agnostic**
> SQLAlchemy 2.0 types (see [`../CODING_STANDARDS.md`](../CODING_STANDARDS.md) and
> [`architecture.md`](./architecture.md)). No tables exist yet — they are defined
> in Phase 0.

---

## Appendix C — Data Model (draft entity list)

Core tables (all tenant-scoped where applicable):

| Entity | Purpose | Key notes |
|---|---|---|
| `tenant` | Customer org. | Root of tenant isolation (CC-1). |
| `user` | Belongs to a tenant; has a role. | Role enforcement lands in Phase 8. |
| `file` | Raw uploaded file metadata + object-storage pointer. | **Immutable** (CC-2). |
| `sheet` | A sheet within a file; header location; status. | One `file` → many `sheet`. |
| `profile` | Per-sheet column stats / distinct values / samples. | The **AI input** (Phase 5) — distinct values + stats, never raw dumps. |
| `mapping_config` | Tenant + file-signature → column→canonical mapping. | **Versioned**; layered (global/template/customer). |
| `taxonomy` / `taxonomy_alias` | Controlled vocab + synonyms. | Aliases collapse raw values (Appendix B). |
| `rule_set` | Ordered set of transformation rules. | **Versioned**; layered (global/template/customer). |
| `rule` | Individual declarative rule. | See Appendix D. |
| `job` | A processing run over a file/batch; status. | Async-ready from Phase 0. |
| `job_event` | Per-stage status/timing/errors. | Observability (CC-7). |
| `validation_flag` | Issue found; severity; location; review status. | Phase 4 lifecycle. |
| `suggestion` | AI suggestion + confidence + rationale + accept/reject state. | Phase 5; human-in-the-loop (CC-5). |
| `output_row` | Clean canonical data with traceability metadata. | Traceability (CC-3). **v1 = a table in the backend DB** (SQLite→Postgres); dedicated warehouse deferred (ADR-005). |

**Relationships (high level):**
- `tenant` 1—* `user`, `file`, `mapping_config`, `rule_set`, `job`, …
- `file` 1—* `sheet`; `sheet` 1—1 `profile`.
- `job` 1—* `job_event`; `job` 1—* `validation_flag`; `job` 1—* `suggestion`.
- `rule_set` 1—* `rule`.
- `output_row` references `source_file_id`, `source_sheet`, `source_row`,
  `mapping_config_version`, `rule_set_version` for full traceability.

---

## Appendix C.1 — Source & Connector entities (documented for Phase 9)

The source-agnostic ingestion abstraction (CC-9, ADR-010) generalises "a file"
into "a source". The `connector_config`, `connector_credential`, and `sync_run`
entities are **now real ORM** (`src/mmm_os/models/connectors.py`, Phase 9); the
`source`/`connector` catalog rows below remain conceptual (the `connector_key`
string on `connector_config` plays the catalog role). The **realised code seam**
(`src/mmm_os/sources/`) produces the common `LandedDataset`, and for **file
sources** it is already persisted via the existing `file` / `sheet` / `profile`
records; API pulls realise it as normalised rows via the partner templates.

| Entity | Purpose | Key notes |
|---|---|---|
| `source` | Generalised inbound source. | `type ∈ {upload, sftp, api_connector}`. The existing `file` is the `upload`/`sftp` realisation; API pulls realise `api_connector`. Tenant-scoped. |
| `landed_dataset` | The common post-ingestion representation both files and API pulls produce; what downstream phases consume. | For file sources, **realised by the existing `file`→`sheet`→`profile`** entities. For API sources, realised by normalised rows. Not a new table for file sources. |
| `connector` | Catalog of partner types. | `{meta, google_ads, dv360, tiktok, sftp}`. Ships default mapping/taxonomy templates (Phase-2 template layer). |
| `connector_config` | Per tenant + connector settings. | Account IDs, metrics/dimensions, currency, timezone, lookback window, backfill range, schedule. Tenant-scoped. |
| `connector_credential` | Encrypted tokens/secrets, scopes, expiry. | **Kept separate from config for security** — encrypted at rest, tenant-scoped, least-privilege, **never logged** (CC-10). |
| `sync_run` | One partner pull. | `connector_config` ref, requested window, status, row counts, errors, started/finished timestamps. Observability (CC-7); idempotent re-pull (CC-6). |

**Traceability (CC-3), generalised:** landed data and every `output_row` MUST
trace back to the `source` (and, for API pulls, the `sync_run`) they came from —
the source-agnostic generalisation of "source file + sheet + row". For file
sources this is the existing `source_file_id`/`source_sheet`/`source_row` chain.

**Relationships (high level, Phase 9):**
- `tenant` 1—* `source`, `connector_config`.
- `connector` 1—* `connector_config`; `connector_config` 1—1 `connector_credential`.
- `connector_config` 1—* `sync_run`; `sync_run` 1—* `landed_dataset` (→ downstream).

---

## Appendix C.2 — Identity, secrets & usage entities

Added for the enterprise-readiness phases (authentication 00.5, secrets 00.6, LLM
cost controls 05.1, compliance 08.1). Tenant-scoped where applicable; portable
types only. The core `user` entity (Appendix C) is **extended**, not replaced.

| Entity | Purpose | Key notes |
|---|---|---|
| `user` *(extends Appendix C)* | Tenant-scoped account. | Add auth fields: password hash, MFA enrolment, status. Every request resolves to `(user, tenant_id)` (CC-1, CC-11). |
| `session` | Active login session / token record. | Portable store (SQLite→Postgres by config); supports logout/expiry. Phase 00.5. |
| `identity_provider_config` | Per-tenant SSO config. | OIDC/SAML settings (issuer, client, cert, attribute mapping); **secrets via `secret_ref`**, not inline. Phase 00.5. |
| `role` / `user_role` | RBAC roles + assignments. | **Coordinate with Phase 8** (governance owns the role/permission model); the 00.5 auth hook enforces them. Tenant-scoped. |
| `llm_usage` | Per-tenant LLM metering. | Tokens/calls attributed to `tenant_id` (+ job/suggestion); drives budgets/caps (CC-13) and observability. Phase 05.1. |
| `secret_ref` | Pointer + metadata for a stored secret. | **Never the secret value** — type, scope, created/expiry only; the value lives in the `SecretStore` (CC-12). Phase 00.6. |
| `audit_log` *(Phase 8/08.1)* | Append-only record of sensitive actions. | Actor + tenant + timestamp; auth events, permission/config/credential changes, exports. |

**Relationships (high level):**
- `tenant` 1—* `user`, `session`, `identity_provider_config`, `llm_usage`, `role`.
- `user` 1—* `session`; `user` *—* `role` via `user_role`.
- `secret_ref` is referenced by `identity_provider_config` and by
  `connector_credential` (Appendix C.1) — the value is never stored in the DB (CC-12).

---

## Appendix C.3 — Collaboration & multi-user workflow entities (Phase 13)

Scoped for [Phase 13](./phases/phase-13-collaboration-multiuser-workflow.md)
(collaboration & multi-user workflow). Tenant-scoped, portable types only. Concrete
columns are fixed in each sub-phase spec at build time; this is the entity map.

| Entity | Purpose | Key notes |
|---|---|---|
| `mapping_config` / `rule_set` *(extend Appendix C)* | Existing versioned configs. | Add `created_by` / `updated_by` (nullable user refs) and a `status` (`draft`/`published`/`archived`); resolution reads the latest **published** version (CC-4). Phase 13.1/13.2. |
| `assignment` | A unit of work assigned to a user. | `target_type` (`file`/`sheet`/`flag_cluster`) + `target_id` → `assignee` user; drives "Assigned to me" / "Needs review" queues. Tenant-scoped. Phase 13.4. |
| `comment` | In-context note / thread on an object. | `target_type` + `target_id` (flag/mapping/file), author, body, optional `@mention` refs; feeds the per-file activity feed. Phase 13.5. |
| `notification` | In-app notification for a user. | Kind (mention/assignment/publish-request), target ref, read/unread; pluggable delivery sink (email/webhook later, honoring CC-10/CC-12). Phase 13.5. |

**Relationships (high level):**
- `tenant` 1—* `assignment`, `comment`, `notification`.
- `user` 1—* `assignment` (assignee), `comment` (author), `notification` (recipient);
  `user` authors `mapping_config` / `rule_set` versions via `created_by`/`updated_by`.
- Every collaborative action is also written to `audit_log` (Appendix C.2) with actor
  + target (CC-5).

---

## Appendix D — Rule Schema (draft)

Each transformation is stored as **data**, not code (CC-4). A rule:

```
Rule:
  id: uuid
  rule_set_id: uuid
  target_field: canonical field or source column
  operation: one of {map_value, rename_column, cast_type, parse_date,
                     convert_currency, dedupe, reshape, fill_missing,
                     normalize_text, custom}
  params: object            # operation-specific
  condition: object | null  # optional predicate (when to apply)
  order: int                # deterministic application order
  layer: {global | template | customer}
```

**Resolution:** customer overrides template overrides global. Rules apply in
`order`. Output MUST be **deterministic + idempotent** (CC-6).

**Operation library (v1)** — see [`phases/phase-03-transformation-rule-engine.md`](./phases/phase-03-transformation-rule-engine.md):
`map_value`, `rename_column`, `cast_type`, `parse_date`, `convert_currency`,
`dedupe`, `reshape` (wide→long), `fill_missing`, `normalize_text`, plus a
`custom` escape hatch. **OQ-3.1 resolved:** the `custom` op's payload is a
**sandboxed expression language** (restricted DSL over the row/field context; no
arbitrary code, imports, or I/O; allowlisted ops; resource-bounded) — see
ADR-004. Adding a capability = adding a new operation handler, not rewriting per
customer.

---

_Living document — the authoritative ORM models + migrations are produced in
Phase 0; this doc mirrors and explains them._
