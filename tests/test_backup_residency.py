"""Tests for portable backup/restore + residency enforcement (Phase 10)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

from mmm_os.core.config import Settings
from mmm_os.db.base import Base
from mmm_os.governance.backup import export_backup, import_backup
from mmm_os.governance.residency import ResidencyError, check_database_residency
from mmm_os.models import ConnectorConfig, Tenant


def _fresh(path: Path, name: str) -> Engine:
    engine = create_engine(f"sqlite:///{path / name}")
    Base.metadata.create_all(engine)
    return engine


def test_backup_roundtrips_across_databases(tmp_path: Path) -> None:
    """A logical backup of one DB restores into a fresh DB with identical rows.

    Exercises the tricky value types (UUID PK, JSON columns, datetimes)."""
    src = _fresh(tmp_path, "src.db")
    tid = uuid.uuid4()
    with Session(src) as s:
        s.add(Tenant(id=tid, name="Backup Co", slug="backup-co", region="eu"))
        s.add(
            ConnectorConfig(
                tenant_id=tid,
                connector_key="meta",
                name="Meta",
                account_ids=["act_1", "act_2"],  # JSON column
                settings={"schedule": {"interval_minutes": 60}},  # JSON column
            )
        )
        s.commit()

    archive = export_backup(src, tmp_path / "archive")
    assert (archive / "manifest.json").exists()

    # Restore into a brand-new database and verify parity.
    dst = _fresh(tmp_path, "dst.db")
    restored = import_backup(dst, archive)
    assert restored["tenant"] == 1
    assert restored["connector_config"] == 1

    with Session(dst) as s:
        tenant = s.get(Tenant, tid)
        assert tenant is not None and tenant.slug == "backup-co" and tenant.region == "eu"
        cfg = s.scalar(select(ConnectorConfig).where(ConnectorConfig.tenant_id == tid))
        assert cfg is not None
        assert cfg.account_ids == ["act_1", "act_2"]
        assert cfg.settings["schedule"]["interval_minutes"] == 60


def test_import_truncates_before_restore(tmp_path: Path) -> None:
    """Restoring replaces existing rows (truncate=True) rather than duplicating."""
    src = _fresh(tmp_path, "src.db")
    with Session(src) as s:
        s.add(Tenant(id=uuid.uuid4(), name="A", slug="a"))
        s.commit()
    archive = export_backup(src, tmp_path / "arc")

    dst = _fresh(tmp_path, "dst.db")
    with Session(dst) as s:
        s.add(Tenant(id=uuid.uuid4(), name="stale", slug="stale"))
        s.commit()
    import_backup(dst, archive)
    with Session(dst) as s:
        tenants = s.scalars(select(Tenant)).all()
        assert [t.slug for t in tenants] == ["a"]  # stale row gone


def test_residency_noop_when_disabled() -> None:
    settings = Settings(residency_enforced=False)
    # Any URL is fine when enforcement is off.
    check_database_residency(settings, "eu", "postgresql+psycopg://x@us-east-1.db/mmm")


def test_residency_allows_matching_region() -> None:
    settings = Settings(
        residency_enforced=True, residency_region_hosts="eu=eu-,europe;us=us-,useast"
    )
    check_database_residency(settings, "eu", "postgresql+psycopg://x@eu-west-1.db/mmm")


def test_residency_rejects_cross_region() -> None:
    settings = Settings(
        residency_enforced=True, residency_region_hosts="eu=eu-,europe;us=us-,useast"
    )
    with pytest.raises(ResidencyError):
        check_database_residency(settings, "eu", "postgresql+psycopg://x@us-east-1.db/mmm")


def test_residency_rejects_region_without_hosts() -> None:
    settings = Settings(residency_enforced=True, residency_region_hosts="eu=eu-")
    with pytest.raises(ResidencyError):
        check_database_residency(settings, "apac", "postgresql+psycopg://x@apac-1.db/mmm")
