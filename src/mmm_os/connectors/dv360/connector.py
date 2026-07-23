"""DV360 connector + a fake report client (Phase 09.5).

DV360 Bid Manager reports arrive as a CSV whose trailing grand-total / summary
rows must be stripped before mapping (``strip_report_totals``).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from mmm_os.connectors.base import PartnerConnector


class Dv360Connector(PartnerConnector):
    """DV360 offline report → canonical; strips trailing total rows first."""

    connector_key = "dv360"

    def preprocess(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Drop grand-total / summary rows (no per-row date)."""
        return [r for r in rows if r.get("FILTER_DATE") and r.get("FILTER_MEDIA_PLAN")]


class FakeDv360ReportClient:
    """A fixture report client including a trailing grand-total row."""

    def fetch_report(
        self, *, config: dict[str, Any], start: date, end: date
    ) -> list[dict[str, Any]]:
        """Return two data rows + one grand-total row (to be stripped)."""
        return [
            {
                "FILTER_DATE": "2026-01-01",
                "FILTER_MEDIA_PLAN": "Awareness Q1",
                "FILTER_INSERTION_ORDER": "IO-1",
                "FILTER_COUNTRY": "US",
                "METRIC_IMPRESSIONS": "50000",
                "METRIC_CLICKS": "300",
                "METRIC_REVENUE_ADVERTISER": "900.0",
                "METRIC_TOTAL_CONVERSIONS": "12",
            },
            {
                "FILTER_DATE": "Grand Total",
                "FILTER_MEDIA_PLAN": None,
                "METRIC_IMPRESSIONS": "50000",
            },
        ]
