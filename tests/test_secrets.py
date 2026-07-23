"""Tests for the SecretStore (Phase 00.6, CC-12)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mmm_os.secrets import LocalEncryptedSecretStore, SecretNotFoundError


def test_round_trip_and_encrypted_at_rest(tmp_path: Path) -> None:
    """A stored secret round-trips; the on-disk bytes are not the plaintext."""
    store = LocalEncryptedSecretStore(tmp_path / "s", b"master-key")
    store.put("auth/pepper", b"super-secret-value")

    assert store.exists("auth/pepper")
    assert store.get("auth/pepper") == b"super-secret-value"

    # No plaintext at rest: no file under the root contains the raw value.
    for f in (tmp_path / "s").iterdir():
        assert b"super-secret-value" not in f.read_bytes()


def test_missing_secret_raises(tmp_path: Path) -> None:
    """Reading an unknown secret raises SecretNotFoundError."""
    store = LocalEncryptedSecretStore(tmp_path / "s", b"master-key")
    with pytest.raises(SecretNotFoundError):
        store.get("nope")


def test_tamper_detection(tmp_path: Path) -> None:
    """Flipping a ciphertext byte fails the integrity check on read."""
    store = LocalEncryptedSecretStore(tmp_path / "s", b"master-key")
    store.put("k", b"value")
    (blob_path,) = list((tmp_path / "s").iterdir())
    data = bytearray(blob_path.read_bytes())
    data[-1] ^= 0x01
    blob_path.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="integrity"):
        store.get("k")


def test_get_or_create(tmp_path: Path) -> None:
    """get_or_create provisions once and returns the same value thereafter."""
    store = LocalEncryptedSecretStore(tmp_path / "s", b"master-key")
    first = store.get_or_create("once", lambda: b"generated")
    second = store.get_or_create("once", lambda: b"different")
    assert first == b"generated"
    assert second == b"generated"
