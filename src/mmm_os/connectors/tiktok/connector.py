"""TikTok connector + a fake report client (Phase 09.5).

TikTok returns each row as separate ``dimensions`` / ``metrics`` objects with
string metrics; they must be flattened (``flatten_report_row``) before mapping.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from mmm_os.connectors.base import PartnerConnector


class TikTokConnector(PartnerConnector):
    """TikTok report → canonical; flattens the split dimensions/metrics objects."""

    connector_key = "tiktok"

    def preprocess(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Flatten ``{dimensions:{…}, metrics:{…}}`` into one namespaced dict."""
        flat: list[dict[str, Any]] = []
        for row in rows:
            merged: dict[str, Any] = {}
            for key, value in (row.get("dimensions") or {}).items():
                merged[f"dimensions.{key}"] = value
            for key, value in (row.get("metrics") or {}).items():
                merged[f"metrics.{key}"] = value
            flat.append(merged)
        return flat


class FakeTikTokReportClient:
    """A fixture report client with the split dimensions/metrics shape."""

    def fetch_report(
        self, *, config: dict[str, Any], start: date, end: date
    ) -> list[dict[str, Any]]:
        """Return one fixture row in TikTok's split response shape."""
        return [
            {
                "dimensions": {
                    "campaign_id": "c-1",
                    "stat_time_day": "2026-01-01",
                    "country_code": "US",
                },
                "metrics": {
                    "campaign_name": "TikTok Launch",
                    "spend": "80.25",
                    "impressions": "20000",
                    "clicks": "600",
                    "reach": "15000",
                    "conversion": "18",
                },
            }
        ]
