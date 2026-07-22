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
into "a source". These entities are **documented now but not yet ORM-modelled** —
they are built in [Phase 9](./phases/phase-09-future-connectors-extraction.md).
The **realised code seam exists today** (`src/mmm_os/sources/`): the common landed
representation is a `LandedDataset`, and for **file sources** it is already
persisted via the existing `file` / `sheet` / `profile` records.

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
