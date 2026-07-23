#!/usr/bin/env python3
"""Generate the mmm-os sample marketing-data set.

Produces a spread of **realistic, deliberately messy** marketing files — the kind
of exports mmm-os is built to ingest: partner-specific column names, taxonomy
aliases (``FB`` / ``fb_ads`` → ``Facebook``), mixed date formats, currency symbols,
multi-tab workbooks, and a few blanks/outliers. They are meant to exercise
structure detection (Phase 1), column mapping (Phase 2), transformation rules
(Phase 3), and validation/anomaly detection (Phase 4).

Deterministic: a fixed RNG seed means re-running reproduces byte-stable data, so
the committed files never churn. Run from the repo root or this directory::

    uv run python sampledata/generate_sample_data.py

Only stdlib + ``openpyxl`` (already a backend dependency) are used.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook

SEED = 20240101
OUT_DIR = Path(__file__).resolve().parent

# --- Shared vocabularies (raw, partner-flavoured — NOT yet canonical) ----------

GEOS = ["United States", "United Kingdom", "Australia", "Canada", "Germany"]
CURRENCY_BY_GEO = {
    "United States": "USD",
    "United Kingdom": "GBP",
    "Australia": "AUD",
    "Canada": "CAD",
    "Germany": "EUR",
}
FUNNELS = ["awareness", "consideration", "conversion", "retention"]

CAMPAIGN_THEMES = [
    "Always_On_Prospecting",
    "Q1_Brand_Awareness",
    "Spring_Sale",
    "BlackFriday_2024",
    "Retargeting_Cart",
    "New_Product_Launch",
    "Holiday_Gifting",
    "Summer_Clearance",
    "Loyalty_Winback",
    "Back_To_School",
]


def rng() -> random.Random:
    """A fresh, seeded RNG so each file is independently reproducible."""
    return random.Random(SEED)


def daterange(start: date, days: int, step: int = 1) -> list[date]:
    """A list of dates from ``start`` for ``days`` entries, ``step`` days apart."""
    return [start + timedelta(days=i * step) for i in range(days)]


def money(r: random.Random, low: float, high: float) -> float:
    """A spend-like amount rounded to cents."""
    return round(r.uniform(low, high), 2)


def write_csv(name: str, header: list[str], rows: list[list[object]]) -> None:
    """Write a CSV file into the sample-data directory."""
    path = OUT_DIR / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"  wrote {name}  ({len(rows)} rows)")


def write_xlsx(name: str, sheets: dict[str, tuple[list[str], list[list[object]]]]) -> None:
    """Write a (possibly multi-tab) XLSX workbook into the sample-data directory."""
    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, (header, rows) in sheets.items():
        ws = wb.create_sheet(title=sheet_name)
        ws.append(header)
        for row in rows:
            ws.append(row)
    wb.save(OUT_DIR / name)
    total = sum(len(rows) for _, rows in sheets.values())
    print(f"  wrote {name}  ({len(sheets)} tab(s), {total} rows)")


# --- Per-source builders -------------------------------------------------------


def facebook_ads() -> None:
    """Meta Ads Manager–style export (nested-ish naming, purchase value)."""
    r = rng()
    header = [
        "Reporting starts",
        "Campaign name",
        "Ad set name",
        "Amount spent (USD)",
        "Impressions",
        "Link clicks",
        "Purchases",
        "Purchase conversion value",
    ]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 1), 160):
        theme = r.choice(CAMPAIGN_THEMES)
        spend = money(r, 40, 900)
        impr = r.randint(2000, 90000)
        clicks = int(impr * r.uniform(0.004, 0.03))
        purch = int(clicks * r.uniform(0.01, 0.08))
        rows.append(
            [
                d.strftime("%Y-%m-%d"),
                f"FB | {theme}",
                f"{theme}__{r.choice(['broad', 'lookalike', 'interest'])}",
                spend,
                impr,
                clicks,
                purch,
                round(purch * r.uniform(35, 120), 2),
            ]
        )
    write_csv("facebook_ads_2024.csv", header, rows)


def google_ads() -> None:
    """Google Ads UI–style export ('Cost', 'Impr.', 'Conv. value')."""
    r = rng()
    header = [
        "Day",
        "Campaign",
        "Ad group",
        "Currency code",
        "Cost",
        "Impr.",
        "Clicks",
        "Conversions",
        "Conv. value",
    ]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 1), 180):
        theme = r.choice(CAMPAIGN_THEMES)
        clicks = r.randint(50, 1500)
        impr = int(clicks / r.uniform(0.02, 0.09))
        conv = round(clicks * r.uniform(0.02, 0.12), 1)
        rows.append(
            [
                d.strftime("%Y-%m-%d"),
                f"Search_{theme}",
                r.choice(["Brand", "Generic", "Competitor", "DSA"]),
                "USD",
                money(r, 30, 1200),
                impr,
                clicks,
                conv,
                round(conv * r.uniform(40, 150), 2),
            ]
        )
    write_csv("google_ads_2024.csv", header, rows)


def tiktok_ads() -> None:
    """TikTok Ads Manager–style export (string-ish metrics, reach)."""
    r = rng()
    header = [
        "stat_time_day",
        "Campaign name",
        "Country",
        "Spend",
        "Impressions",
        "Clicks",
        "Reach",
        "Conversions",
    ]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 2, 1), 140):
        theme = r.choice(CAMPAIGN_THEMES)
        impr = r.randint(5000, 200000)
        rows.append(
            [
                d.strftime("%Y-%m-%d"),
                f"TT_{theme}",
                r.choice(["US", "GB", "AU", "CA", "DE"]),
                money(r, 25, 700),
                impr,
                int(impr * r.uniform(0.005, 0.02)),
                int(impr * r.uniform(0.6, 0.85)),
                r.randint(0, 60),
            ]
        )
    write_csv("tiktok_ads.csv", header, rows)


def youtube_video() -> None:
    """YouTube/Google video export (views + view rate)."""
    r = rng()
    header = [
        "date",
        "channel",
        "campaign",
        "geo",
        "cost",
        "impressions",
        "views",
        "clicks",
    ]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 15), 150):
        geo = r.choice(GEOS)
        impr = r.randint(8000, 250000)
        rows.append(
            [
                d.strftime("%Y-%m-%d"),
                "YouTube",
                f"YT_{r.choice(CAMPAIGN_THEMES)}",
                geo,
                money(r, 50, 800),
                impr,
                int(impr * r.uniform(0.15, 0.4)),
                int(impr * r.uniform(0.001, 0.01)),
            ]
        )
    write_csv("youtube_video.csv", header, rows)


def programmatic_dv360() -> None:
    """DV360-style export (Insertion Order / Line Item / Media Cost)."""
    r = rng()
    header = [
        "Date",
        "Insertion Order",
        "Line Item",
        "Media Cost (Advertiser Currency)",
        "Impressions",
        "Clicks",
        "Total Conversions",
    ]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 3, 1), 120):
        io = f"IO_{r.choice(CAMPAIGN_THEMES)}"
        impr = r.randint(10000, 400000)
        rows.append(
            [
                d.strftime("%m/%d/%Y"),  # US-format dates on purpose
                io,
                f"{io}__LI_{r.randint(1, 6)}",
                money(r, 60, 1500),
                impr,
                int(impr * r.uniform(0.0006, 0.004)),
                r.randint(0, 40),
            ]
        )
    write_csv("programmatic_dv360.csv", header, rows)


def tv_spots() -> None:
    """Offline TV buys — weekly, GRPs, no clicks (messy header casing)."""
    r = rng()
    header = ["Week Commencing", "Station", "Daypart", "Market", "Spend (GBP)", "GRPs", "Reach %"]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 1), 120, step=7):
        rows.append(
            [
                d.strftime("%d/%m/%Y"),  # UK-format dates
                r.choice(["ITV", "Channel 4", "Sky", "BBC", "Channel 5"]),
                r.choice(["Breakfast", "Daytime", "Peak", "Late Peak", "Night"]),
                r.choice(["London", "Midlands", "North", "Scotland", "National"]),
                money(r, 2000, 45000),
                round(r.uniform(20, 400), 1),
                round(r.uniform(5, 65), 1),
            ]
        )
    write_csv("tv_spots.csv", header, rows)


def radio_buys() -> None:
    """Offline radio buys — weekly spend + reach."""
    r = rng()
    header = ["week", "station", "region", "currency", "spend", "spots", "reach"]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 7), 110, step=7):
        geo = r.choice(GEOS)
        rows.append(
            [
                d.strftime("%Y-%m-%d"),
                r.choice(["KISS", "Heart", "Capital", "Classic FM", "LBC"]),
                geo,
                CURRENCY_BY_GEO[geo],
                money(r, 500, 12000),
                r.randint(10, 120),
                r.randint(20000, 800000),
            ]
        )
    write_csv("radio_buys.csv", header, rows)


def ooh_billboards() -> None:
    """Out-of-home placements — no clicks, impressions estimated."""
    r = rng()
    header = ["Date", "Format", "City", "Spend", "Estimated Impressions"]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 1), 100, step=7):
        rows.append(
            [
                d.strftime("%Y-%m-%d"),
                r.choice(["Billboard", "Bus Shelter", "Digital Screen", "Transit", "Mall"]),
                r.choice(["New York", "London", "Sydney", "Toronto", "Berlin"]),
                money(r, 1500, 30000),
                r.randint(50000, 2000000),
            ]
        )
    write_csv("ooh_billboards.csv", header, rows)


def email_campaigns() -> None:
    """Owned email — sends/opens/clicks/revenue."""
    r = rng()
    header = ["Send Date", "Campaign", "Segment", "Sends", "Opens", "Clicks", "Revenue"]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 1), 130):
        sends = r.randint(5000, 200000)
        opens = int(sends * r.uniform(0.1, 0.45))
        clicks = int(opens * r.uniform(0.02, 0.2))
        rows.append(
            [
                d.strftime("%Y-%m-%d"),
                f"Email_{r.choice(CAMPAIGN_THEMES)}",
                r.choice(["All", "Lapsed", "VIP", "New", "Prospects"]),
                sends,
                opens,
                clicks,
                round(clicks * r.uniform(1.5, 12), 2),
            ]
        )
    write_csv("email_campaigns.csv", header, rows)


def affiliate_partners() -> None:
    """Affiliate network export — commission + orders."""
    r = rng()
    header = ["date", "partner", "channel", "clicks", "orders", "sale_amount", "commission"]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 1), 140):
        clicks = r.randint(100, 8000)
        orders = int(clicks * r.uniform(0.005, 0.05))
        sale = round(orders * r.uniform(30, 140), 2)
        rows.append(
            [
                d.strftime("%Y-%m-%d"),
                r.choice(["TopCashback", "Honey", "RetailMeNot", "Skimlinks", "Awin"]),
                "affiliate",
                clicks,
                orders,
                sale,
                round(sale * r.uniform(0.03, 0.12), 2),
            ]
        )
    write_csv("affiliate_partners.csv", header, rows)


def retail_sales_offline() -> None:
    """First-party offline retail sales — units + revenue per store/region."""
    r = rng()
    header = ["Date", "Store", "Region", "Units Sold", "Gross Revenue", "Currency"]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 1), 120):
        for _ in range(r.randint(1, 2)):
            geo = r.choice(GEOS)
            units = r.randint(20, 900)
            rows.append(
                [
                    d.strftime("%Y-%m-%d"),
                    f"Store_{r.randint(100, 140)}",
                    geo,
                    units,
                    round(units * r.uniform(18, 60), 2),
                    CURRENCY_BY_GEO[geo],
                ]
            )
    write_csv("retail_sales_offline.csv", header, rows[:190])


def messy_mixed_export() -> None:
    """Deliberately messy blended export.

    Exercises the harder path: channel **aliases** (``FB`` / ``fb_ads`` /
    ``adwords``), mixed date formats, currency **symbols** inside spend, a few
    blank cells, and the occasional negative/outlier value for anomaly detection.
    """
    r = rng()
    header = ["dt", "media_channel", "campaign", "market", "spend", "impressions", "clicks", "conv"]
    channel_aliases = ["FB", "fb_ads", "facebook ads", "google", "adwords", "tik tok", "yt", "IG"]
    date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y"]
    symbols = ["$", "£", "€", ""]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 1), 175):
        impr = r.randint(1000, 120000)
        clicks = int(impr * r.uniform(0.003, 0.03))
        spend_val = money(r, 20, 800)
        # ~4% blank spend, ~2% negative outlier (data-quality flags in Phase 4).
        if r.random() < 0.04:
            spend_cell: object = ""
        elif r.random() < 0.02:
            spend_cell = f"{r.choice(symbols)}-{spend_val}"
        else:
            spend_cell = f"{r.choice(symbols)}{spend_val}"
        rows.append(
            [
                d.strftime(r.choice(date_formats)),
                r.choice(channel_aliases),
                r.choice(CAMPAIGN_THEMES),
                r.choice(["US", "UK", "AU", "", "CA"]),
                spend_cell,
                impr,
                clicks,
                r.randint(0, 50) if r.random() > 0.05 else "",
            ]
        )
    write_csv("messy_mixed_export.csv", header, rows)


def multi_channel_workbook() -> None:
    """A multi-tab workbook: one tab per paid-social channel (structure detection)."""
    r = rng()

    def social_tab(prefix: str, geo_codes: list[str]) -> tuple[list[str], list[list[object]]]:
        header = ["Date", "Campaign", "Country", "Spend", "Impressions", "Clicks", "Conversions"]
        rows: list[list[object]] = []
        for d in daterange(date(2024, 1, 1), r.randint(110, 160)):
            impr = r.randint(3000, 150000)
            rows.append(
                [
                    d.strftime("%Y-%m-%d"),
                    f"{prefix}_{r.choice(CAMPAIGN_THEMES)}",
                    r.choice(geo_codes),
                    money(r, 30, 750),
                    impr,
                    int(impr * r.uniform(0.004, 0.02)),
                    r.randint(0, 70),
                ]
            )
        return header, rows

    write_xlsx(
        "multi_channel_workbook.xlsx",
        {
            "Facebook": social_tab("FB", ["US", "GB", "AU"]),
            "Google": social_tab("GA", ["US", "CA", "DE"]),
            "TikTok": social_tab("TT", ["US", "GB", "AU", "DE"]),
        },
    )


def paid_search_weekly() -> None:
    """Weekly-granularity paid-search workbook (single tab)."""
    r = rng()
    header = [
        "Week",
        "Engine",
        "Campaign",
        "Cost",
        "Impressions",
        "Clicks",
        "Conversions",
        "Revenue",
    ]
    rows: list[list[object]] = []
    for d in daterange(date(2024, 1, 1), 100, step=7):
        clicks = r.randint(500, 12000)
        conv = int(clicks * r.uniform(0.02, 0.1))
        rows.append(
            [
                d.strftime("%Y-%m-%d"),
                r.choice(["Google", "Bing", "Google", "Google"]),
                f"PS_{r.choice(CAMPAIGN_THEMES)}",
                money(r, 200, 6000),
                int(clicks / r.uniform(0.02, 0.08)),
                clicks,
                conv,
                round(conv * r.uniform(45, 160), 2),
            ]
        )
    write_xlsx("paid_search_weekly.xlsx", {"Weekly": (header, rows)})


def meta_multi_account() -> None:
    """A multi-tab workbook: one tab per ad account (same schema, needs stacking)."""
    r = rng()

    def account_tab(_acct: str) -> tuple[list[str], list[list[object]]]:
        header = [
            "Reporting starts",
            "Campaign name",
            "Amount spent",
            "Impressions",
            "Link clicks",
            "Purchases",
        ]
        rows: list[list[object]] = []
        for d in daterange(date(2024, 1, 1), r.randint(100, 150)):
            impr = r.randint(2000, 100000)
            clicks = int(impr * r.uniform(0.004, 0.03))
            rows.append(
                [
                    d.strftime("%Y-%m-%d"),
                    f"FB | {r.choice(CAMPAIGN_THEMES)}",
                    money(r, 30, 800),
                    impr,
                    clicks,
                    int(clicks * r.uniform(0.01, 0.07)),
                ]
            )
        return header, rows

    write_xlsx(
        "meta_multi_account.xlsx",
        {
            "act_1001_US": account_tab("US"),
            "act_1002_UK": account_tab("UK"),
            "act_1003_AU": account_tab("AU"),
        },
    )


BUILDERS = [
    facebook_ads,
    google_ads,
    tiktok_ads,
    youtube_video,
    programmatic_dv360,
    tv_spots,
    radio_buys,
    ooh_billboards,
    email_campaigns,
    affiliate_partners,
    retail_sales_offline,
    messy_mixed_export,
    multi_channel_workbook,
    paid_search_weekly,
    meta_multi_account,
]


def main() -> None:
    """Generate the full sample-data set into this directory."""
    print(f"Generating sample data into {OUT_DIR} …")
    for build in BUILDERS:
        build()
    print(f"Done — {len(BUILDERS)} files.")


if __name__ == "__main__":
    main()
