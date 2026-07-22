"""SQLAlchemy ORM models — the tenant-scoped, versioned data model [Phase 0].

Importing this package registers every model on ``Base.metadata`` so Alembic
autogenerate and ``create_all`` see the full schema.
"""

from mmm_os.models.config import (
    MappingConfig,
    Rule,
    RuleSet,
    Taxonomy,
    TaxonomyAlias,
)
from mmm_os.models.file import File, Profile, Sheet
from mmm_os.models.job import Job, JobEvent, Suggestion, ValidationFlag
from mmm_os.models.output import OutputRow
from mmm_os.models.tenant import Tenant, User

__all__ = [
    "File",
    "Job",
    "JobEvent",
    "MappingConfig",
    "OutputRow",
    "Profile",
    "Rule",
    "RuleSet",
    "Sheet",
    "Suggestion",
    "Taxonomy",
    "TaxonomyAlias",
    "Tenant",
    "User",
    "ValidationFlag",
]
