"""Universal clone / duplicate of reusable config entities (Phase 15).

Deep-copies an entity (and its children) into a new draft with fresh ids, a
``cloned_from`` provenance pointer, and (optionally) a different target tenant.
Never copies secrets/credentials (CC-10/CC-12), audit, sessions, or output rows.
Clones are tenant-scoped writes (CC-1); cross-tenant clone is an admin action.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.models import (
    ConnectorConfig,
    FeedTemplate,
    MappingConfig,
    Rule,
    RuleSet,
    Stack,
    StackRow,
)


def _copy_name(name: str, new_name: str | None) -> str:
    return new_name.strip() if new_name else f"{name} (copy)"


def clone_rule_set(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    rule_set_id: uuid.UUID,
    target_tenant_id: uuid.UUID | None = None,
    new_name: str | None = None,
    created_by: uuid.UUID | None = None,
) -> RuleSet | None:
    """Clone a rule set and all its rules into a new draft (default same tenant)."""
    source = session.scalar(
        tenant_scoped_select(RuleSet, tenant_id).where(RuleSet.id == rule_set_id)
    )
    if source is None:
        return None
    dest_tenant = target_tenant_id or tenant_id
    clone = RuleSet(
        tenant_id=dest_tenant,
        name=_copy_name(source.name, new_name),
        version=1,
        layer=source.layer,
        lifecycle_status="draft",
        created_by=created_by,
        cloned_from=source.id,
    )
    session.add(clone)
    session.flush()
    rules = session.scalars(select(Rule).where(Rule.rule_set_id == source.id)).all()
    for rule in rules:
        session.add(
            Rule(
                tenant_id=dest_tenant,
                rule_set_id=clone.id,
                target_field=rule.target_field,
                operation=rule.operation,
                params=dict(rule.params),
                condition=dict(rule.condition) if rule.condition else None,
                order_index=rule.order_index,
                layer=rule.layer,
            )
        )
    session.flush()
    return clone


def clone_mapping_config(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    mapping_config_id: uuid.UUID,
    target_tenant_id: uuid.UUID | None = None,
    new_name: str | None = None,
    created_by: uuid.UUID | None = None,
) -> MappingConfig | None:
    """Clone a mapping config. Same tenant → next version; cross-tenant → version 1."""
    source = session.scalar(
        tenant_scoped_select(MappingConfig, tenant_id).where(MappingConfig.id == mapping_config_id)
    )
    if source is None:
        return None
    dest_tenant = target_tenant_id or tenant_id
    # The unique key is (tenant, file_signature, version); a same-tenant clone must
    # bump the version, a cross-tenant clone starts at 1.
    if dest_tenant == tenant_id:
        latest = session.scalar(
            select(func.max(MappingConfig.version)).where(
                MappingConfig.tenant_id == dest_tenant,
                MappingConfig.file_signature == source.file_signature,
            )
        )
        version = (latest or 0) + 1
    else:
        version = 1
    clone = MappingConfig(
        tenant_id=dest_tenant,
        name=_copy_name(source.name, new_name),
        file_signature=source.file_signature,
        version=version,
        layer=source.layer,
        is_active=False,
        mapping=dict(source.mapping),
        lifecycle_status="draft",
        created_by=created_by,
        cloned_from=source.id,
    )
    session.add(clone)
    session.flush()
    return clone


def clone_feed_template(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    feed_template_id: uuid.UUID,
    target_tenant_id: uuid.UUID | None = None,
    new_name: str | None = None,
) -> FeedTemplate | None:
    """Clone a feed template into a new record."""
    source = session.scalar(
        tenant_scoped_select(FeedTemplate, tenant_id).where(FeedTemplate.id == feed_template_id)
    )
    if source is None:
        return None
    dest_tenant = target_tenant_id or tenant_id
    clone = FeedTemplate(
        tenant_id=dest_tenant,
        name=_copy_name(source.name, new_name),
        fmt=source.fmt,
        delimiter=source.delimiter,
        has_header=source.has_header,
        fixed_fields=[dict(f) for f in source.fixed_fields],
        expected_columns=list(source.expected_columns),
        filename_glob=source.filename_glob,
        cloned_from=source.id,
    )
    session.add(clone)
    session.flush()
    return clone


def clone_connector_config(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connector_config_id: uuid.UUID,
    target_tenant_id: uuid.UUID | None = None,
    new_name: str | None = None,
) -> ConnectorConfig | None:
    """Clone a connector config **without** its credential/secret (CC-10)."""
    source = session.scalar(
        tenant_scoped_select(ConnectorConfig, tenant_id).where(
            ConnectorConfig.id == connector_config_id
        )
    )
    if source is None:
        return None
    dest_tenant = target_tenant_id or tenant_id
    clone = ConnectorConfig(
        tenant_id=dest_tenant,
        connector_key=source.connector_key,
        name=_copy_name(source.name, new_name),
        account_ids=list(source.account_ids),
        settings=dict(source.settings),
        enabled=False,  # starts disabled: no credential attached yet
        cloned_from=source.id,
    )
    session.add(clone)
    session.flush()
    return clone


def clone_stack(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stack_id: uuid.UUID,
    new_name: str | None = None,
    created_by: uuid.UUID | None = None,
) -> Stack | None:
    """Clone a stack and its rows into a new draft."""
    source = session.scalar(tenant_scoped_select(Stack, tenant_id).where(Stack.id == stack_id))
    if source is None:
        return None
    clone = Stack(
        tenant_id=tenant_id,
        name=_copy_name(source.name, new_name),
        description=source.description,
        version=1,
        lifecycle_status="draft",
        grain=source.grain,
        reporting_currency=source.reporting_currency,
        reporting_timezone=source.reporting_timezone,
        schema_contract=dict(source.schema_contract),
        source_job_ids=list(source.source_job_ids),
        created_by=created_by,
        cloned_from=source.id,
    )
    session.add(clone)
    session.flush()
    rows = session.scalars(
        tenant_scoped_select(StackRow, tenant_id).where(StackRow.stack_id == source.id)
    ).all()
    for row in rows:
        session.add(
            StackRow(
                tenant_id=tenant_id,
                stack_id=clone.id,
                stack_version=clone.version,
                source_job_id=row.source_job_id,
                source_file_id=row.source_file_id,
                source_sheet=row.source_sheet,
                source_row=row.source_row,
                data=dict(row.data),
            )
        )
    session.flush()
    return clone


def clone_customer_configs(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    target_tenant_id: uuid.UUID,
    created_by: uuid.UUID | None = None,
) -> dict[str, int]:
    """Bulk-clone a customer's config setup into a target customer (admin action).

    Copies rule sets (+ rules), mapping configs, feed templates, and connector
    configs (**never** credentials/secrets, CC-10). Returns per-entity counts.
    """
    counts = {"rule_sets": 0, "mapping_configs": 0, "feed_templates": 0, "connector_configs": 0}
    for rs in session.scalars(tenant_scoped_select(RuleSet, tenant_id)).all():
        if clone_rule_set(
            session,
            tenant_id=tenant_id,
            rule_set_id=rs.id,
            target_tenant_id=target_tenant_id,
            new_name=rs.name,
            created_by=created_by,
        ):
            counts["rule_sets"] += 1
    for mc in session.scalars(tenant_scoped_select(MappingConfig, tenant_id)).all():
        if clone_mapping_config(
            session,
            tenant_id=tenant_id,
            mapping_config_id=mc.id,
            target_tenant_id=target_tenant_id,
            new_name=mc.name,
            created_by=created_by,
        ):
            counts["mapping_configs"] += 1
    for ft in session.scalars(tenant_scoped_select(FeedTemplate, tenant_id)).all():
        if clone_feed_template(
            session,
            tenant_id=tenant_id,
            feed_template_id=ft.id,
            target_tenant_id=target_tenant_id,
            new_name=ft.name,
        ):
            counts["feed_templates"] += 1
    for cc in session.scalars(tenant_scoped_select(ConnectorConfig, tenant_id)).all():
        if clone_connector_config(
            session,
            tenant_id=tenant_id,
            connector_config_id=cc.id,
            target_tenant_id=target_tenant_id,
            new_name=cc.name,
        ):
            counts["connector_configs"] += 1
    return counts
