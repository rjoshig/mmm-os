"""Local encrypted-dev ``SecretStore`` backend (Phase 00.6).

Encrypts each secret at rest under a per-store master key and writes the ciphertext
to a directory (one file per secret name). **No plaintext at rest** (CC-12).

The cipher is built from Python's standard library only (no third-party crypto
dependency in dev): an HMAC-SHA256 keystream (counter mode) for confidentiality
plus a separate HMAC-SHA256 tag over the ciphertext (encrypt-then-MAC) for
integrity. This is a legitimate construction for **development**; production MUST
use a managed KMS/vault backend behind this same interface (OQ-00.6-2).
"""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

from mmm_os.secrets.base import SecretNotFoundError, SecretStore

_MAGIC = b"MMMS1"  # versioned envelope prefix
_NONCE_LEN = 16
_TAG_LEN = 32


def _derive(master: bytes, label: bytes) -> bytes:
    """Derive a subkey for ``label`` from the master key."""
    return hmac.new(master, label, hashlib.sha256).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """Generate ``length`` keystream bytes as HMAC(key, nonce || counter)."""
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def _safe_name(name: str) -> str:
    """Map a secret name to a stable, filesystem-safe filename (never reversible)."""
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


class LocalEncryptedSecretStore(SecretStore):
    """A filesystem ``SecretStore`` that encrypts values at rest (dev only).

    Args:
        root: Directory to hold encrypted secret files (created if missing).
        master_key: The at-rest encryption key. In dev it comes from the
            environment (never hardcoded); production uses a KMS backend instead.
    """

    def __init__(self, root: Path | str, master_key: bytes) -> None:
        """Bind the store to ``root`` and derive enc/mac subkeys from ``master_key``."""
        if not master_key:
            raise ValueError("master_key must be non-empty")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._enc_key = _derive(master_key, b"enc")
        self._mac_key = _derive(master_key, b"mac")

    def _path(self, name: str) -> Path:
        return self.root / _safe_name(name)

    def put(self, name: str, value: bytes) -> None:
        """Encrypt ``value`` and write it to disk under ``name``."""
        nonce = os.urandom(_NONCE_LEN)
        ciphertext = bytes(
            a ^ b for a, b in zip(value, _keystream(self._enc_key, nonce, len(value)), strict=True)
        )
        tag = hmac.new(self._mac_key, _MAGIC + nonce + ciphertext, hashlib.sha256).digest()
        self._path(name).write_bytes(_MAGIC + nonce + tag + ciphertext)

    def get(self, name: str) -> bytes:
        """Read + verify + decrypt the secret under ``name``."""
        path = self._path(name)
        if not path.exists():
            raise SecretNotFoundError(name)
        blob = path.read_bytes()
        prefix = len(_MAGIC)
        nonce = blob[prefix : prefix + _NONCE_LEN]
        tag = blob[prefix + _NONCE_LEN : prefix + _NONCE_LEN + _TAG_LEN]
        ciphertext = blob[prefix + _NONCE_LEN + _TAG_LEN :]
        expected = hmac.new(self._mac_key, _MAGIC + nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected):
            raise ValueError(f"secret {name!r} failed integrity check")
        return bytes(
            a ^ b
            for a, b in zip(
                ciphertext, _keystream(self._enc_key, nonce, len(ciphertext)), strict=True
            )
        )

    def delete(self, name: str) -> None:
        """Delete the secret under ``name`` (idempotent)."""
        self._path(name).unlink(missing_ok=True)

    def exists(self, name: str) -> bool:
        """Return whether a secret is stored under ``name``."""
        return self._path(name).exists()
