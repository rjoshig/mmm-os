"""The common **landed dataset** representation (CC-9).

Every ingestion source — file uploads, SFTP drops, and (deferred) partner API
connectors — converges on this shape so the downstream mapping (Phase 2),
transform (Phase 3), validation (Phase 4), and output stages consume data
*without knowing or caring about the source* it came from.

For **file sources** a landed dataset carries the detected structure of each
sheet (header row + inferred columns), which is persisted as ``sheet`` /
``profile`` records. For **API sources** (deferred, Phase 9) the same shape
carries already-normalised rows in :attr:`LandedTable.records`, since partner
report schemas are known and stable (no header detection needed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Recognised source families (mirrors the documented ``source.type`` values).
SOURCE_TYPE_UPLOAD = "upload"
SOURCE_TYPE_SFTP = "sftp"
SOURCE_TYPE_API_CONNECTOR = "api_connector"


@dataclass
class LandedTable:
    """One tabular unit within a landed dataset (a sheet, or a partner report).

    Attributes:
        name: A human-readable name (sheet title, or report/entity name).
        index: A stable zero-based ordinal within the dataset.
        header_row_index: For file sources, the detected header row index within
            the raw preview (``None`` if unknown). ``None`` for API sources,
            whose columns are known up front.
        columns: The column structure as ``{index, name, type, date_format}``
            dicts — the same shape persisted to ``sheet.columns``.
        confident: Whether structure detection was confident (file sources).
            Always ``True`` for API sources with a known schema.
        records: Optional already-normalised rows (used by API sources). File
            sources leave this ``None`` and are profiled from raw bytes instead.
    """

    name: str
    index: int
    header_row_index: int | None = None
    columns: list[dict[str, Any]] = field(default_factory=list)
    confident: bool = False
    records: list[dict[str, Any]] | None = None


@dataclass
class LandedDataset:
    """A source-agnostic dataset produced by a :class:`~mmm_os.sources.base.SourceConnector`.

    Attributes:
        source_type: The source family (``"upload"`` / ``"sftp"`` /
            ``"api_connector"``).
        source_ref: Traceability metadata locating the origin (e.g.
            ``{"file_id": ...}`` for uploads, or ``{"connector_config_id": ...,
            "sync_run_id": ...}`` for API pulls). Carried through to output rows
            so every result traces back to its source (CC-3).
        tables: One :class:`LandedTable` per tabular unit (non-empty only).
    """

    source_type: str
    source_ref: dict[str, Any]
    tables: list[LandedTable] = field(default_factory=list)
