# Phase 2.1 — Mapping Engine (signature + apply + validation)

**Parent:** [`phase-02`](./phase-02-mapping-engine-saved-configs.md) ·
**Depends on:** Phases 0–1 · **Status:** Done (pending PR merge)

Covers **P2-1**, **P2-5** and realises OQ-2.1 (column signature) and OQ-2.2
(required fields).

## Objective

The pure engine that maps a sheet's detected columns to canonical fields, computes
a reusable **column signature**, and validates that required canonical fields are
mapped — with no persistence or API (that is 02.2).

## Scope

- **In:** column-signature function; apply a mapping (source column → canonical
  field, or ignore) to detected columns; required-field validation.
- **Out:** saved configs, matching, layered resolution, API (02.2); value-level
  transformation (Phase 3).

## Functional Requirements

- **P2.1-1 Column signature (OQ-2.1):** compute a signature from a sheet's columns as the **normalized set of header names** (lowercased, trimmed, whitespace/punctuation-collapsed), order-tolerant; equal sets produce equal signatures.
- **P2.1-2 Apply mapping (P2-1):** given detected columns and a mapping `{source_name: canonical_field | null}`, produce the mapped columns, the ignored columns, and any targets that are not valid canonical fields.
- **P2.1-3 Required validation (P2-5, OQ-2.2):** report missing required canonical fields — required dimensions (`date`, `channel`) and at least `measure_policy.min_required` measures. A mapping with any missing required field is **incomplete** (blocks output).
- **P2.1-4 Canonical-driven:** valid targets are read from the canonical schema (00.1), never hardcoded.

## Deliverables

- `src/mmm_os/mapping/signature.py` — `normalize_name`, `column_signature`.
- `src/mmm_os/mapping/engine.py` — `apply_mapping`, `MappingResult` (mapped / ignored / invalid / missing_required / is_complete).
- Tests: signature order-tolerance + normalization; apply mapping; required validation.

## Acceptance Criteria

- Two sheets with the same header names in different order produce the **same** signature.
- Applying a mapping yields the correct mapped/ignored/invalid partition.
- A mapping missing `channel` (or with no measure) is reported incomplete; a mapping with `date` + `channel` + ≥1 measure is complete.
- Valid canonical targets come from the schema config.

## Dependencies

Phases 0 (canonical schema) and 1 (detected `sheet.columns`).

## Open Questions

None outstanding (OQ-2.1, OQ-2.2 resolved).

## Sub-phases

N/A (leaf sub-phase).
