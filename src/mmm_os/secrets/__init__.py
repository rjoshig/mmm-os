"""Secrets management (CC-12, Phase 00.6).

A single ``SecretStore`` abstraction for all sensitive material — app/signing
keys, auth secrets, and (Phase 9) partner OAuth tokens. Local encrypted-dev
backend now; pluggable KMS/vault later. The DB stores only a ``secret_ref``
pointer, never the value.
"""

from mmm_os.secrets.base import SecretNotFoundError, SecretStore
from mmm_os.secrets.factory import build_secret_store, get_secret_store
from mmm_os.secrets.local import LocalEncryptedSecretStore

__all__ = [
    "LocalEncryptedSecretStore",
    "SecretNotFoundError",
    "SecretStore",
    "build_secret_store",
    "get_secret_store",
]
