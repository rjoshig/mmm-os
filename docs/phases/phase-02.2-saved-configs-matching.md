# Phase 2.2 — Saved Configs, Matching & Layered Resolution

**Parent:** [`phase-02`](./phase-02-mapping-engine-saved-configs.md) ·
**Depends on:** 02.1 · **Status:** Done (pending PR merge)

Covers **P2-2, P2-3, P2-4, P2-6**.

## Objective

Persist mappings as reusable, versioned `mapping_config` records; auto-apply a
saved config to a new sheet by column signature; merge layered configs; and expose
it via the API.

## Scope

- **In:** save a sheet's mapping (versioned, keyed by tenant + signature); find a
  matching config for a new sheet; layered resolution (customer > template >
  global); re-map (new version, prior versions retained); mapping API.
- **Out:** value-level transformation (Phase 3); AI suggestions (Phase 5); UI (Phase 6).

## Functional Requirements

- **P2.2-1 Saved config (P2-2):** persist a mapping as a `mapping_config` keyed by **tenant + column signature**, versioned (reuses the Phase-0 versioning helper).
- **P2.2-2 Config matching (P2-3):** for a new sheet, compute its signature and auto-apply the matching config; if none matches, report **needs-mapping**.
- **P2.2-3 Layered resolution (P2-4):** merge configs for a signature in precedence order **customer > template > global**, merged at runtime.
- **P2.2-4 Re-map (P2-6):** editing a config creates a new version; prior versions remain retrievable so past outputs stay traceable to the version used.
- **P2.2-5 API:** endpoints to save a sheet mapping (returns the config + validation) and to auto-map a sheet (returns the applied mapping or needs-mapping).

## Deliverables

- `src/mmm_os/mapping/service.py` — save, resolve (layered), and auto-map.
- `src/mmm_os/schemas/mapping.py` + `src/mmm_os/api/routers/mapping.py`.
- Tests: save → auto-apply same-signature sheet; slight column change → no match / flagged; missing required blocks; re-map creates v2 with v1 retained; layered merge precedence.

## Acceptance Criteria

- Map a sheet once → save → a same-structure sheet auto-applies the config with no manual step.
- A changed column signature does not match and is flagged needs-mapping.
- A mapping missing a required field is surfaced as incomplete (blocks output).
- Editing a config creates v2; v1 remains retrievable.
- Customer-layer entries override template and global for the same signature.

## Dependencies

Phase 2.1.

## Open Questions

None outstanding.

## Sub-phases

N/A (leaf sub-phase).
