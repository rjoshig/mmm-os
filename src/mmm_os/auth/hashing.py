"""Password hashing and session-token helpers (Phase 00.5, stdlib only).

Passwords use PBKDF2-HMAC-SHA256 with a per-user random salt (no third-party
dependency). Session tokens are random and stored **hashed** (HMAC with a pepper
from the ``SecretStore``, CC-12) so a DB leak does not expose usable tokens.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

_PBKDF2_ROUNDS = 240_000
_SALT_BYTES = 16
_TOKEN_BYTES = 32


def hash_password(password: str, *, salt: str | None = None) -> tuple[str, str]:
    """Hash ``password``; return ``(hash_hex, salt_hex)``.

    Args:
        password: The plaintext password.
        salt: Optional existing salt (hex) to verify against; a new random salt is
            generated when omitted.
    """
    salt_hex = salt or secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), _PBKDF2_ROUNDS
    )
    return digest.hex(), salt_hex


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Return whether ``password`` matches the stored hash (constant-time)."""
    candidate, _ = hash_password(password, salt=salt)
    return hmac.compare_digest(candidate, password_hash)


def new_session_token() -> str:
    """Return a fresh, URL-safe random session token."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(token: str, pepper: bytes) -> str:
    """Return the at-rest hash of a session token (HMAC-SHA256 with a pepper)."""
    return hmac.new(pepper, token.encode("utf-8"), hashlib.sha256).hexdigest()
