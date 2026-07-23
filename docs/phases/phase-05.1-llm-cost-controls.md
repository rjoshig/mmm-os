# Phase 05.1 — LLM Cost Controls

**Inserted phase** (standalone, not a sub-phase) · **Depends on:** Phase 5 ·
**Status:** Done (per-tenant metering + budgets/429 + response cache + tier routing) — pending PR merge.

Cross-cutting: human-in-the-loop (CC-5), LLM budget enforcement (CC-13),
observability (CC-7).

> Resolves the deferred **OQ-5.1** per-file cost ceiling with a proper per-tenant
> metering + budget model (rather than a single static number).

## Objective

Make AI usage economically safe at multi-tenant scale: meter LLM usage per tenant,
enforce configurable budgets, and reduce cost per suggestion — without weakening
the suggest-don't-decide guarantee (CC-5).

## Scope

- **In:** per-tenant token/call metering; configurable budgets/caps with
  enforcement; response caching; batching; model-tier routing; per-tenant
  usage/cost visibility.
- **Out:** the suggestion logic itself (Phase 5); billing/invoicing; the LLM
  provider abstraction (already Phase 5.1 / ADR-008).

## Functional Requirements

- **P5.1-1 Metering:** every LLM call MUST record tokens + call count attributed to
  a `tenant_id` (and job/suggestion where relevant), persisted as `llm_usage`.
- **P5.1-2 Budgets:** per-tenant budgets/caps (e.g. daily/monthly tokens or cost)
  MUST be configurable, with sensible defaults.
- **P5.1-3 Enforcement:** at the cap the system MUST enforce the configured
  behaviour — **throttle** or **block** further calls — surfaced as a clear,
  non-crashing signal (parallels the "LLM disabled → 503" path in Phase 5.2).
- **P5.1-4 Profile-only inputs (reaffirm P5-1):** only profiles/distinct-values are
  sent, never raw rows — a cost *and* privacy control.
- **P5.1-5 Caching:** identical suggestion requests (same profile signature +
  prompt version + model) SHOULD reuse a cached response instead of re-calling.
- **P5.1-6 Batching:** multiple suggestion units SHOULD be batchable into fewer
  calls where the provider supports it.
- **P5.1-7 Model-tier routing:** easy cases SHOULD route to a cheaper model tier;
  harder/low-confidence cases escalate to a stronger model (config-driven,
  extends ADR-008 model selection).
- **P5.1-8 Visibility:** per-tenant usage + cost MUST be queryable and feed
  observability (Phase 07.1).

## Deliverables

- `llm_usage` entity + metering hook around the Phase-5 `LLMClient`.
- Per-tenant budget config + enforcement middleware.
- Suggestion response cache + optional batching.
- Model-tier routing policy (config-driven).

## Acceptance Criteria

- LLM calls are metered per tenant; usage is queryable.
- A tenant at its cap is throttled/blocked per config, with a clear signal and no
  crash; suggestions already committed are unaffected.
- A repeated identical suggestion request is served from cache (no second call).
- Only profile data is sent to the model (verifiable), unchanged from Phase 5.

## Dependencies

Phase 5 (AI layer, `LLMClient`, ADR-008). Feeds Phase 07.1 (observability). Budget
config is tenant-scoped (CC-1).

## Open Questions

- **OQ-5.1-1** Default per-tenant budgets (tokens/cost, window).
- **OQ-5.1-2** Behaviour at cap: hard **block** vs **degrade** (skip AI, fall back
  to deterministic-only).
- **OQ-5.1-3** Model-tier routing policy (what signals route easy vs hard cases).

## Sub-phases

TBD — to be broken down before implementation.
