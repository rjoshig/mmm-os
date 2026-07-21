# Phase 2 — Mapping Engine & Saved Configs

**Depends on:** Phases 0–1 · **Status:** Not started · **MVP:** yes (Phases 0–4)

Cross-cutting: config-as-data (CC-4), traceability (CC-3), multi-tenant (CC-1).

## Objective

Map a sheet's detected columns to the canonical schema, and make that mapping
**reusable** so future files of the same type auto-map.

## Scope

- **In:** column→canonical-field mapping; layered saved configs
  (global/template/customer); config reuse/matching; versioning.
- **Out:** value-level transformation (Phase 3), AI suggestions (Phase 5).

## Functional Requirements

- **P2-1 Column mapping:** map each source column to a canonical field ([`../canonical-schema.md`](../canonical-schema.md), Appendix A) or mark as ignored.
- **P2-2 Saved config:** persist a mapping as a `mapping_config` keyed by **tenant + file-type/signature**, versioned.
- **P2-3 Config matching:** on a new file, detect whether an existing config matches its structure (column signature) and auto-apply it; otherwise flag as needs-mapping.
- **P2-4 Layered resolution:** resolve mappings in precedence order — **customer override > template > global default** — merged at runtime.
- **P2-5 Unmapped handling:** required canonical fields with no mapping MUST block output and be surfaced clearly.
- **P2-6 Re-map:** user can edit a saved config; a new version is created; prior outputs remain traceable to the version used.

## Deliverables

- Mapping engine (apply config → produce canonically-keyed table).
- `mapping_config` storage with versioning + layered resolution.
- Column-signature matcher for config reuse.

## Acceptance Criteria

- Manually map a file once → save config → upload a same-structure file → config auto-applies with no manual step.
- Change a source file's column order/names slightly → matcher either matches (if signature tolerant) or flags for review per defined rules.
- A missing required field blocks output with a clear message.
- Editing a config creates v2; a re-run of an old job still references v1.

## Dependencies

Phases 0–1.

## Open Questions

- **OQ-2.1** Column-signature definition (exact names vs fuzzy vs position-tolerant).
- **OQ-2.2** Required vs optional canonical fields for v1 (see Appendix A).

## Sub-phases

TBD — to be broken down before implementation.
