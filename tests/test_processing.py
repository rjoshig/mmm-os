"""Integration tests for file processing / structure detection (01.2)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient


def _upload(client: TestClient, tenant_id: uuid.UUID, name: str, content: bytes, ctype: str) -> str:
    response = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={"upload": (name, content, ctype)},
    )
    assert response.status_code == 201, response.text
    file_id: str = response.json()["file"]["id"]
    return file_id


def test_process_multitab_xlsx(
    client: TestClient, make_xlsx: Callable[[dict[str, list[list[object]]]], bytes]
) -> None:
    """A 3-sheet XLSX (empty / title-rows / clean) yields 2 non-empty sheets."""
    tenant_id = uuid.uuid4()
    xlsx = make_xlsx(
        {
            "Empty": [],
            "Titled": [
                ["Q1 Report", None, None],
                [None, None, None],
                ["date", "channel", "spend"],
                ["2026-01-01", "Facebook", 100],
                ["2026-01-02", "Google", 200],
            ],
            "Clean": [
                ["date", "channel", "impressions"],
                ["2026-01-01", "TikTok", 5000],
            ],
        }
    )
    file_id = _upload(
        client,
        tenant_id,
        "book.xlsx",
        xlsx,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    response = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["job"]["status"] == "succeeded"
    sheets = {s["sheet_name"]: s for s in body["sheets"]}
    assert set(sheets) == {"Titled", "Clean"}  # empty sheet skipped
    assert sheets["Titled"]["header_row_index"] == 2
    assert sheets["Clean"]["header_row_index"] == 0
    titled_types = {c["name"]: c["type"] for c in sheets["Titled"]["columns"]}
    assert titled_types["date"] == "date"
    assert titled_types["channel"] == "string"
    assert titled_types["spend"] == "number"


def test_process_csv(client: TestClient) -> None:
    """A CSV yields a single parsed sheet with the header on row 0."""
    tenant_id = uuid.uuid4()
    content = b"date,channel,spend\n2026-01-01,Facebook,100\n2026-01-02,Google,200\n"
    file_id = _upload(client, tenant_id, "data.csv", content, "text/csv")

    response = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "succeeded"
    assert len(body["sheets"]) == 1
    assert body["sheets"][0]["header_row_index"] == 0


def test_process_malformed_file_marks_job_failed(client: TestClient) -> None:
    """A malformed/unsupported file marks the job failed without crashing (P1-7)."""
    tenant_id = uuid.uuid4()
    file_id = _upload(client, tenant_id, "notes.txt", b"just some text", "text/plain")

    response = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "failed"
    assert body["sheets"] == []


def test_process_unknown_file_404(client: TestClient) -> None:
    """Processing a non-existent file returns 404."""
    tenant_id = uuid.uuid4()
    response = client.post(f"/api/v1/tenants/{tenant_id}/files/{uuid.uuid4()}/process")
    assert response.status_code == 404
