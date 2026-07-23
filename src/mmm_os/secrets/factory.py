"""Select and build the configured ``SecretStore`` backend (Phase 00.6)."""

from __future__ import annotations

import hashlib
from functools import lru_cache

from mmm_os.core.config import Settings, get_settings
from mmm_os.secrets.base import SecretStore
from mmm_os.secrets.local import LocalEncryptedSecretStore


def build_secret_store(settings: Settings) -> SecretStore:
    """Build a ``SecretStore`` from settings.

    ``secrets_backend = "local"`` (dev) encrypts values on disk under a key derived
    from ``secret_master_key``. A managed KMS/vault backend (OQ-00.6-2) plugs in
    here without changing callers.
    """
    if settings.secrets_backend == "local":
        # Derive a fixed-length key from the configured master key material.
        master = hashlib.sha256(settings.secret_master_key.encode("utf-8")).digest()
        return LocalEncryptedSecretStore(settings.secrets_local_path, master)
    raise ValueError(f"unknown secrets backend: {settings.secrets_backend!r}")


@lru_cache
def get_secret_store() -> SecretStore:
    """Return the process-wide secret store (cached)."""
    return build_secret_store(get_settings())
