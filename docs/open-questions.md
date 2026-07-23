# Open Questions

**Status:** v0.2 — many questions resolved during the foundations exercise.
**Rule:** where a question is still **Open**, stop and ask rather than assuming
(see [`../CLAUDE.md`](../CLAUDE.md), golden rule 4). Resolutions below are
recorded here and, where architectural, in [`architecture.md`](./architecture.md)
(ADR log); schema-affecting ones in [`canonical-schema.md`](./canonical-schema.md).

**Legend:** ✅ Resolved · 🟡 Partially resolved · ⏸️ Deferred (with a leaning).

---

## Appendix E — Consolidated Open Questions (from the source docs)

| ID | Question | Phase | Status |
|---|---|---|---|
| OQ-0.1 | Tenant isolation: row-level vs schema/DB-per-tenant. | 0 | ✅ **Row-level** (`tenant_id` on every domain table). See ADR-003. |
| OQ-0.2 | Warehouse choice for clean output. | 0 | ✅ **v1 = an `output_row` table in the backend DB** (SQLite→Postgres); dedicated warehouse deferred until scale. See ADR-005. |
| OQ-1.1 | Max file size / row count for v1. | 1 | ✅ **~200 MB / ~5M rows per sheet** as the documented v1 ceiling; streamed/chunked; configurable; over-limit files fail the job with a clear reason. |
| OQ-1.2 | Multiple header-like rows behaviour (pick vs ask). | 1 | ✅ **Pick + flag**: auto-select the highest-scoring header deterministically; below a confidence threshold, flag `needs-review` (AI assists in Phase 5). |
| OQ-2.1 | Column-signature definition (exact/fuzzy/positional). | 2 | ✅ **Normalized header-name set** (lowercased, trimmed, whitespace/punctuation-collapsed), order-tolerant; match = exact set equality. Fuzzy/positional matching deferred to the AI layer (Phase 5). |
| OQ-2.2 | Required vs optional canonical fields / measures. | 2 | ✅ **Required: `date` + `channel` + ≥1 measure or factor** (Cycle 2 adds factor sources); all other fields optional. See canonical-schema A.4. |
| OQ-3.1 | Escape-hatch `custom` rule scope. | 3 | ✅ **Sandboxed expression language** (restricted DSL over row/field context; no arbitrary code, imports, or I/O; allowlisted ops; resource-bounded). See ADR-004. |
| OQ-3.2 | Reshape (wide→long) config model. | 3 | ✅ **Draft config model** `{ id_vars, value_vars \| value_var_pattern, var_name → dimension, value_name → measure }`; deterministic. |
| OQ-4.1 | Default severity / blocking policy. | 4 | ✅ **BLOCK** = missing/unmapped required field, negative measure, type mismatch on a required field; **WARN** = date gaps, duplicates, outliers, out-of-range non-required. Configurable per tenant. |
| OQ-4.2 | Anomaly method for v1. | 4 | ✅ **z-score (robust/median variant) + IQR** per dimension slice; behind a pluggable detector interface. |
| OQ-5.1 | LLM provider / model + cost ceiling per file. | 5 | 🟡 **Dual provider — OpenAI + Anthropic — selected by config/env** (off by default; provider auto-inferred from model name). Swappable without code changes. **Cost ceiling per file deferred** (needs real usage data). See ADR-008. |
| OQ-5.2 | Confidence calibration. | 5 | ⏸️ **Deferred** — needs labelled accept/reject data. Interim: model-reported confidence + configurable thresholds; calibrate later (reliability curves / isotonic). |
| OQ-6.1 | Design system / component library. | 6 | ✅ **Extracted design language + hand-built shadcn-style primitives** (Card/Badge/Table/PageHeader/StatCard); no heavy third-party component library. See ADR-009 and `../front-end/CLAUDE.md`. |
| OQ-7.1 | Queue tech + worker hosting. | 7 | ✅ **Celery + Redis** (broker + result backend); autoscaling workers; per-tenant rate limiting/fairness. See ADR-007. |
| OQ-8.1 | Target compliance framework. | 8 | ⏸️ **Deferred** — working target **SOC 2 Type II** (per PRD); specific controls/scope to be set in Phase 8 with legal. |

---

## Questions surfaced during repository initialization

| ID | Question | Phase | Status |
|---|---|---|---|
| OQ-INIT.1 | Object-storage provider and local-dev substitute. | 1 | ✅ **Storage abstraction**: local filesystem in dev, S3-compatible (S3/MinIO) in prod, selected by env. See ADR-006. |
| OQ-INIT.2 | Is the clean-output "warehouse" a backend-DB table or a separate system for v1? | 0/1 | ✅ **Backend-DB table** (`output_row`) for v1 — same decision as OQ-0.2. See ADR-005. |
| OQ-INIT.3 | Does the UI (Prisma) database store anything beyond front-end concerns? | 6 | ✅ **UI-only concerns** (session/preferences/UI state later); never mirrors backend domain data; effectively empty until Phase 6. |
| OQ-INIT.4 | LLM provider/SDK choice and credential injection. | 5 | ✅ **OpenAI SDK and Anthropic SDK, config/env-selected**; credentials via env (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `LLM_API_KEY`) or JSON config; only profile data sent to the model (P5-1). Folds into ADR-008. |

---

## Partner-connector questions (Phase 9 — deferred)

Surfaced when designing the source-agnostic abstraction (ADR-010). The
architecture is settled; these are **implementation inputs** needed before the
relevant Phase-9 sub-phase, several with **external lead times**. Do not assume —
confirm before building.

| ID | Question | Sub-phase | Status |
|---|---|---|---|
| OQ-9.1 | Partner priority/order for implementation (which partner first?). | 09.4/09.5 | ⏸️ Deferred — Meta is the assumed reference (09.4); confirm ordering of Google Ads / DV360 / TikTok. |
| OQ-9.2 | OAuth app registration / API access approval per platform (Meta app review, Google Ads developer token, TikTok API access). | 09.2/09.4/09.5 | ⏸️ Deferred — **external lead times**; start approvals early. |
| OQ-9.3 | Auth model per partner: OAuth2 (per-customer) vs long-lived/system-user tokens. | 09.2 | ⏸️ Deferred — contract is auth-agnostic; per-partner choice set at build. |
| OQ-9.4 | Incremental strategy + rolling lookback window (restatement handling) and historical backfill depth. | 09.6 | ⏸️ Deferred — needs per-partner restatement behaviour. |
| OQ-9.5 | Per-partner rate limits / quotas. | 09.6 | ⏸️ Deferred — from each partner's API docs. |
| OQ-9.6 | Confirm aggregate-only (no user-level PII) scope per partner. | 09.2/09.4/09.5 | ⏸️ Deferred — assumed aggregate-only; confirm requested scopes per partner. |
| OQ-9.7 | Currency/timezone normalization: source of truth across partners. | 09.6/09.7 | ⏸️ Deferred — ties to canonical schema; likely per `connector_config`. |
| OQ-9.8 | SFTP specifics: per-tenant directory layout, file-naming contract, PGP encryption. | 09.3 | ⏸️ Deferred — define the drop contract with the first SFTP customer. |
| OQ-9.9 | Default `action_type`(s) that count as conversions per customer (purchase vs lead vs custom). | 09.4/09.7 | ⏸️ Deferred — per-tenant KPI decision; template default = `purchase`. |
| OQ-9.10 | Attribution-window policy across partners (consistency requirement over time + across partners). | 09.4/09.5/09.6 | ⏸️ Deferred — must stay consistent across pulls; confirm with customer. Materially changes numbers. |
| OQ-9.11 | Should `channel` be fixed per connector, or derived from placement/`publisher_platform`? | 09.4/09.7 | ⏸️ Deferred — template default fixes `channel` (placement in `sub_channel`); overridable per tenant. |
| OQ-9.12 | Confirm exact partner field names + attribution params against the current API version. | 09.4/09.5 | ⏸️ Deferred — Meta/Google/TikTok template field names are **provisional**; verify at implementation time. |
| OQ-9.13 | Google Ads: which `conversion_action`(s) count as conversions per customer; `conversions` vs `all_conversions`. | 09.5 | ⏸️ Deferred — per-tenant KPI decision (parallels Meta OQ-9.9). |
| OQ-9.14 | Google Ads: geo-target-constant → country resolution source (for `resolve_geo_target`). | 09.5 | ⏸️ Deferred — need the geo-target-constant reference data. |
| OQ-9.15 | TikTok: which conversion event + **value** metric per customer (drives `revenue`, left null by default). | 09.5 | ⏸️ Deferred — per-tenant; value-metric name provisional. |
| OQ-9.16 | TikTok: all vs destination clicks; sync vs async report thresholds; how advertiser currency is fetched. | 09.5 | ⏸️ Deferred — config + API-behaviour details. |
| OQ-9.17 | Cross-partner: consistent channel-naming (fixed constant per connector vs derived) applied uniformly across Meta/Google/TikTok/DV360. | 09.4/09.5 | ⏸️ Deferred — templates fix `channel` per connector today (Meta OQ-9.11); confirm uniform resolution. DV360 default = `Programmatic` (vs `DV360`/`Google`). |
| OQ-9.18 | DV360: which cost metric counts as `spend` (`METRIC_REVENUE_ADVERTISER` vs media-cost vs billable-cost). | 09.5 | ⏸️ Deferred — per-tenant billing/markup model; template default = `METRIC_REVENUE_ADVERTISER`. |
| OQ-9.19 | DV360: hierarchy level to pull (Media Plan / Insertion Order / Line Item) and its mapping to campaign/ad_group. | 09.5 | ⏸️ Deferred — default = Media Plan→campaign, Insertion Order→ad_group. |
| OQ-9.20 | DV360: Bid Manager async offline-report handling (create/run/poll/download signed CSV) + stripping grand-total rows. | 09.5 | ⏸️ Deferred — needs `strip_report_totals` op (Phase 3) + async report orchestration (Phase 09.6). |

---

## Enterprise-readiness questions (inserted + spec-only phases)

Surfaced by the enterprise-readiness phases. **Build** phases resolve theirs before
implementation; **spec-only** phases (10–12) resolve theirs if/when scheduled.

| ID | Question | Phase | Status |
|---|---|---|---|
| OQ-00.5-1 | Session store: DB-backed vs stateless signed tokens vs both. | 00.5 | ⏸️ Deferred to build. |
| OQ-00.5-2 | OIDC/SAML library selection (maintained, audited). | 00.5 | ⏸️ Deferred to build. |
| OQ-00.5-3 | Per-tenant IdP config model (discovery, cert rotation, attribute mapping). | 00.5 | ⏸️ Deferred to build. |
| OQ-00.5-4 | MFA method(s) for v1 (TOTP / WebAuthn / OTP). | 00.5 | ⏸️ Deferred to build. |
| OQ-00.6-1 | Dev secrets backend + at-rest encryption scheme. | 00.6 | ⏸️ Deferred to build. |
| OQ-00.6-2 | Target managed KMS/vault. | 00.6 | ⏸️ Deferred to build. |
| OQ-00.6-3 | Key rotation policy (cadence, envelope encryption). | 00.6 | ⏸️ Deferred to build. |
| OQ-5.1-1 | Default per-tenant LLM budgets (tokens/cost, window). | 05.1 | ⏸️ Deferred to build. Supersedes the old OQ-5.1 cost-ceiling framing. |
| OQ-5.1-2 | Behaviour at cap: hard block vs degrade (deterministic-only). | 05.1 | ⏸️ Deferred to build. |
| OQ-5.1-3 | Model-tier routing policy (signals for easy vs hard). | 05.1 | ⏸️ Deferred to build. |
| OQ-07.1-1 | Metrics/logging/tracing stack (e.g. OTel + Prometheus/Grafana vs hosted APM). | 07.1 | ⏸️ Deferred to build. |
| OQ-07.2-1 | Retry limits/policy per failure class. | 07.2 | ⏸️ Deferred to build. |
| OQ-07.2-2 | DLQ handling workflow (alert / manual replay / expiry). | 07.2 | ⏸️ Deferred to build. |
| OQ-08.1-1 | Target framework(s) — SOC 2 Type II (per OQ-8.1); others? | 08.1 | ⏸️ Deferred to build. |
| OQ-08.1-2 | Which technical controls are in-scope for v1. | 08.1 | ⏸️ Deferred to build. |
| OQ-10-1 | Retention periods per data class. | 10 | ⏸️ Spec-only. |
| OQ-10-2 | RPO/RTO targets. | 10 | ⏸️ Spec-only. |
| OQ-10-3 | Erasure vs immutable-raw (CC-2) / audit reconciliation. | 10 | ⏸️ Spec-only. |
| OQ-10-4 | Data-residency requirements + regions. | 10 | ⏸️ Spec-only. |
| OQ-11-1 | Hosting/cloud target + container orchestration. | 11 | ⏸️ Spec-only. |
| OQ-11-2 | IaC tooling. | 11 | ⏸️ Spec-only. |
| OQ-11-3 | CI/CD platform + release/rollback strategy. | 11 | ⏸️ Spec-only. |
| OQ-12-1 | Concrete SLA targets per stage. | 12 | ⏸️ Spec-only. |
| OQ-12-2 | Load-testing tooling + traffic modelling. | 12 | ⏸️ Spec-only. |
| OQ-12-3 | Scale ceiling to validate (200–500 tenants + batch sizes). | 12 | ⏸️ Spec-only. |

---

## Still open (need input before their phase)

- **OQ-5.1 (cost ceiling per file)** — set once we have real per-file token/cost data.
- **OQ-5.2 (confidence calibration)** — needs labelled accept/reject outcomes.
- **OQ-8.1 (compliance controls)** — SOC 2 Type II is the working target; confirm scope + controls with legal in Phase 8.
- **OQ-9.1…OQ-9.20 (partner connectors)** — Phase 9 implementation inputs; OQ-9.2 has external approval lead times worth starting early; OQ-9.9…9.12 come from the Meta template pattern; OQ-9.13…9.17 from the Google Ads & TikTok templates; OQ-9.18…9.20 from the DV360 template (cost-metric choice, hierarchy level, async offline-report handling).

---

## Decisions already locked (for reference)

Recorded in [`architecture.md`](./architecture.md) (ADR log) and the relevant docs:

- Two independent databases (backend + UI), each SQLite now / Postgres later, swappable by config only (ADR-001, ADR-002).
- **Row-level tenant isolation** — `tenant_id` on every domain table (ADR-003, OQ-0.1).
- **Clean output v1 = `output_row` table in the backend DB** (ADR-005, OQ-0.2/INIT.2).
- **Object storage = abstraction; local FS dev / S3-compatible prod** (ADR-006, OQ-INIT.1).
- **Transformation `custom` op = sandboxed expression language** (ADR-004, OQ-3.1).
- **Async queue = Celery + Redis** (ADR-007, OQ-7.1).
- **AI provider = Claude via the Anthropic API**, env-injected creds, profile-only inputs (ADR-008, OQ-5.1/INIT.4).
- **Design system = extracted tokens + hand-built shadcn-style primitives** (ADR-009, OQ-6.1).
- **Source-agnostic ingestion abstraction** — every source (upload/SFTP/API) emits one `LandedDataset` via `SourceConnector`; `FileSource` real now, connectors deferred to Phase 9 (ADR-010, CC-9/CC-10).
- Required canonical fields: `date` + `channel` + ≥1 measure **or factor** (OQ-2.2; factors added in Cycle 2).
- Python targets **3.10+**; backend SQLAlchemy 2.0 + Alembic; UI Prisma.
- Front-end design language replicated from the reference UI (`../front-end/CLAUDE.md`).

---

_Living document — when a still-open question is answered, move it up with a
pointer to the ADR / phase spec that records the decision._
