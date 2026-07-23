"""Authentication + secrets models (Phases 00.5 / 00.6).

``Session`` backs login sessions (CC-11). ``SecretRef`` is a pointer + metadata for
a secret whose value lives in the ``SecretStore`` — never in the DB (CC-12).
``IdentityProviderConfig`` holds per-tenant SSO settings (OIDC/SAML), with secret
material referenced via the store.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Session(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A login session. The raw token is never stored — only its hash (CC-12)."""

    __tablename__ = "session"
    __table_args__ = (UniqueConstraint("token_hash"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SecretRef(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A pointer + metadata for a stored secret. **Never holds the value** (CC-12).

    Not tenant-scoped via the mixin: some secrets are global (e.g. the session
    pepper). Tenant-scoped secrets set ``tenant_id`` explicitly (nullable).
    """

    __tablename__ = "secret_ref"
    __table_args__ = (UniqueConstraint("name"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, default="opaque")
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tenant.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IdentityProviderConfig(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Per-tenant SSO configuration (OIDC/SAML). Secrets via ``SecretRef`` (CC-12)."""

    __tablename__ = "identity_provider_config"
    __table_args__ = (UniqueConstraint("tenant_id", "kind"),)

    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # "oidc" | "saml"
    issuer: Mapped[str | None] = mapped_column(String(1024))
    client_id: Mapped[str | None] = mapped_column(String(255))
    # Client secret / signing cert are NOT stored here — only a reference name.
    secret_ref_name: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
