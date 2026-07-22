"""Tests for the Phase 0.2 ORM models and tenant scoping."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mmm_os.db.base import Base
from mmm_os.models import Tenant, User

EXPECTED_TABLES = {
    "tenant",
    "user",
    "file",
    "sheet",
    "profile",
    "mapping_config",
    "taxonomy",
    "taxonomy_alias",
    "rule_set",
    "rule",
    "job",
    "job_event",
    "validation_flag",
    "suggestion",
    "output_row",
}


def test_all_phase0_tables_registered() -> None:
    """Importing models registers every Phase-0 table on Base.metadata."""
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_every_domain_table_has_tenant_id() -> None:
    """Every domain table except the tenant root carries tenant_id (CC-1)."""
    for name, table in Base.metadata.tables.items():
        if name == "tenant":
            continue
        assert "tenant_id" in table.columns, f"{name} is missing tenant_id"


def test_output_row_has_traceability_columns() -> None:
    """output_row carries full traceability metadata (CC-3)."""
    cols = set(Base.metadata.tables["output_row"].columns.keys())
    assert {
        "source_file_id",
        "source_sheet",
        "source_row",
        "mapping_config_version",
        "rule_set_version",
        "ingested_at",
    } <= cols


def test_versioned_config_tables_have_version_column() -> None:
    """mapping_config and rule_set are versioned (CC-4)."""
    for name in ("mapping_config", "rule_set"):
        assert "version" in Base.metadata.tables[name].columns


def test_create_all_and_insert_tenant_scoped_user() -> None:
    """A user can be created scoped to a tenant on a fresh in-memory DB."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        tenant = Tenant(name="Acme", slug="acme")
        session.add(tenant)
        session.flush()  # assigns tenant.id
        user = User(tenant_id=tenant.id, email="user@acme.example", display_name="Ada")
        session.add(user)
        session.commit()

        loaded = session.get(User, user.id)
        assert loaded is not None
        assert loaded.tenant_id == tenant.id
        assert loaded.role == "member"
