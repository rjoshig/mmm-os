# Sample marketing data

A spread of **realistic, deliberately messy** marketing files for exercising the
mmm-os pipeline end to end: structure detection (Phase 1), column mapping to the
[canonical schema](../docs/canonical-schema.md) (Phase 2), transformation rules
(Phase 3), and validation/anomaly detection (Phase 4).

They mimic real partner exports — partner-specific column names, taxonomy
**aliases** (`FB` / `fb_ads` → `Facebook`), mixed date formats, currency symbols,
multi-tab workbooks, and a few blanks/outliers — so the mapping and validation
steps have something real to do. **None of it is real customer data**; it is
generated locally with a fixed seed.

## Files

| File | Format | Tabs | Rows | What it exercises |
|---|---|---|---|---|
| `facebook_ads_2024.csv` | CSV | 1 | 160 | Meta-style headers (`Amount spent (USD)`, `Link clicks`), purchase value. |
| `google_ads_2024.csv` | CSV | 1 | 180 | Google Ads headers (`Cost`, `Impr.`, `Conv. value`), explicit currency column. |
| `tiktok_ads.csv` | CSV | 1 | 140 | TikTok headers (`stat_time_day`), reach, country codes. |
| `youtube_video.csv` | CSV | 1 | 150 | Video metrics (views vs impressions), already-canonical `channel`. |
| `programmatic_dv360.csv` | CSV | 1 | 120 | DV360 IO/Line-Item naming, **US `MM/DD/YYYY` dates**. |
| `tv_spots.csv` | CSV | 1 | 120 | Offline TV, **weekly**, GRPs, no clicks, **UK `DD/MM/YYYY` dates**. |
| `radio_buys.csv` | CSV | 1 | 110 | Offline radio, weekly, per-region currency. |
| `ooh_billboards.csv` | CSV | 1 | 100 | Out-of-home, estimated impressions, no clicks. |
| `email_campaigns.csv` | CSV | 1 | 130 | Owned email — sends/opens/clicks/revenue. |
| `affiliate_partners.csv` | CSV | 1 | 140 | Affiliate — orders, sale amount, commission. |
| `retail_sales_offline.csv` | CSV | 1 | 187 | First-party offline sales — units + revenue by store/region. |
| `messy_mixed_export.csv` | CSV | 1 | 175 | **The hard one:** channel aliases, mixed date formats, `$`/`£`/`€` in spend, blanks, negative outliers. |
| `multi_channel_workbook.xlsx` | XLSX | 3 | 351 | Multi-tab workbook — one tab per paid-social channel. |
| `paid_search_weekly.xlsx` | XLSX | 1 | 100 | Weekly-granularity paid search. |
| `meta_multi_account.xlsx` | XLSX | 3 | 380 | Multi-tab — one tab per ad account, same schema (needs stacking). |

Every file lands cleanly: `read_preview` + `detect_header` find a confident header
row on all 22 sheets.

## Suggested starter files

- **Cleanest happy path:** `youtube_video.csv` (already has a `channel` column and
  ISO dates) or `email_campaigns.csv`.
- **Mapping practice:** `facebook_ads_2024.csv`, `google_ads_2024.csv` — raw
  partner headers that need mapping to canonical fields.
- **Multi-tab structure detection:** `multi_channel_workbook.xlsx`.
- **Validation / anomaly / AI-suggestion showcase:** `messy_mixed_export.csv`.

## Regenerating

The files are committed, but you can regenerate them (byte-stable, fixed seed):

```bash
uv run python sampledata/generate_sample_data.py
```

Only the standard library and `openpyxl` (already a backend dependency) are used.
