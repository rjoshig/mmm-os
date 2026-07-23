"""SQLAlchemy ORM models — the tenant-scoped, versioned data model [Phase 0].

Importing this package registers every model on ``Base.metadata`` so Alembic
autogenerate and ``create_all`` see the full schema.
"""

from mmm_os.models.ai_usage import LlmBudget, LlmUsage
from mmm_os.models.auth import IdentityProviderConfig, SecretRef, Session
from mmm_os.models.config import (
    MappingConfig,
    Rule,
    RuleSet,
    Taxonomy,
    TaxonomyAlias,
)
from mmm_os.models.connectors import ConnectorConfig, ConnectorCredential, SyncRun
from mmm_os.models.file import File, Profile, Sheet
from mmm_os.models.governance import AuditLog
from mmm_os.models.job import Job, JobEvent, Suggestion, ValidationFlag
from mmm_os.models.output import OutputRow
from mmm_os.models.tenant import Tenant, TenantSettings, User

__all__ = [
    "AuditLog",
    "ConnectorConfig",
    "ConnectorCredential",
    "File",
    "IdentityProviderConfig",
    "Job",
    "JobEvent",
    "LlmBudget",
    "LlmUsage",
    "MappingConfig",
    "OutputRow",
    "Profile",
    "Rule",
    "RuleSet",
    "SecretRef",
    "Session",
    "Sheet",
    "Suggestion",
    "SyncRun",
    "Taxonomy",
    "TaxonomyAlias",
    "Tenant",
    "TenantSettings",
    "User",
    "ValidationFlag",
]
