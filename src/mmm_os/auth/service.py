"""Authentication service: login, sessions, and the default-admin seed (00.5).

Sessions are DB-backed; the raw token is returned to the client once and stored
only as an HMAC hash (pepper from the ``SecretStore``, CC-12). All functions are
tenant-aware — a resolved session yields the user's ``(user, tenant_id)``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from mmm_os.auth.hashing import (
    hash_password,
    hash_token,
    new_session_token,
    verify_password,
)
from mmm_os.core.config import Settings
from mmm_os.models import Session as SessionModel
from mmm_os.models import Tenant, User
from mmm_os.models.mixins import utcnow
from mmm_os.secrets.base import SecretStore

# The pepper is a global secret, self-provisioned on first use (CC-12).
SESSION_PEPPER_SECRET = "auth/session-pepper"


@dataclass(frozen=True)
class Principal:
    """The authenticated identity resolved for a request."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str


def _as_utc(value: datetime) -> datetime:
    """Treat a naive datetime (SQLite reads) as UTC for safe comparison."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _pepper(store: SecretStore) -> bytes:
    """Return the session-token pepper, creating it once if absent."""
    import secrets as _secrets

    return store.get_or_create(SESSION_PEPPER_SECRET, lambda: _secrets.token_bytes(32))


def authenticate(session: DbSession, *, email: str, password: str) -> User | None:
    """Return the active user matching ``email`` + ``password``, or ``None``."""
    user = session.scalar(select(User).where(User.email == email))
    if user is None or user.status != "active":
        return None
    if not user.password_hash or not user.password_salt:
        return None
    if not verify_password(password, user.password_hash, user.password_salt):
        return None
    return user


def create_session(session: DbSession, store: SecretStore, *, user: User, ttl_hours: int) -> str:
    """Create a login session for ``user`` and return the raw token (shown once)."""
    token = new_session_token()
    record = SessionModel(
        tenant_id=user.tenant_id,
        user_id=user.id,
        token_hash=hash_token(token, _pepper(store)),
        expires_at=utcnow() + timedelta(hours=ttl_hours),
    )
    session.add(record)
    session.flush()
    return token


def resolve_session(session: DbSession, store: SecretStore, *, token: str) -> Principal | None:
    """Resolve a raw token to a ``Principal``, or ``None`` if invalid/expired."""
    token_hash = hash_token(token, _pepper(store))
    record = session.scalar(select(SessionModel).where(SessionModel.token_hash == token_hash))
    if record is None or record.revoked_at is not None:
        return None
    if _as_utc(record.expires_at) <= utcnow():
        return None
    user = session.get(User, record.user_id)
    if user is None or user.status != "active":
        return None
    return Principal(user_id=user.id, tenant_id=user.tenant_id, email=user.email, role=user.role)


def revoke_session(session: DbSession, store: SecretStore, *, token: str) -> bool:
    """Revoke the session for ``token``. Returns whether a session was revoked."""
    token_hash = hash_token(token, _pepper(store))
    record = session.scalar(select(SessionModel).where(SessionModel.token_hash == token_hash))
    if record is None or record.revoked_at is not None:
        return False
    record.revoked_at = utcnow()
    session.flush()
    return True


def seed_default_admin(session: DbSession, settings: Settings) -> User:
    """Ensure a default tenant + admin user exist (idempotent). Dev convenience."""
    tenant = session.scalar(select(Tenant).where(Tenant.slug == settings.default_tenant_slug))
    if tenant is None:
        tenant = Tenant(name="Default", slug=settings.default_tenant_slug)
        session.add(tenant)
        session.flush()

    admin = session.scalar(
        select(User).where(User.tenant_id == tenant.id, User.email == settings.default_admin_email)
    )
    if admin is None:
        pw_hash, salt = hash_password(settings.default_admin_password)
        admin = User(
            tenant_id=tenant.id,
            email=settings.default_admin_email,
            display_name="Administrator",
            role="admin",
            status="active",
            password_hash=pw_hash,
            password_salt=salt,
        )
        session.add(admin)
        session.flush()
    return admin
