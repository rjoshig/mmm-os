# Phase 5.1 — LLM Provider Abstraction & Config

**Parent:** [`phase-05`](./phase-05-ai-suggestion-layer.md) ·
**Depends on:** Phases 2, 3, 4 · **Status:** Done (pending PR merge)

Realises ADR-008 (dual OpenAI + Anthropic, off by default, config/env-driven).

## Objective

A provider-agnostic LLM client that supports **both the OpenAI API format and the
Anthropic SDK**, selected by config/env, **off by default**, and swappable by
changing only configuration.

## Scope

- **In:** `LLMConfig` loaded from env and/or an optional JSON file; provider
  auto-inference from model name; `LLMClient` interface with OpenAI and Anthropic
  backends (lazy-imported optional SDKs); a client factory that refuses to build
  when disabled.
- **Out:** the suggestion prompts / storage / review loop (05.2).

## Functional Requirements

- **P5.1-1 Off by default:** `enabled` defaults to **false**; the LLM is inert until explicitly turned on.
- **P5.1-2 Dual provider:** `provider` is `auto` | `openai` | `anthropic`; both an OpenAI backend (also OpenAI-compatible via `base_url`) and an Anthropic backend are provided.
- **P5.1-3 Config-only switching:** provider/model/key/thresholds come from env **or** a JSON config file (`LLM_CONFIG_FILE`), env overriding JSON. When `provider = auto`, the provider is inferred from the model name (`gpt*`/`o*` → OpenAI, `claude*` → Anthropic).
- **P5.1-4 Interface:** handlers depend on an `LLMClient` protocol (`complete(system, user) -> str`), so a fake can be injected in tests — no SDK/network required.
- **P5.1-5 Secrets via env:** API keys come from `LLM_API_KEY` or `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`; never hardcoded. SDKs are optional deps (`mmm-os[llm]`), imported lazily.

## Deliverables

- `src/mmm_os/ai/` — `errors`, `config` (loader + provider inference), `client` (interface + OpenAI/Anthropic backends + factory).
- `llm.config.example.json` + `.env.example` LLM keys.
- Tests: default disabled; provider inference; env + JSON config load/override; factory refuses when disabled; key fallback.

## Acceptance Criteria

- With no config, the LLM is disabled and the factory raises `LLMDisabledError`.
- Setting `LLM_ENABLED=true` + `LLM_MODEL=gpt-4o-mini` yields an OpenAI client; `claude-*` yields an Anthropic client — no code change.
- A JSON config file is honoured; env overrides it.
- The SDKs are optional; the core imports and runs without them.

## Dependencies

Phases 2, 3, 4.

## Open Questions

OQ-5.1 (provider) resolved to dual OpenAI+Anthropic; cost ceiling still open.

## Sub-phases

N/A (leaf sub-phase).
