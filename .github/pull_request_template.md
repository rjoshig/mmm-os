<!--
  See GIT_STANDARDS.md. One phase (or sub-phase) per PR, aligned to the roadmap
  in docs/phases/README.md. Fill in every section.
-->

## Linked phase

<!-- Link the phase (or sub-phase) spec this PR implements, e.g.
     docs/phases/phase-01-file-ingestion-structure-detection.md -->

- Phase:

## Summary

<!-- What does this PR change, and why? -->

## Acceptance criteria

<!-- Copy the linked phase's Acceptance Criteria here and tick each item only
     when it is genuinely met. -->

- [ ]
- [ ]

## Cross-cutting requirements

<!-- Tick those this PR touches / upholds (see build-plan.md CC-1…CC-8). -->

- [ ] CC-1 Multi-tenant (`tenant_id` everywhere; no cross-tenant reads)
- [ ] CC-2 Immutable raw files
- [ ] CC-3 Traceability
- [ ] CC-4 Config-as-data (versioned)
- [ ] CC-5 Human-in-the-loop AI
- [ ] CC-6 Idempotent jobs
- [ ] CC-7 Observability

## Checks

- [ ] Backend: `ruff`, `mypy`, `pytest` (SQLite) pass
- [ ] Front-end (if touched): `lint`, `typecheck`, `build` pass
- [ ] No secrets committed; `.env` not included (only `.env.example`)
