"""Authentication routes: login, logout, and current-principal (Phase 00.5).

These are the only feature routes that are **not** behind ``require_auth`` — login
is the entry point. Tokens are Bearer tokens; the raw token is returned once and
stored only as a hash (CC-12).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_secret_store_dep
from mmm_os.auth.service import (
    Principal,
    authenticate,
    create_session,
    resolve_session,
    revoke_session,
)
from mmm_os.core.config import Settings, get_settings
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.schemas.auth import LoginRequest, LoginResponse, PrincipalRead
from mmm_os.secrets import SecretStore

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    session: Session = Depends(get_session),
    store: SecretStore = Depends(get_secret_store_dep),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    """Authenticate credentials and issue a session token."""
    user = authenticate(session, email=body.email, password=body.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    token = create_session(session, store, user=user, ttl_hours=settings.session_ttl_hours)
    actor = Principal(user_id=user.id, tenant_id=user.tenant_id, email=user.email, role=user.role)
    record_audit(
        session,
        tenant_id=user.tenant_id,
        action="auth.login",
        principal=actor,
        target_type="user",
        target_id=str(user.id),
    )
    session.commit()
    return LoginResponse(
        token=token,
        principal=PrincipalRead(
            user_id=user.id, tenant_id=user.tenant_id, email=user.email, role=user.role
        ),
    )


@router.get("/me", response_model=PrincipalRead)
def me(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
    store: SecretStore = Depends(get_secret_store_dep),
) -> PrincipalRead:
    """Return the principal for the presented Bearer token (401 if invalid)."""
    token = _bearer(authorization)
    principal = resolve_session(session, store, token=token) if token else None
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    return PrincipalRead(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        email=principal.email,
        role=principal.role,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
    store: SecretStore = Depends(get_secret_store_dep),
) -> None:
    """Revoke the presented session token (idempotent)."""
    token = _bearer(authorization)
    if token:
        revoke_session(session, store, token=token)
        session.commit()


def _bearer(authorization: str | None) -> str | None:
    """Extract the token from a ``Bearer <token>`` header."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization[len("bearer ") :].strip()
