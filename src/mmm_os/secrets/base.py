"""The secrets abstraction (CC-12, Phase 00.6).

All sensitive material — app/signing keys, auth secrets, and (Phase 9) partner
OAuth tokens — flows through a ``SecretStore``. The application database stores
only a ``secret_ref`` (pointer + metadata); the value itself lives here, never in
plaintext at rest and never logged. Callers depend on this interface, so the
backend swaps (local dev → managed KMS/vault) by config only.
"""

from __future__ import annotations

import abc
from collections.abc import Callable


class SecretNotFoundError(KeyError):
    """Raised when a secret name is not present in the store."""


class SecretStore(abc.ABC):
    """Abstract, pluggable store for named secret values.

    Names are opaque keys (e.g. ``"auth/session-pepper"`` or
    ``"connector/<id>/oauth-token"``). Values are bytes, encrypted at rest by the
    backend. Implementations MUST NOT log secret values.
    """

    @abc.abstractmethod
    def put(self, name: str, value: bytes) -> None:
        """Store (or overwrite) the secret ``value`` under ``name``."""

    @abc.abstractmethod
    def get(self, name: str) -> bytes:
        """Return the secret stored under ``name``.

        Raises:
            SecretNotFoundError: If ``name`` has no stored value.
        """

    @abc.abstractmethod
    def delete(self, name: str) -> None:
        """Delete the secret under ``name`` (no error if absent)."""

    @abc.abstractmethod
    def exists(self, name: str) -> bool:
        """Return whether a secret is stored under ``name``."""

    def get_or_create(self, name: str, factory: Callable[[], bytes]) -> bytes:
        """Return the secret under ``name``, creating it via ``factory`` if absent.

        Used for self-provisioning secrets (e.g. a session pepper generated once
        on first boot). Not atomic across processes — acceptable for the dev
        backend; a real KMS backend provides stronger guarantees.
        """
        if self.exists(name):
            return self.get(name)
        value = factory()
        self.put(name, value)
        return value
