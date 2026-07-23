"""Pydantic v2 schemas for the transformation API (03.2)."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from mmm_os.models.enums import RuleLayer


class RuleSpecIn(BaseModel):
    """A rule as supplied by a caller."""

    target_field: str = ""
    operation: str
    params: dict[str, Any] = Field(default_factory=dict)
    condition: dict[str, Any] | None = None
    order: int = 0
    layer: str = RuleLayer.CUSTOMER.value


class PreviewRequest(BaseModel):
    """Request to preview a rule set on sample rows."""

    rows: list[dict[str, Any]]
    rules: list[RuleSpecIn]
    limit: int | None = None


class PreviewResponse(BaseModel):
    """Before/after result of a preview."""

    before: list[dict[str, Any]]
    after: list[dict[str, Any]]


class SaveRuleSetRequest(BaseModel):
    """Request to save (version) a rule set by explicit name."""

    name: str = Field(min_length=1, max_length=255)
    layer: str = RuleLayer.CUSTOMER.value
    rules: list[RuleSpecIn]


class SaveSheetRuleSetRequest(BaseModel):
    """Request to save a rule set for a sheet.

    The rule-set name is derived server-side from the sheet's column signature
    (rule sets are reused across files with identical headers), so callers supply
    only the layer and rules — never a name.
    """

    layer: str = RuleLayer.CUSTOMER.value
    rules: list[RuleSpecIn]
    draft: bool = False  # save as a draft (Phase 13.2); default publishes immediately


class RuleSetRead(BaseModel):
    """A saved rule set as returned to callers."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    version: int
    layer: str
    rules: list[RuleSpecIn]
