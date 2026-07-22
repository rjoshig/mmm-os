# Phase 0.1 — Canonical Schema & Taxonomies (machine-readable + loader)

**Parent:** [`phase-00`](./phase-00-foundations-canonical-schema-data-model.md) ·
**Depends on:** — · **Status:** Done (pending PR merge)

Covers Phase-0 requirements **P0-1** and **P0-2**.

## Objective

Encode the canonical schema and standard taxonomies as **machine-readable,
versioned config** that the application loads and **validates at startup** — never
hardcoded. This is the fixed target contract everything else resolves to.

## Scope

- **In:** `canonical_schema.yaml` + `taxonomies.yaml` resource files; typed
  models describing their structure; a loader that parses + validates them;
  startup wiring that fails fast on invalid config.
- **Out:** ORM tables/migrations (00.2), tenancy + config versioning (00.3), any
  ingestion/mapping/transform logic.

## Functional Requirements

- **P0.1-1** Ship `canonical_schema.yaml` encoding Appendix A ([`../canonical-schema.md`](../canonical-schema.md)): dimensions, measures, metadata fields, each with `name`, `type`, `required`, optional `taxonomy` and `notes`; plus a `measure_policy` (`min_required`).
- **P0.1-2** Ship `taxonomies.yaml` encoding Appendix B: controlled vocabularies (`channel`, `funnel_stage`, `geo`, `currency`) with `terms` and `aliases` (synonym → canonical term).
- **P0.1-3** Define typed (Pydantic v2) models for both files; parsing MUST reject structurally invalid config with a clear error.
- **P0.1-4** Cross-validate: every field whose `type` is `enum` MUST reference a `taxonomy` that exists in `taxonomies.yaml`.
- **P0.1-5** Encode the resolved required set (OQ-2.2): `date` + `channel` required, `measure_policy.min_required = 1`. A helper exposes required dimensions/measures.
- **P0.1-6** Load + validate **at application startup**; invalid config MUST prevent boot (fail fast), not degrade silently.
- **P0.1-7** Both files carry a `version`; alias lookup is case-insensitive and returns the canonical term.

## Deliverables

- `src/mmm_os/resources/canonical_schema.yaml`, `src/mmm_os/resources/taxonomies.yaml`.
- `src/mmm_os/canonical/` — typed models + loader + validation.
- Startup hook (FastAPI) that loads & validates, exposing the parsed schema on app state.
- Tests: valid config loads; a malformed schema and an enum-without-taxonomy each raise.

## Acceptance Criteria

- App boots and loads + validates the shipped canonical schema and taxonomies.
- `date` and `channel` are required; `measure_policy.min_required == 1`.
- An enum field referencing a missing taxonomy fails validation with a clear message.
- Alias lookup collapses `FB`/`fb_ads`/`facebook ads` → `Facebook` (case-insensitive).
- Nothing about the schema is hardcoded in Python — it is read from the YAML.

## Dependencies

None (first sub-phase of Phase 0).

## Open Questions

None outstanding (OQ-2.2 resolved). Date-granularity and wide-vs-long measure
representation remain open at the *schema-design* level (see canonical-schema A.4)
but do not block this loader.
