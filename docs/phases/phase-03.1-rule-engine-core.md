# Phase 3.1 — Rule Engine Core & Structural Operations

**Parent:** [`phase-03`](./phase-03-transformation-rule-engine.md) ·
**Depends on:** Phases 0, 2 · **Status:** Done (pending PR merge)

Covers **P3-1, P3-4, P3-5** and the structural operations of P3-2.

## Objective

The declarative rule engine: apply an ordered, layered set of rules to in-memory
records deterministically, via an extensible operation registry. Ships the
structural operations.

## Scope

- **In:** rule spec model; operation registry (new op = new handler); ordered +
  layered application (global → template → customer, then by `order`); optional
  per-row condition; structural ops `rename_column`, `cast_type`,
  `normalize_text`, `fill_missing`, `dedupe`.
- **Out:** value/domain ops (`map_value`, `parse_date`, `convert_currency`,
  `reshape`) and the `custom` escape hatch (03.2); persistence/preview/API (03.2);
  validation (Phase 4).

## Functional Requirements

- **P3.1-1 Rule spec (P3-1):** a rule is `{target_field, operation, params, condition, order, layer}`.
- **P3.1-2 Registry (P3-2 extensibility):** operations are registered handlers; adding a capability is adding a handler, not rewriting the engine.
- **P3.1-3 Ordered + deterministic (P3-4):** rules apply in a defined order; the same input + rules yield identical output.
- **P3.1-4 Layered (P3-5):** rules from global, template, and customer layers are merged and applied in precedence order.
- **P3.1-5 Condition:** an optional predicate restricts a row-level op to matching rows.
- **P3.1-6 Structural ops:** `rename_column`, `cast_type`, `normalize_text`, `fill_missing`, `dedupe`.

## Deliverables

- `src/mmm_os/transform/` — `types`, `registry`, `conditions`, `engine`, `operations_core`.
- Tests: ordering/determinism/layering; each structural op; condition gating.

## Acceptance Criteria

- Applying rules is deterministic and respects layer + order.
- Each structural op transforms records correctly; unknown ops raise a clear error.
- A condition restricts an op to matching rows only.

## Dependencies

Phases 0 (schema) and 2 (mapped, canonically-keyed records).

## Open Questions

None outstanding.

## Sub-phases

N/A (leaf sub-phase).
