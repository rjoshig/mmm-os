"""Tests for the Phase-9 connector framework (mock partner clients)."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from mmm_os.connectors.credentials import load_token, store_token
from mmm_os.connectors.registry import build_partner_connector
from mmm_os.connectors.scheduling import run_sync
from mmm_os.connectors.sftp.source import LocalDirSftpClient, pull_sftp
from mmm_os.models import ConnectorConfig, ConnectorCredential, SyncRun
from mmm_os.secrets import SecretStore
from mmm_os.sources.base import FetchRequest
from mmm_os.storage.local import LocalObjectStorage

_WINDOW = (date(2026, 1, 1), date(2026, 1, 7))


def _fetch(key: str, account_ctx: dict | None = None) -> list[dict]:
    connector = build_partner_connector(key, account_ctx=account_ctx)
    dataset = connector.fetch(FetchRequest(ref={}, config={}, date_range=_WINDOW))
    return dataset.tables[0].records or []


def test_meta_normalizes_nested_metrics() -> None:
    """Meta pull maps channel + extracts nested conversions/revenue via the template."""
    row = _fetch("meta")[0]
    assert row["channel"] == "Facebook"
    assert row["sub_channel"] == "Facebook"
    assert row["funnel_stage"] == "Conversion"
    assert row["conversions"] == 7.0
    assert row["revenue"] == 350.0
    assert row["currency"] == "USD"


def test_google_micros_and_geo_resolution() -> None:
    """Google spend is de-micro'd and the geo-target id is resolved via account_ctx."""
    row = _fetch("google_ads", account_ctx={"geo_map": {"2840": "United States"}})[0]
    assert row["channel"] == "Google"
    assert row["spend"] == 125.0
    assert row["geo"] == "United States"


def test_dv360_strips_total_rows() -> None:
    """DV360 drops the trailing grand-total row before mapping."""
    rows = _fetch("dv360")
    assert len(rows) == 1
    assert rows[0]["channel"] == "Programmatic"
    assert rows[0]["ad_group"] == "IO-1"


def test_tiktok_flattens_and_casts() -> None:
    """TikTok flattens the split response and casts string metrics to numbers."""
    row = _fetch("tiktok")[0]
    assert row["channel"] == "TikTok"
    assert row["campaign"] == "TikTok Launch"
    assert row["spend"] == 80.25
    assert row["geo"] == "US"


def test_credentials_stored_encrypted(engine: Engine, secret_store: SecretStore) -> None:
    """A token is stored in the SecretStore; the DB holds only a reference (CC-10)."""
    tid = uuid.uuid4()
    with Session(engine) as session:
        config = ConnectorConfig(tenant_id=tid, connector_key="meta", name="Meta")
        session.add(config)
        session.flush()
        cred = store_token(
            session, secret_store, tenant_id=tid, connector_config_id=config.id, token="tok-secret"
        )
        session.commit()

        assert cred.secret_ref_name != "tok-secret"
        assert load_token(secret_store, cred) == "tok-secret"
        stored = session.scalar(
            select(ConnectorCredential).where(ConnectorCredential.id == cred.id)
        )
        assert stored is not None and "tok-secret" not in stored.secret_ref_name


def test_run_sync_is_idempotent(engine: Engine) -> None:
    """Re-running a sync for the same window replaces the prior run (CC-6)."""
    tid = uuid.uuid4()
    with Session(engine) as session:
        config = ConnectorConfig(tenant_id=tid, connector_key="meta", name="Meta", settings={})
        session.add(config)
        session.flush()
        connector = build_partner_connector("meta")

        first = run_sync(session, connector, config, _WINDOW)
        second = run_sync(session, connector, config, _WINDOW)
        session.commit()

        assert first.sync_run.row_count == 1 and second.sync_run.row_count == 1
        runs = session.scalars(
            select(SyncRun).where(SyncRun.connector_config_id == config.id)
        ).all()
        assert len(runs) == 1  # replaced, not duplicated


def test_sftp_pull_lands_files(engine: Engine, storage: LocalObjectStorage, tmp_path: Path) -> None:
    """SFTP pull ingests a dropped file as an immutable upload."""
    tid = uuid.uuid4()
    drop = tmp_path / "sftp" / str(tid)
    drop.mkdir(parents=True)
    (drop / "sales.csv").write_bytes(b"date,channel,spend\n2026-01-01,FB,10\n")
    client = LocalDirSftpClient(tmp_path / "sftp")

    with Session(engine) as session:
        files = pull_sftp(session, storage, client, tenant_id=tid, remote_dir=str(tid))
        session.commit()
        assert len(files) == 1 and files[0].filename == "sales.csv"
        with storage.open(f"{tid}/{files[0].id}/sales.csv") as fh:
            assert b"2026-01-01" in fh.read()


def test_connector_api_config_and_sync(client: TestClient) -> None:
    """Create a connector config, trigger a sync, and list the runs (dev fake client)."""
    tid = uuid.uuid4()
    created = client.post(
        f"/api/v1/tenants/{tid}/connector-configs",
        json={"connector_key": "meta", "name": "Meta Prod", "account_ids": ["act_1"]},
    )
    assert created.status_code == 201, created.text
    config_id = created.json()["id"]

    synced = client.post(f"/api/v1/tenants/{tid}/connector-configs/{config_id}/sync")
    assert synced.status_code == 200, synced.text
    assert synced.json()["status"] == "succeeded" and synced.json()["row_count"] == 1

    runs = client.get(f"/api/v1/tenants/{tid}/connector-configs/{config_id}/sync-runs")
    assert runs.status_code == 200 and len(runs.json()) == 1
