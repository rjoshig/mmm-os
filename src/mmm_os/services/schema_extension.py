"""Tenant schema-extension registry + resolved-schema (Phase 21, ADR-015)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from mmm_os.canonical import CanonicalConfig
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.models import SchemaExtension

_KINDS = {"dimension", "measure", "factor"}


@dataclass(frozen=True)
class ResolvedField:
    """A field in the resolved schema (canonical core or a tenant extension)."""

    name: str
    kind: str  # dimension | measure | factor
    type: str
    source: str  # core | extension


def register_extension(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    kind: str,
    name: str,
    data_type: str = "string",
    taxonomy_ref: str | None = None,
    validation: str | None = None,
) -> SchemaExtension:
    """Register (or update) a tenant schema extension. Raises on an invalid kind."""
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {sorted(_KINDS)}")
    name = name.strip()
    existing = session.scalar(
        tenant_scoped_select(SchemaExtension, tenant_id).where(SchemaExtension.name == name)
    )
    if existing is not None:
        existing.kind = kind
        existing.data_type = data_type
        existing.taxonomy_ref = taxonomy_ref
        existing.validation = validation
        existing.version += 1
        session.flush()
        return existing
    ext = SchemaExtension(
        tenant_id=tenant_id,
        kind=kind,
        name=name,
        data_type=data_type,
        taxonomy_ref=taxonomy_ref,
        validation=validation,
    )
    session.add(ext)
    session.flush()
    return ext


def list_extensions(
    session: Session, tenant_id: uuid.UUID, kind: str | None = None
) -> list[SchemaExtension]:
    """Return a tenant's schema extensions (optionally filtered by kind)."""
    query = tenant_scoped_select(SchemaExtension, tenant_id).order_by(SchemaExtension.name)
    if kind is not None:
        query = query.where(SchemaExtension.kind == kind)
    return list(session.scalars(query).all())


def delete_extension(session: Session, tenant_id: uuid.UUID, ext_id: uuid.UUID) -> bool:
    """Delete a tenant's schema extension; return whether it existed."""
    ext = session.scalar(
        tenant_scoped_select(SchemaExtension, tenant_id).where(SchemaExtension.id == ext_id)
    )
    if ext is None:
        return False
    session.delete(ext)
    session.flush()
    return True


def resolved_fields(
    session: Session, tenant_id: uuid.UUID, canonical: CanonicalConfig
) -> list[ResolvedField]:
    """Return the resolved schema: canonical core fields + this tenant's extensions.

    The UI and engines read this so a custom dimension/measure/factor auto-appears
    as a mapping target, transform target, validation subject, and output column —
    "add a dimension = a registry row, zero code" (ADR-015).
    """
    schema = canonical.schema
    fields: list[ResolvedField] = []
    for kind, group in (
        ("dimension", schema.dimensions),
        ("measure", schema.measures),
        ("factor", schema.factors),
    ):
        fields += [
            ResolvedField(name=f.name, kind=kind, type=f.type.value, source="core") for f in group
        ]
    for ext in list_extensions(session, tenant_id):
        if ext.lifecycle_status != "published":
            continue
        fields.append(
            ResolvedField(name=ext.name, kind=ext.kind, type=ext.data_type, source="extension")
        )
    return fields


def custom_checks(session: Session, tenant_id: uuid.UUID) -> list[tuple[str, str]]:
    """Return (name, expression) pairs for extensions carrying a validation expression."""
    return [
        (ext.name, ext.validation)
        for ext in list_extensions(session, tenant_id)
        if ext.validation
    ]
