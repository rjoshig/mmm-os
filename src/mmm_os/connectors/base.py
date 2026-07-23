"""Partner connector base + report-client seam (Phase 9, CC-9).

A ``PartnerConnector`` is a :class:`~mmm_os.sources.base.SourceConnector` whose
``fetch`` calls a partner reporting API (behind the ``ReportClient`` seam), applies
partner-specific pre-processing, and normalizes the response into the common
:class:`~mmm_os.sources.landed.LandedDataset`. Live API calls live in a concrete
``ReportClient`` enabled with real credentials; tests inject a fake client, so the
framework + normalization are fully exercised without network access.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol, runtime_checkable

from mmm_os.connectors.normalize import normalize_rows
from mmm_os.resilience import retry
from mmm_os.sources.base import FetchRequest, SourceConnector
from mmm_os.sources.landed import SOURCE_TYPE_API_CONNECTOR, LandedDataset


@runtime_checkable
class ReportClient(Protocol):
    """A partner reporting-API client: pull raw report rows for a date window."""

    def fetch_report(
        self, *, config: dict[str, Any], start: date, end: date
    ) -> list[dict[str, Any]]:
        """Return raw report rows for ``config`` over ``[start, end]``."""
        ...


class PartnerConnector(SourceConnector):
    """Base for API-based partner connectors (Meta/Google/DV360/TikTok)."""

    connector_key: str = ""

    def __init__(self, client: ReportClient, *, account_ctx: dict[str, Any] | None = None) -> None:
        """Bind the connector to a report client + optional normalization context."""
        self.client = client
        self.account_ctx = account_ctx or {}
        self.source_type = SOURCE_TYPE_API_CONNECTOR

    def preprocess(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Partner-specific row shaping before normalization (override as needed)."""
        return rows

    def fetch(self, request: FetchRequest) -> LandedDataset:
        """Pull + normalize a report window into a ``LandedDataset``.

        The window comes from ``request.date_range``; retries wrap transient
        report-API failures (Phase 07.2).
        """
        config = request.config or {}
        if request.date_range is None:
            raise ValueError("a date_range is required for a partner connector fetch")
        start, end = request.date_range
        raw = retry(
            lambda: self.client.fetch_report(config=config, start=start, end=end), retries=2
        )
        rows = self.preprocess(raw)
        return normalize_rows(
            self.connector_key, rows, account_ctx=self.account_ctx, source_ref=request.ref
        )

    def test_connection(self) -> bool:
        """A real connector probes credentials; the base assumes reachable."""
        return True
