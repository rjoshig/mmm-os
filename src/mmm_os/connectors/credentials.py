"""Connector credential management (Phase 9 — deferred; placeholder only).

Will define the token storage/refresh interface for partner auth: OAuth2 per
customer per partner (plus long-lived/system-user tokens), with credentials
encrypted at rest, tenant-scoped, least-privilege read-only reporting scopes,
auto-refresh, and graceful expiry/revocation handling. Tokens are never logged
(CC-10). Backed by the ``connector_credential`` entity and Phase-8 encryption.

No logic is implemented yet — see Phase 9.2.
"""
