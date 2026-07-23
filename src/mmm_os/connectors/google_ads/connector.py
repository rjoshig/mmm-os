"""Google Ads connector + a fake report client (Phase 09.5)."""

from __future__ import annotations

from datetime import date
from typing import Any

from mmm_os.connectors.base import PartnerConnector


class GoogleAdsConnector(PartnerConnector):
    """GAQL rows → canonical (cost in micros; geo-target id resolved via account_ctx)."""

    connector_key = "google_ads"


class FakeGoogleAdsReportClient:
    """A fixture report client (cost_micros; country as a geo-target id)."""

    def fetch_report(
        self, *, config: dict[str, Any], start: date, end: date
    ) -> list[dict[str, Any]]:
        """Return one fixture row of aggregate Google Ads performance."""
        return [
            {
                "segments.date": "2026-01-01",
                "campaign.name": "Search Brand",
                "campaign.advertising_channel_type": "SEARCH",
                "geographic_view.country_criterion_id": "2840",
                "metrics.cost_micros": "125000000",
                "metrics.impressions": "8000",
                "metrics.clicks": "410",
                "metrics.conversions": "22",
                "metrics.conversions_value": "1800",
                "customer.currency_code": "USD",
            }
        ]
