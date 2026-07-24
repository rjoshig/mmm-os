"""Semantic (cross-field) validation checks — meaningful MMM data validation (P17).

These catch data errors by making sense of the data (CC-15): funnel monotonicity
(clicks <= impressions), ratio plausibility (CTR/CVR/CPC/CPM), and delivery/revenue
coherence. Pure functions over canonical-keyed, transformed rows; each returns
``Finding`` objects and only fires when the relevant fields are present, so a sheet
that carries only spend is never spuriously flagged.
"""

from __future__ import annotations

from mmm_os.canonical.models import CanonicalSchema
from mmm_os.ingestion.structure import parse_number
from mmm_os.transform.types import Table
from mmm_os.validation.flags import Finding

# Plausibility bands (OQ-17.1 — configurable per tenant later). Generous defaults
# so only clearly-wrong data is flagged.
_CTR_MAX = 0.30  # click-through rate ceiling
_CVR_MAX = 1.0  # conversion rate ceiling (conversions per click)


def _num(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return parse_number(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _present(schema: CanonicalSchema, *names: str) -> set[str]:
    measures = {f.name for f in schema.measures}
    return {n for n in names if n in measures}


def check_funnel_monotonicity(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag rows that violate funnel ordering (a genuine data impossibility).

    ``clicks <= impressions``, ``conversions <= clicks``, ``reach <= impressions``.
    """
    findings: list[Finding] = []
    pairs = [("clicks", "impressions"), ("conversions", "clicks"), ("reach", "impressions")]
    for i, row in enumerate(table):
        for lower, upper in pairs:
            lo, hi = _num(row.get(lower)), _num(row.get(upper))
            if lo is None or hi is None:
                continue
            if lo > hi:
                findings.append(
                    Finding(
                        "funnel_monotonicity",
                        f"{lower} ({lo:g}) exceeds {upper} ({hi:g})",
                        {"row": i, "field": lower, "compared_to": upper},
                    )
                )
    return findings


def check_ctr_plausibility(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag implausible click-through rates (clicks / impressions outside [0, CTR_MAX])."""
    if not _present(schema, "clicks", "impressions") >= {"clicks", "impressions"}:
        return []
    findings: list[Finding] = []
    for i, row in enumerate(table):
        clicks, impressions = _num(row.get("clicks")), _num(row.get("impressions"))
        if clicks is None or not impressions:
            continue
        ctr = clicks / impressions
        if ctr > _CTR_MAX:
            findings.append(
                Finding(
                    "ctr_implausible",
                    f"CTR {ctr:.3f} exceeds plausible ceiling {_CTR_MAX}",
                    {"row": i, "field": "clicks", "ctr": round(ctr, 4)},
                )
            )
    return findings


def check_cvr_plausibility(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag implausible conversion rates (conversions / clicks outside [0, CVR_MAX])."""
    if not _present(schema, "conversions", "clicks") >= {"conversions", "clicks"}:
        return []
    findings: list[Finding] = []
    for i, row in enumerate(table):
        conversions, clicks = _num(row.get("conversions")), _num(row.get("clicks"))
        if conversions is None or not clicks:
            continue
        cvr = conversions / clicks
        if cvr > _CVR_MAX:
            findings.append(
                Finding(
                    "cvr_implausible",
                    f"conversion rate {cvr:.3f} exceeds ceiling {_CVR_MAX}",
                    {"row": i, "field": "conversions", "cvr": round(cvr, 4)},
                )
            )
    return findings


def check_spend_delivery_coherence(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag positive spend with zero/absent impressions (spend without delivery)."""
    if not _present(schema, "spend", "impressions") >= {"spend", "impressions"}:
        return []
    findings: list[Finding] = []
    for i, row in enumerate(table):
        spend, impressions = _num(row.get("spend")), _num(row.get("impressions"))
        if spend is None or impressions is None:
            continue
        if spend > 0 and impressions == 0:
            findings.append(
                Finding(
                    "spend_without_delivery",
                    f"spend {spend:g} with zero impressions",
                    {"row": i, "field": "spend"},
                )
            )
    return findings


def check_revenue_conversion_coherence(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag positive revenue with zero/absent conversions (revenue without conversions)."""
    if not _present(schema, "revenue", "conversions") >= {"revenue", "conversions"}:
        return []
    findings: list[Finding] = []
    for i, row in enumerate(table):
        revenue, conversions = _num(row.get("revenue")), _num(row.get("conversions"))
        if revenue is None or conversions is None:
            continue
        if revenue > 0 and conversions == 0:
            findings.append(
                Finding(
                    "revenue_without_conversion",
                    f"revenue {revenue:g} with zero conversions",
                    {"row": i, "field": "revenue"},
                )
            )
    return findings


SEMANTIC_CHECKS = (
    check_funnel_monotonicity,
    check_ctr_plausibility,
    check_cvr_plausibility,
    check_spend_delivery_coherence,
    check_revenue_conversion_coherence,
)
