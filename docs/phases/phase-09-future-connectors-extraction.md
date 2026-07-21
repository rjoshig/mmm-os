# Phase 9 — (Future) Connectors & Extraction

**Depends on:** deferred · **Status:** Deferred

> **Deferred. Do not build until explicitly scoped.** This phase is out of scope
> for the MVP and everything after it until a maintainer explicitly scopes it. Per
> [`../../CLAUDE.md`](../../CLAUDE.md), never build anything marked Deferred.

## Objective

Extend ingestion beyond files: pull data from marketing-platform APIs, and
convert unstructured PDF/email inputs into tables that feed the normal pipeline —
**only if and when explicitly scoped.**

## Scope

- **In (future):**
  - **9a API connectors:** Meta, Google, TikTok, CRM, e-commerce, ERP. Hardest / least-glamorous; each API differs and changes often.
  - **9b PDF/email extraction:** unstructured → tabular via OCR/LLM, with human-review fallback. Highest failure rate; keep isolated from the core tabular pipeline.
- **Out:** anything in the MVP-through-Phase-8 core. Do not let this phase's
  complexity leak into the tabular pipeline.

## Functional Requirements

*(To be defined when the phase is scoped. Placeholder outline only.)*

- **P9a-1** Per-connector auth + incremental fetch + schema mapping into the canonical schema.
- **P9a-2** Connector change resilience (APIs differ and change often).
- **P9b-1** OCR/LLM extraction step that turns unstructured input into candidate tables *before* the normal pipeline.
- **P9b-2** Mandatory human-review fallback for low-confidence extractions.

## Deliverables

*(To be defined when scoped.)*

## Acceptance Criteria

*(To be defined when scoped.)*

## Dependencies

Deferred — would build on the full core (Phases 0–8).

## Open Questions

- Whether/when to add API connectors (PRD §2.3).
- Whether/when to add PDF/email extraction (PRD §2.3).
- Depth of connector support and per-platform maintenance budget.

## Sub-phases

TBD — to be broken down before implementation.
