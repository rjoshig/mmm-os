"""Application authentication (Phase 00.5, CC-11).

Password login with DB-backed sessions; tokens stored hashed with a pepper from
the ``SecretStore`` (CC-12). Distinct from partner-connector credentials (Phase 9).
"""

from mmm_os.auth.service import (
    Principal,
    authenticate,
    create_session,
    resolve_session,
    revoke_session,
    seed_default_admin,
)

__all__ = [
    "Principal",
    "authenticate",
    "create_session",
    "resolve_session",
    "revoke_session",
    "seed_default_admin",
]
