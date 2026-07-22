"""Tests for per-column profiling (01.3)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from mmm_os.ingestion.profiling import profile_rows
from mmm_os.models import Profile


def test_profile_rows_computes_stats() -> None:
    """profile_rows computes distinct/null/min/max per column below the header."""
    columns = [
        {"index": 0, "name": "channel", "type": "string"},
        {"index": 1, "name": "spend", "type": "number"},
    ]
    rows = [
        ["channel", "spend"],  # header (skipped)
        ["Facebook", "100"],
        ["Google", "300"],
        ["Facebook", None],  # null spend
    ]
    row_count, stats = profile_rows(
        rows, columns, header_index=0, distinct_limit=10, sample_limit=5
    )

    assert row_count == 3
    by_name = {s["name"]: s for s in stats}
    assert by_name["channel"]["distinct_count"] == 2
    assert by_name["channel"]["null_count"] == 0
    assert by_name["spend"]["null_count"] == 1
    assert by_name["spend"]["null_rate"] == 1 / 3
    assert by_name["spend"]["min"] == 100.0
    assert by_name["spend"]["max"] == 300.0


def test_process_persists_profiles(client: TestClient, engine: Engine) -> None:
    """Processing a CSV persists a profile per non-empty sheet (P1-5)."""
    tenant_id = uuid.uuid4()
    content = b"date,channel,spend\n2026-01-01,Facebook,100\n2026-01-02,Google,200\n"
    upload = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={"upload": ("data.csv", content, "text/csv")},
    )
    file_id = upload.json()["file"]["id"]

    response = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    assert response.status_code == 200
    sheet_id = uuid.UUID(response.json()["sheets"][0]["id"])

    with Session(engine) as session:
        profile = session.scalar(select(Profile).where(Profile.sheet_id == sheet_id))
        assert profile is not None
        assert profile.row_count == 2
        stats = {c["name"]: c for c in profile.column_stats["columns"]}
        assert stats["channel"]["distinct_count"] == 2
        assert stats["spend"]["min"] == 100.0
        assert stats["spend"]["max"] == 200.0
        # Profiles hold distinct values + stats only, never full row dumps.
        assert len(stats["channel"]["sample_values"]) <= 20
