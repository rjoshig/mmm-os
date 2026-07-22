# Phase 5.2 — Suggestion Service, Review & Ratify API

**Parent:** [`phase-05`](./phase-05-ai-suggestion-layer.md) ·
**Depends on:** 05.1 · **Status:** Done (pending PR merge)

Covers **P5-1..P5-8**.

## Objective

Use the LLM client to draft mapping / taxonomy / anomaly suggestions from
**profile data**, score confidence, store reasoning, and gate everything behind a
human accept/reject loop (suggest, don't decide).

## Scope

- **In:** suggestion prompts + JSON parsing for column mapping, taxonomy
  labelling, and anomaly explanation; confidence thresholds; suggestion +
  rationale storage; accept/reject; ratification that writes accepted mappings
  into the config store; API.
- **Out:** structure-detection suggestions beyond a stub; UI (Phase 6);
  auto-commit (forbidden, CC-5).

## Functional Requirements

- **P5.2-1 Profile inputs (P5-1):** suggestions consume **distinct values + column stats** (the Phase-1.3 profile), never raw row dumps — verifiable in what is sent.
- **P5.2-2 Mapping suggestions (P5-2):** per source column, propose a canonical field with a **confidence** and rationale; thresholds classify high (auto-fill-as-pending) vs low (needs review). Never committed without a human accept.
- **P5.2-3 Taxonomy suggestions (P5-3):** given distinct raw values, propose the canonical term.
- **P5.2-4 Anomaly explanation (P5-5):** given a flag, produce a plain-language likely cause.
- **P5.2-5 Reasoning stored (P5-7):** every suggestion persists its rationale + confidence + state.
- **P5.2-6 Ratification (P5-8):** accepting a mapping suggestion writes it into the `mapping_config` store (Phase 2) — a human action; the AI never writes committed config.
- **P5.2-7 API:** endpoints to request suggestions and to accept/reject them; the LLM being disabled returns a clear 503.

## Deliverables

- `src/mmm_os/ai/` — `prompts`, `suggestions` (service), `service` (persistence + ratify).
- `schemas/ai.py` + `api/routers/ai.py`.
- Tests (with a fake LLM client): mapping suggestions parsed + persisted with confidence/rationale; accept writes a mapping config; reject updates state; disabled → 503; inputs are profile-only.

## Acceptance Criteria

- Given a profiled sheet, the system returns per-column mapping suggestions with confidences and rationales; accepting one creates the mapping-config entry (a human action).
- Given distinct channel spellings, a taxonomy suggestion proposes the correct canonical term.
- No suggestion becomes committed config without an explicit accept.
- Only profile data is sent to the model (verifiable in the fake client's captured input).

## Dependencies

Phase 5.1; Phases 2 (mapping config), 1.3 (profiles), 4 (flags).

## Open Questions

OQ-5.2 (confidence calibration) deferred; interim = model-reported confidence + thresholds.

## Sub-phases

N/A (leaf sub-phase).
