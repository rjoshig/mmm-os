# Git Standards — mmm-os

These rules keep history readable, tie every change to the phase roadmap, and
keep secrets out of the repository. They apply to all contributors (human and
AI) working on `mmm-os`.

## Branching

- Branch off the default branch. One branch maps to **one phase** (or, once a
  phase is broken into sub-phases, **one sub-phase**) from the roadmap in
  `docs/phases/README.md`.
- Branch name prefixes:
  - `feat/` — new functionality (a phase or sub-phase deliverable).
  - `fix/` — bug fixes.
  - `chore/` — tooling, scaffolding, dependencies, CI, non-code housekeeping.
  - `docs/` — documentation-only changes.
- Include a short, kebab-case description and, where useful, the phase number:
  - `feat/phase-01-file-ingestion`
  - `feat/phase-01.1-object-storage`
  - `docs/update-open-questions`

## Commits — Conventional Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <short imperative summary>

<optional body — the "why", not the "what">

<optional footer — refs, breaking changes>
```

- **Types:** `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `build`, `ci`, `perf`, `style`.
- Keep the summary under ~72 characters, imperative mood ("add", not "added").
- Commit in **logical chunks** — one coherent change per commit — not one giant
  commit at the end.
- Reference the phase where relevant, e.g. `feat(ingestion): add header-row
  detection (P1-3)`.

## Pull Requests

- **One phase (or sub-phase) per PR**, aligned to the phase roadmap. Do not mix
  phases in a single PR.
- Every PR MUST:
  1. **Link the phase** it implements (e.g. `docs/phases/phase-01-file-ingestion-structure-detection.md`).
  2. Include the phase's **Acceptance Criteria as a checklist**, each item ticked
     only when genuinely met.
  3. Pass all required checks (`ruff`, `mypy`, `pytest` on SQLite; front-end
     `lint` + `typecheck` + `build`) before merge.
- Do not start a later phase's PR until the prior phase's acceptance criteria pass.

### PR template

A template lives at `.github/pull_request_template.md`. It requires the linked
phase, the acceptance-criteria checklist, a summary of changes, and confirmation
that checks pass and no secrets are included.

## Secrets & environment

- **Never commit secrets** — no credentials, tokens, or private URLs in code,
  commits, or PR descriptions.
- `.env` files are **never** committed. Only `.env.example` (backend, at repo
  root) and `front-end/.env.example` (UI) are tracked, with placeholder values.
- All configuration is read from environment variables (see `CODING_STANDARDS.md`).

## Traceability

Because config is data (CC-4) and outputs must be traceable (CC-3), keep commit
messages descriptive enough that a reviewer can map a change back to a phase
requirement (`P<phase>-<n>`) or a cross-cutting requirement (`CC-<n>`).
