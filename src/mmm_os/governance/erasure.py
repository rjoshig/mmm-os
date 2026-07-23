"""Right-to-erasure (Phase 10, P10-3).

Deletes a tenant's data on request. Reconciles the tensions in OQ-10-3:

- **Immutable raw (CC-2):** erasure is the governance-authorized exception — raw
  bytes are deleted (never overwritten).
- **Audit trail:** erasure **keeps** the ``audit_log`` and ``user`` identity rows and
  the ``tenant`` shell, and the erasure event itself is recorded — so *what was
  erased* stays provable while the *data* is gone.

``erase_file`` removes one file + all data derived from it (reusing the retention
cascade). ``erase_tenant`` removes **all** of a tenant's data-bearing rows + storage.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mmm_os.db.base import Base
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.governance.retention import delete_file_data
from mmm_os.ingestion.service import storage_key_for
from mmm_os.models import File
from mmm_os.storage.base import ObjectStorage

# Kept on a tenant erasure: account identity + the compliance audit trail + the
# tenant shell. Everything else tenant-scoped is deleted.
_ERASE_KEEP = frozenset({"user", "audit_log", "tenant"})


def _tenant_scoped_models() -> list[type]:
    """All ORM classes carrying a ``tenant_id`` column (future-proof discovery)."""
    return [m.class_ for m in Base.registry.mappers if "tenant_id" in m.columns]


def erase_file(
    session: Session, storage: ObjectStorage, tenant_id: uuid.UUID, file_id: uuid.UUID
) -> bool:
    """Erase one file + all data derived from it. Returns ``False`` if not found."""
    file = session.scalar(tenant_scoped_select(File, tenant_id).where(File.id == file_id))
    if file is None:
        return False
    delete_file_data(session, storage, tenant_id, file)
    session.flush()
    return True


def erase_tenant(
    session: Session, storage: ObjectStorage, tenant_id: uuid.UUID
) -> dict[str, int]:
    """Erase all of a tenant's data (right-to-be-forgotten); return per-table counts.

    Deletes every data-bearing tenant-scoped row + all raw-file bytes, keeping only
    the user identities, the audit log, and the tenant shell (see module docstring).
    """
    for file in session.scalars(select(File).where(File.tenant_id == tenant_id)):
        storage.delete(storage_key_for(file))

    summary: dict[str, int] = {}
    for cls in _tenant_scoped_models():
        if cls.__tablename__ in _ERASE_KEEP:  # type: ignore[attr-defined]
            continue
        result = session.execute(delete(cls).where(cls.tenant_id == tenant_id))  # type: ignore[attr-defined]
        count = int(result.rowcount or 0)  # type: ignore[attr-defined]
        if count:
            summary[cls.__tablename__] = count  # type: ignore[attr-defined]
    session.flush()
    return summary
