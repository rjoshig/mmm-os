"""The source-agnostic ingestion contract (CC-9).

A :class:`SourceConnector` is the single seam every inbound source implements —
uploads today (:class:`~mmm_os.sources.file_source.FileSource`), SFTP and partner
API connectors later (Phase 9). Each connector turns its source into a common
:class:`~mmm_os.sources.landed.LandedDataset`; nothing downstream depends on
*which* connector produced it.

Only the file source is implemented now. The API-oriented methods
(:meth:`SourceConnector.test_connection`, :meth:`SourceConnector.list_available`)
are part of the contract so partner connectors attach without reshaping it; the
file source gives them trivial implementations.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import date
from typing import Any

from mmm_os.sources.landed import LandedDataset


@dataclass
class FetchRequest:
    """A request for a connector to produce a landed dataset.

    The fields honestly cover both source families: file sources use ``ref`` to
    locate stored bytes; API sources (deferred) use ``config`` plus an optional
    ``date_range`` to scope a partner report pull.

    Attributes:
        ref: Source-specific locator (e.g. ``{"file_id": ...}`` for uploads).
        config: Connector configuration (account IDs, metrics/dimensions, …) —
            unused by the file source.
        date_range: Optional ``(start, end)`` window for API pulls.
        options: Free-form tuning (preview row counts, etc.).
    """

    ref: dict[str, Any]
    config: dict[str, Any] | None = None
    date_range: tuple[date, date] | None = None
    options: dict[str, Any] | None = None


class SourceConnector(abc.ABC):
    """Abstract contract every ingestion source implements.

    Implementations MUST be side-effect free with respect to the immutable raw
    layer (CC-2): they read source bytes/APIs and emit a landed dataset, but do
    not mutate originals.
    """

    #: The source family this connector produces (see ``landed.SOURCE_TYPE_*``).
    source_type: str

    @abc.abstractmethod
    def fetch(self, request: FetchRequest) -> LandedDataset:
        """Produce the common landed dataset for ``request``.

        Args:
            request: What to fetch (a stored file, or a partner report window).

        Returns:
            A :class:`LandedDataset` tagged with this connector's ``source_type``
            and a ``source_ref`` for traceability (CC-3).
        """

    def test_connection(self) -> bool:
        """Return whether the source is reachable/authorised.

        Trivially ``True`` for file sources (no live connection). Partner API
        connectors (Phase 9) override this to probe credentials.
        """
        return True

    def list_available(self) -> list[dict[str, Any]]:
        """List selectable entities (accounts / metrics / reports).

        Empty for file sources. Partner API connectors (Phase 9) override this
        to enumerate a customer's authorised ad accounts and reportable fields.
        """
        return []
