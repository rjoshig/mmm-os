"""Meta (Facebook/Instagram) connector + a fake report client (Phase 09.4)."""

from __future__ import annotations

from datetime import date
from typing import Any

from mmm_os.connectors.base import PartnerConnector


class MetaConnector(PartnerConnector):
    """Meta Insights → canonical via ``meta/templates/default_mapping.yaml``."""

    connector_key = "meta"


class FakeMetaReportClient:
    """A fixture report client (nested actions/action_values, string metrics)."""

    def fetch_report(
        self, *, config: dict[str, Any], start: date, end: date
    ) -> list[dict[str, Any]]:
        """Return one fixture row of aggregate Meta performance."""
        return [
            {
                "date_start": "2026-01-01",
                "publisher_platform": "facebook",
                "campaign_name": "Spring Sale",
                "adset_name": "Prospecting",
                "country": "US",
                "objective": "OUTCOME_SALES",
                "spend": "100.50",
                "impressions": "12000",
                "inline_link_clicks": "340",
                "reach": "9000",
                "actions": [{"action_type": "purchase", "value": "7"}],
                "action_values": [{"action_type": "purchase", "value": "350.0"}],
                "account_currency": "USD",
            }
        ]
