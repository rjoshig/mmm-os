# Phase 18 — In-App Sandbox / Test Environment

**Depends on:** 3 (preview), 4 (validation), 13 (draft→publish lifecycle)
· **Status:** Build · **Cycle:** 5 (Usability, Reuse & Model-Readiness)

Cross-cutting: config-as-data (CC-4), human-in-the-loop (CC-5), idempotent (CC-6),
multi-tenant (CC-1).

See the umbrella design: [`../design/usability-reuse-model-readiness.md`](../design/usability-reuse-model-readiness.md) §4.5.

## Objective

Give users a safe, in-product space to **try configs before publishing** — run the
full pipeline against a sample or real file and see coverage, transforms,
validation flags, and output stats, without affecting published configs or real
output/stacks.

## Scope

- **In:** a **sandbox run** mode over the existing pipeline; sandbox results
  (throwaway, auto-expiring); a Test/Sandbox UI toggle + results panel, clearly
  badged.
- **Out:** a separate staging **deployment** (infra, Phase 11); a permanent
  parallel dataset; sandbox sharing/collaboration beyond the tenant.

## Cross-cutting

- **CC-4** sandbox runs use config **drafts**; publishing is a separate, explicit
  step (unchanged from Phase 13).
- **CC-1** sandbox jobs and results are tenant-scoped.
- **CC-6** a sandbox run is deterministic for the same input + draft config.
- Sandbox output is **excluded** from real output/`output_row`/Stacks and never
  feeds a published stack.

## Functional Requirements

- **P18-1 Sandbox run** — run detect → map → transform → validate → output-stats on
  a chosen file (sample fixture or real) using a chosen config **draft**, producing
  a throwaway result: mapping coverage, transform before/after, validation flags,
  and output statistics. Builds on `transform/preview.py` + `pipeline/service.py`.
- **P18-2 Isolation** — a `sandbox` flag on `job` (or a dedicated sandbox job kind)
  marks the run; its rows/artifacts never enter real output or a Stack; results
  auto-expire via the existing retention mechanism (Phase 10).
- **P18-3 Promote** — from a satisfactory sandbox run, the user can save/publish the
  tried config draft through the normal draft→publish flow (Phase 13) — the sandbox
  itself commits nothing.
- **P18-4 UI** — a "Test / Sandbox" toggle on the file/transform pages and a sandbox
  results panel; a clear **Sandbox** badge everywhere so results are never mistaken
  for a published stack.

## Deliverables

- Sandbox flag on `job` (+ migration) and a sandbox run path (reusing preview +
  pipeline services).
- Retention/expiry wiring for sandbox runs.
- UI toggle + results panel + badges.
- Tests: sandbox run produces results but writes **no** real output/Stack rows;
  expiry purges sandbox artifacts; promote path publishes the draft normally.

## Acceptance Criteria

- Running a config draft in sandbox shows coverage/preview/flags/stats but creates
  **no** `output_row`/`StackRow` and does not alter published configs.
- Sandbox results are badged and auto-expire per retention.
- Promoting a tried draft publishes it through the standard lifecycle (audited).
- Backend `ruff`/`mypy`/`pytest` and front-end `typecheck`/`lint`/`build` pass.

## Dependencies

Phase 3 (preview), Phase 4 (validation), Phase 10 (retention), Phase 13
(draft→publish), Phase 17 (output stats).

## Open Questions

- **OQ-18.1** sandbox data — sample fixtures vs real files; retention/expiry window
  for sandbox runs. Default: allow both; short expiry (e.g. 7 days).

## Sub-phases

TBD (per the sub-phase convention in [`README.md`](./README.md)).
