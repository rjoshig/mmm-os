# Phase 9.2 — Connector Framework & Credentials

**Parent:** [`phase-09`](./phase-09-future-connectors-extraction.md) ·
**Depends on:** 09.1, Phase 8 (encryption) · **Status:** Done — full framework with mock partner clients (live API calls behind a `ReportClient` seam).

## Objective

Provide the shared scaffolding for **API-based** partner connectors on top of
`SourceConnector`, plus secure per-customer credential management (CC-10).

## Scope

- **In:** an API-connector base (pagination, rate limiting, retry/backoff,
  response→`LandedDataset` normalisation); the OAuth2/token lifecycle; the
  encrypted, tenant-scoped credential store (`connector_credential`).
- **Out:** any specific partner; scheduling (09.6).

## Functional Requirements

- **P9.2-1** A connector base class partners subclass, emitting `LandedDataset`
  records with a known column schema (no header detection).
- **P9.2-2** OAuth2 per customer per partner, plus long-lived/system-user tokens
  where a partner uses Business-Manager-style access.
- **P9.2-3** Tokens **encrypted at rest, tenant-scoped, least-privilege read-only
  reporting scopes, auto-refreshed**; expiry/revocation surfaced as clear errors;
  **never logged** (CC-10).
- **P9.2-4** `connector` catalog + `connector_config` (per tenant + connector).

## Deliverables

- `src/mmm_os/connectors/base.py`, `credentials.py` (currently placeholders).
- ORM + migrations for `connector`, `connector_config`, `connector_credential`.
- Credential encryption integration (Phase 8).

## Acceptance Criteria

- A connector can authenticate against a test account and refresh an expiring
  token without manual intervention.
- Credentials are encrypted at rest and never appear in logs or error output.

## Dependencies

09.1; Phase 8 (encryption); Phase 2 (template layer, for 09.7).

## Open Questions

OQ-9.2 (API approval lead times), OQ-9.3 (auth model per partner), OQ-9.6
(aggregate-only scope).

## Sub-phases

N/A (leaf sub-phase).
