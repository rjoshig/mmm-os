# Phase 5 — AI Suggestion Layer

**Depends on:** Phases 2, 3, 4 · **Status:** Done (all sub-phases implemented; pending PR merge)

Cross-cutting: human-in-the-loop (CC-5) — AI never auto-commits.

## Objective

Accelerate mapping, labelling, structure detection, and anomaly triage with AI
**suggestions** that humans ratify. Mirrors "Data MAITE": suggest, don't decide.

## Scope

- **In:** AI suggestions for column mapping, value/taxonomy labelling, structure
  detection, anomaly explanation; confidence scoring; review loop; reasoning
  storage.
- **Out:** any auto-commit without human approval.

## Functional Requirements

- **P5-1 Inputs:** AI MUST receive **profiles (distinct values + column stats)**, not raw data dumps (cheaper, more accurate, privacy-preserving).
- **P5-2 Mapping suggestions:** propose canonical field per source column, with a **confidence score**. High-confidence MAY auto-fill the mapping *as a pending suggestion*; low-confidence flags for review. Never final without human accept.
- **P5-3 Taxonomy suggestions:** given distinct raw values, propose the canonical term to collapse them into.
- **P5-4 Structure suggestions:** propose header row / data sheets / date column when detection is ambiguous.
- **P5-5 Anomaly explanations:** for a flag, produce a plain-language likely-cause explanation (e.g. "likely duplicate import").
- **P5-6 Confidence thresholds:** configurable thresholds drive auto-fill-as-pending vs flag-for-review behaviour.
- **P5-7 Reasoning stored:** every suggestion MUST store its rationale so the review UI can show *why*.
- **P5-8 Ratification:** accepting a suggestion writes the corresponding **mapping/rule** into the config store (Phases 2/3). AI never writes directly to committed config.
- **P5-9 Transform-rule suggestions (Cycle 4 — Data-MAITE parity):** propose declarative **transform rules** (normalize_text, map_value, fill_missing, cast_type, parse_date, convert_currency, dedupe) from the column profile, and — with `remediate=true` — from the sheet's **open validation flags** (AI remediation). `POST /sheets/{id}/suggest-transforms`; only allowlisted operations are kept; accepting appends the rule to the sheet's rule set (CC-5). UI: "Suggest with AI" on the transform builder + "Suggest fixes (AI)" on the validation screen — reuses the metered/budgeted LLM path (CC-13).

## Deliverables

- Suggestion service wrapping the LLM for the four suggestion types.
- Confidence scoring + threshold config.
- Suggestion + reasoning storage tied to the review loop.

## Acceptance Criteria

- Given a profiled sheet, system returns per-column mapping suggestions with confidences and rationales; accepting one creates the mapping-config entry (a human action).
- Given distinct channel spellings, taxonomy suggestion proposes the correct canonical term.
- No suggestion becomes committed config without an explicit accept.
- AI receives only profile data, verifiable in logs (no raw row dumps sent).

## Dependencies

Phases 2, 3, 4.

## Open Questions

- **OQ-5.1** — 🟡 Partial: provider = **Claude via the Anthropic API** (behind a provider abstraction); **per-file cost ceiling still open** (needs real usage data). See ADR-008.
- **OQ-5.2** — ⏸️ Deferred: confidence calibration needs labelled accept/reject data. Interim: model-reported confidence + configurable thresholds; calibrate later (reliability curves / isotonic).
- **OQ-INIT.4** — ✅ Resolved: **OpenAI + Anthropic SDKs, config/env-selected** (off by default; provider auto-inferred from model name); credentials via env (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `LLM_API_KEY`) or JSON config; only profile data sent to the model (P5-1). See ADR-008.

See [`../open-questions.md`](../open-questions.md) for status.

## Sub-phases

Phase 5 is implemented as two PR-sized sub-phases (one per branch/PR):

- [`phase-05.1-llm-provider-config.md`](./phase-05.1-llm-provider-config.md) — provider-agnostic LLM client (OpenAI + Anthropic), config/env-driven, off by default (ADR-008). **Done.**
- [`phase-05.2-suggestion-service-api.md`](./phase-05.2-suggestion-service-api.md) — mapping/taxonomy/anomaly suggestions from profiles, confidence, reasoning storage, accept/reject/ratify, API (P5-1..P5-8). **Done.**
