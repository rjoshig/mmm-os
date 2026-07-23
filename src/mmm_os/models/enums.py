"""Domain enumerations.

Per CODING_STANDARDS.md, enums are **stored as strings** and validated in the app
layer — never as native DB enums. These classes provide the canonical string
values used as column defaults and (later) for validation.
"""

from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    """Lifecycle status of a processing job."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SheetStatus(str, Enum):
    """Status of a sheet within a file."""

    DETECTED = "detected"
    SKIPPED_EMPTY = "skipped_empty"
    PARSED = "parsed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class ColumnType(str, Enum):
    """Inferred column data type (structure detection)."""

    STRING = "string"
    NUMBER = "number"
    CURRENCY = "currency"
    DATE = "date"
    BOOLEAN = "boolean"


class RuleLayer(str, Enum):
    """Layer at which a config (mapping/rule) applies (CC-4 layered resolution)."""

    GLOBAL = "global"
    TEMPLATE = "template"
    CUSTOMER = "customer"


class Severity(str, Enum):
    """Severity of a validation flag."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class ReviewStatus(str, Enum):
    """Human review status of a validation flag."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    OVERRIDDEN = "overridden"


class SuggestionKind(str, Enum):
    """Type of AI suggestion (Phase 5)."""

    MAPPING = "mapping"
    TAXONOMY = "taxonomy"
    STRUCTURE = "structure"
    ANOMALY_EXPLANATION = "anomaly_explanation"
    TRANSFORM_RULE = "transform_rule"


class SuggestionState(str, Enum):
    """Human-in-the-loop state of an AI suggestion (CC-5)."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
