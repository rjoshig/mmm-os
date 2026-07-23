"""Connector credential storage (Phase 9, CC-10 / CC-12).

Partner tokens are stored in the ``SecretStore`` (encrypted at rest, never logged);
the database holds only a ``ConnectorCredential`` reference. This module never
returns or logs the token except through :func:`load_token`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.models import ConnectorCredential
from mmm_os.secrets.base import SecretStore


def _secret_name(config_id: uuid.UUID) -> str:
    """Return the SecretStore key for a connector config's token."""
    return f"connector/{config_id}/token"


def store_token(
    session: Session,
    store: SecretStore,
    *,
    tenant_id: uuid.UUID,
    connector_config_id: uuid.UUID,
    token: str,
    scopes: list[str] | None = None,
    expires_at: datetime | None = None,
) -> ConnectorCredential:
    """Encrypt + store a partner token and upsert its DB reference (CC-10)."""
    name = _secret_name(connector_config_id)
    store.put(name, token.encode("utf-8"))
    credential = session.scalar(
        select(ConnectorCredential).where(
            ConnectorCredential.connector_config_id == connector_config_id
        )
    )
    if credential is None:
        credential = ConnectorCredential(
            tenant_id=tenant_id,
            connector_config_id=connector_config_id,
            secret_ref_name=name,
        )
        session.add(credential)
    credential.scopes = scopes
    credential.expires_at = expires_at
    session.flush()
    return credential


def load_token(store: SecretStore, credential: ConnectorCredential) -> str:
    """Return the decrypted token for a credential (from the SecretStore)."""
    return store.get(credential.secret_ref_name).decode("utf-8")
