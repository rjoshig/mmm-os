# Phase 13 — Collaboration & Multi-User Workflow

**Depends on:** 2 (mapping configs), 3 (rule sets), 6 (Review UI), 8 (RBAC + audit)
· **Status:** Done — all sub-phases (13.1–13.5) implemented.

Enterprise-overhaul theme: make the platform a place where **a team works the data
together** — one person configures, another continues, a third reviews — with full
visibility of who did what. The foundations already exist (tenant isolation CC-1,
config-as-data CC-4, RBAC, audit log, human-in-the-loop CC-5); this phase closes the
**collaboration gaps** on top of them.

## Objective

Let multiple authenticated users in a tenant collaborate on the same data safely and
legibly: discover and reuse each other's configs, hand off work mid-flow, see run
history, and communicate in context — without stepping on each other.

## Why now (the gap)

Today configs are shared data keyed by column signature, so "one configures, another
continues" already *works implicitly*. But the team cannot yet: browse/search the
configs they collectively own, see who authored or last changed a config, stage a
config for review before it goes live, pick up work assigned to them, watch run
history, or leave notes. This phase makes the implicit collaboration **explicit and
manageable**.

## Scope

- **In:** config library + version history/diff + authorship; config draft→review→
  publish lifecycle; jobs/pipeline-runs history UI; per-user review queue &
  assignment; in-context comments/annotations + activity feed + notifications.
- **Out:** real-time co-editing / live presence cursors (not needed at this scale);
  external chat integrations (Slack/email) beyond a notification hook; SSO/SCIM user
  provisioning (Phase 00.5 extension, tracked separately).

## Cross-cutting

- **CC-1** every new record (`created_by`, comments, assignments, notifications) is
  `tenant_id`-scoped; no cross-tenant reach.
- **CC-4** configs stay versioned data; the draft/publish state is *data on the
  version*, never a code branch.
- **CC-5/audit** every collaborative action (assign, comment, publish, approve) is
  written to the existing audit log with actor + target.
- **RBAC (Phase 8)**: authoring/publishing needs `write_config`; approving a config
  or resolving a queue item needs `review`; viewing needs `read`.

## Functional Requirements

Grouped by sub-phase (see **Sub-phases**).

- **P13-1** Config library: list/search every saved **mapping config** and **rule
  set** in the tenant, with version count, layer, the signature/scope it applies to,
  and last-updated. Drill into a config's **version history** and **diff** two
  versions.
- **P13-2** Config authorship: persist `created_by` / `updated_by` on config +
  rule-set versions; surface "created by X · last edited by Y" in the library and on
  the mapping/transform screens.
- **P13-3** Config lifecycle: a saved config version may be a **draft**; a user with
  `review` **publishes** (or requests changes on) it; only the latest *published*
  version resolves into the pipeline. Prior published versions remain for traceability
  (CC-3).
- **P13-4** Runs history: a **Runs** view listing jobs, full-pipeline runs, and sync
  runs with status, timing, stage breakdown, and errors (CC-7); drill into one run's
  per-stage detail. *(Coordinates with Cycle 3 automation, which produces scheduled
  runs; this is the review-side visibility surface — see Dependencies.)*
- **P13-5** Review queue & assignment: assign a file / sheet / flag-cluster to a
  tenant user; each user gets an **"Assigned to me"** queue and a tenant
  **"Needs review"** board; assignment changes are audited and (optionally) notified.
- **P13-6** Annotations & notifications: leave **comments** on a flag, mapping, or
  file; **@mention** a teammate; an **activity feed** per file; **in-app
  notifications** for mentions, assignments, and publish requests.

## Sub-phases

Built in order; each is a PR-sized slice with its own `phase-13.M-*.md` spec created
at build time (per the sub-phase convention in [`README.md`](./README.md)).

- **13.1 — Config library & authorship** (P13-1, P13-2). **Done**: `created_by` on
  `mapping_config` + `rule_set` (nullable, threaded through the save endpoints);
  `GET /config-library` (families with latest version, version count, author) +
  `GET /config-library/versions`. UI: a **Configs** screen with version history +
  authorship. (Side-by-side value diff is a follow-up.)
- **13.2 — Config draft → review → publish lifecycle** (P13-3). **Done**:
  `lifecycle_status` (`draft`|`published`|`archived`) on mapping-config + rule-set
  versions (default published — back-compat); pipeline resolution reads the latest
  *published* only; save-as-draft (transform builder) + a `review`-gated
  `POST /config-library/publish` (audited). UI: status badges + Publish on the Configs
  screen; "Save as draft" / "Save & publish" on the transform builder.
- **13.3 — Jobs & pipeline-runs history UI** (P13-4). **Delivered by Cycle 3, Slice 2**:
  a `/runs` view over `job` (with stage `job_event`s) + tenant-wide `sync_run`
  records — status, timing, errors, stage logs (CC-7). Endpoints: `GET /jobs/{id}`
  (detail + events), `GET /sync-runs` (tenant-wide). Read-only.
- **13.4 — Review queue & work assignment** (P13-5). **Done**: `assignment` records
  (target_type/target_id → assignee, note, status), gated by `review` + audited.
  Endpoints: `POST /assignments`, `GET /assignments?assignee=` (a user's queue),
  `POST /assignments/{id}/resolve`. UI: a `/queue` review-queue screen + "Assign"
  dialog on the file detail.
- **13.5 — Collaboration annotations & notifications** (P13-6). **Done**: `comment`
  + `notification` records (tenant-scoped). `POST/GET /comments` (per-object activity
  feed) with @mentions → in-app notifications; `GET /notifications` +
  `POST /notifications/{id}/read`; assignments also notify the assignee. UI: a comments
  panel on the file detail (with a mention picker) + a notifications center on the
  Queue screen. Notification delivery is in-app via a `_notify` sink (email/webhook
  is a follow-up).

## Deliverables

- New models + migrations: config authorship columns, config `status`, `assignment`,
  `comment`, `notification` (all tenant-scoped, dialect-agnostic types).
- Backend endpoints for config library/diff, publish lifecycle, runs history,
  assignment, comments, notifications — thin routers, tenant + RBAC enforced.
- Review-UI screens: **Configs** (library + history + diff), **Runs**, **My queue** /
  **Needs review**, and comment/notification affordances woven into existing screens.
- Docs kept in sync (this spec, README status, build-plan, data-model entities).

## Acceptance Criteria

- Two users in one tenant: user A saves a mapping as a **draft**; user B sees it in
  the config library with "created by A", **diffs** it against the prior version, and
  **publishes** it; only then does it resolve into the pipeline — all steps audited.
- A file/sheet **assigned** to user B appears in B's "Assigned to me" queue; resolving
  it clears the queue item.
- The **Runs** view lists a file's jobs/pipeline runs with status + timing + errors.
- A **comment** with an `@mention` produces an in-app **notification** for the
  mentioned user.
- No collaborative record or query crosses a tenant boundary (CC-1 tests).
- Backend `ruff`/`mypy`/`pytest` and front-end `typecheck`/`lint`/`build` pass.

## Dependencies

Phases 2, 3, 6, 8. **Coordinates with Cycle 3** (Sources/Connectors + scheduler):
Cycle 3 *produces* scheduled pipeline/sync runs; **13.3 visualizes** them. Build 13.3
to read whatever run records exist, and extend it when Cycle 3 lands the scheduler so
there is no duplicated Runs UI.

## Open Questions

- **OQ-13.1** Publishing model: does publishing a config require a *different* user
  than the author (segregation of duties), or may an author self-publish with
  `review` permission? Default assumption: self-publish allowed; a tenant setting can
  later require a second approver.
- **OQ-13.2** Notification delivery beyond in-app (email/webhook) — in scope for 13.5
  as a pluggable sink, or a later phase? Default: in-app only now, sink interface
  defined.
- **OQ-13.3** Assignment granularity — file, sheet, and/or flag-cluster level? Default:
  file + sheet now; flag-cluster if it proves useful.
