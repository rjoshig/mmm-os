# Phase 6 — Review UI (Next.js)

**Depends on:** Phases 2–5 · **Status:** Not started

The UI shell is scaffolded during repo initialization; feature screens land here.
All UI MUST match the design language in [`../../front-end/CLAUDE.md`](../../front-end/CLAUDE.md).

## Objective

Give users an intuitive, preview-driven interface to review AI suggestions,
confirm mappings, tune transformations, and resolve validation flags —
**generating config behind the scenes** (users never write JSON).

## Scope

- **In:** file/job dashboard; mapping-review screen; transformation builder
  (action-based); validation-review screen; before/after preview everywhere.
- **Out:** connector config UI, admin/RBAC UI (Phase 8).

## Functional Requirements

- **P6-1 Job dashboard:** list files/jobs with status, per-file progress, and what needs attention.
- **P6-2 Mapping review:** show source columns + samples alongside AI-suggested canonical fields (with confidence + reason); user accepts/rejects/modifies. Actions write mapping config.
- **P6-3 Action-based transformation builder:** user clicks a column → picks an operation → configures via UI (e.g. assign canonical values to distinct raw values); each action authors a rule. **No raw JSON exposed.**
- **P6-4 Live preview:** every mapping/rule change shows before/after on sample rows immediately.
- **P6-5 Validation review:** list flags with location + severity + AI explanation; acknowledge/resolve/override.
- **P6-6 Reuse visibility:** show when a saved config auto-applied, and let the user confirm or adjust.

## Deliverables

- Next.js app implementing the four screens above against the Phase 1–5 APIs.

## Acceptance Criteria

- A non-technical user can, without seeing any JSON: upload a file, review/accept AI mapping suggestions, collapse messy channel values via the UI, see live before/after, resolve a flag, and produce clean output.
- Editing anything updates the underlying versioned config correctly.
- Auto-applied configs are clearly indicated.

## Dependencies

Phases 2–5.

## Open Questions

- **OQ-6.1** Design system / component library. *(The base design language is
  extracted from the reference UI — see [`../../front-end/CLAUDE.md`](../../front-end/CLAUDE.md);
  confirm whether to formalize a component library on top.)*

## Sub-phases

TBD — to be broken down before implementation.
