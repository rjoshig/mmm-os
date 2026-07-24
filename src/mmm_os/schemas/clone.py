"""Schemas for universal clone / duplicate (Phase 15)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class CloneRequest(BaseModel):
    """Clone options: an optional new name and (admin) a target tenant."""

    new_name: str | None = None
    target_tenant_id: uuid.UUID | None = None


class CloneResponse(BaseModel):
    """The identity of a freshly cloned entity."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    cloned_from: uuid.UUID | None


class CustomerCloneResponse(BaseModel):
    """Per-entity counts of a bulk customer-config clone."""

    target_tenant_id: uuid.UUID
    counts: dict[str, int]
