"""Schemas for the config library (Phase 13, Slice 1): browse saved configs + authors."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ConfigLibraryItem(BaseModel):
    """A saved config family (all versions of one mapping signature or rule-set name)."""

    kind: str  # "mapping" | "rule_set"
    key: str  # file signature (mapping) or name (rule set) — used to fetch versions
    name: str
    layer: str
    latest_version: int
    version_count: int
    updated_at: datetime
    created_by_email: str | None


class ConfigLibraryResponse(BaseModel):
    """The tenant's saved mapping configs + rule sets, one entry per family."""

    items: list[ConfigLibraryItem]


class ConfigVersionItem(BaseModel):
    """One version of a config family, for the version-history / diff view."""

    version: int
    layer: str
    status: str  # draft | published | archived (Phase 13.2)
    created_at: datetime
    created_by_email: str | None
    summary: str  # e.g. "6 columns mapped" or "3 rules"


class ConfigVersionsResponse(BaseModel):
    """The version history of a single config family."""

    kind: str
    key: str
    versions: list[ConfigVersionItem]


class PublishRequest(BaseModel):
    """Publish (or archive) a specific config version (Phase 13.2)."""

    kind: str  # "mapping" | "rule_set"
    key: str
    version: int
    status: str = "published"  # published | archived
