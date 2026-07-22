"""Source-agnostic ingestion abstraction (CC-9).

Every inbound source produces a common :class:`~mmm_os.sources.landed.LandedDataset`
via the :class:`~mmm_os.sources.base.SourceConnector` contract, so all downstream
phases consume data without knowing its origin. :class:`~mmm_os.sources.file_source.FileSource`
is the first (and currently only) implementation; partner API connectors are
designed in :doc:`Phase 9 </phases/phase-09-future-connectors-extraction>` and
plug into this same seam. See ADR-010 in ``docs/architecture.md``.
"""

from __future__ import annotations

from mmm_os.sources.base import FetchRequest, SourceConnector
from mmm_os.sources.file_source import FileSource
from mmm_os.sources.landed import (
    SOURCE_TYPE_API_CONNECTOR,
    SOURCE_TYPE_SFTP,
    SOURCE_TYPE_UPLOAD,
    LandedDataset,
    LandedTable,
)

__all__ = [
    "SOURCE_TYPE_API_CONNECTOR",
    "SOURCE_TYPE_SFTP",
    "SOURCE_TYPE_UPLOAD",
    "FetchRequest",
    "FileSource",
    "LandedDataset",
    "LandedTable",
    "SourceConnector",
]
