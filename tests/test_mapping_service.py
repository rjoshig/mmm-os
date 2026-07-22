"""Service-level tests for layered mapping resolution (02.2)."""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mmm_os.mapping.service import resolve_mapping, save_sheet_mapping
from mmm_os.mapping.signature import column_signature
from mmm_os.models import File, Sheet, Tenant


def _make_sheet(session: Session) -> tuple[Tenant, Sheet]:
    tenant = Tenant(name="Acme", slug="acme")
    session.add(tenant)
    session.flush()
    file = File(tenant_id=tenant.id, filename="x.csv")
    session.add(file)
    session.flush()
    sheet = Sheet(
        tenant_id=tenant.id,
        file_id=file.id,
        sheet_name="s",
        sheet_index=0,
        header_row_index=0,
        columns=[{"name": "date"}, {"name": "channel"}, {"name": "spend"}],
    )
    session.add(sheet)
    session.flush()
    return tenant, sheet


def test_layers_merge(engine: Engine) -> None:
    """global + template + customer configs merge into one mapping."""
    with Session(engine) as session:
        tenant, sheet = _make_sheet(session)
        save_sheet_mapping(
            session,
            tenant_id=tenant.id,
            sheet=sheet,
            name="g",
            mapping={"date": "date"},
            layer="global",
        )
        save_sheet_mapping(
            session,
            tenant_id=tenant.id,
            sheet=sheet,
            name="t",
            mapping={"channel": "channel"},
            layer="template",
        )
        save_sheet_mapping(
            session,
            tenant_id=tenant.id,
            sheet=sheet,
            name="c",
            mapping={"spend": "spend"},
            layer="customer",
        )
        merged = resolve_mapping(session, tenant.id, column_signature(sheet.columns))
        assert merged == {"date": "date", "channel": "channel", "spend": "spend"}


def test_customer_overrides_global(engine: Engine) -> None:
    """For the same key, the customer layer wins over global."""
    with Session(engine) as session:
        tenant, sheet = _make_sheet(session)
        save_sheet_mapping(
            session,
            tenant_id=tenant.id,
            sheet=sheet,
            name="g",
            mapping={"spend": "impressions"},
            layer="global",
        )
        save_sheet_mapping(
            session,
            tenant_id=tenant.id,
            sheet=sheet,
            name="c",
            mapping={"spend": "spend"},
            layer="customer",
        )
        merged = resolve_mapping(session, tenant.id, column_signature(sheet.columns))
        assert merged["spend"] == "spend"
