# Phase 16.3 — AI-Assisted Harmonization

**Parent:** [`phase-16-harmonization-stack-assembly.md`](./phase-16-harmonization-stack-assembly.md)
· **Status:** Build · **Cycle:** 5

Cross-cutting: human-in-the-loop (CC-5), LLM budget (CC-13), config-as-data (CC-4).

## Objective

Accelerate harmonization (Phase 16.2) with AI that **drafts** taxonomy/value
harmonization, semantic field matches, and entity-resolution proposals — always
ratified by a human.

## Functional Requirements

- **P16.3-1 Suggestion kinds** — extend `src/mmm_os/ai/` with harmonization
  suggestion kinds: taxonomy/value harmonization, semantic field matching, and
  entity-resolution (campaign/geo/product) proposals.
- **P16.3-2 Suggest, don't decide (CC-5)** — each suggestion carries confidence +
  rationale; a human accepts / rejects / modifies; nothing commits automatically.
  Accepted suggestions author the versioned harmonization config (CC-4).
- **P16.3-3 Deterministic-first** — apply the deterministic alias table before
  invoking the LLM; only the unresolved residual goes to the model (cost + quality,
  OQ-16.3).
- **P16.3-4 Metering (CC-13)** — all LLM usage is metered against the per-tenant
  budget; over-cap degrades to deterministic-only (no hard failure of the flow).

## Acceptance Criteria

- For an unmapped source value, the AI proposes a canonical mapping with confidence
  + rationale; accepting it writes the harmonization config; rejecting it leaves
  config untouched.
- The deterministic alias table resolves known values **without** an LLM call;
  only unknowns invoke the model.
- LLM usage is recorded against the tenant budget; at cap, the flow continues
  deterministically.

## Dependencies

Phase 5 (AI suggestion service), Phase 05.1 (LLM cost controls), Phase 16.2.

## Open Questions

Inherits parent OQ-16.3.
