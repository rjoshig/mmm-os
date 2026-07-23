"""Tests for file-format parsing + per-customer feed templates (Slice 7.4)."""

from __future__ import annotations

import io
import uuid

from fastapi.testclient import TestClient

from mmm_os.ingestion.parsing import FixedWidthField, ParseOptions, read_preview


def test_fixed_width_parsing_slices_and_synthesizes_header() -> None:
    # Space-padded fixed-width, no source header line.
    data = b"alice00042\nbob  00099\n"
    fields = (FixedWidthField("name", 0, 5), FixedWidthField("amount", 5, 5))
    opts = ParseOptions(fmt="fixed_width", fixed_fields=fields, has_header=False)
    sheet = read_preview(io.BytesIO(data), "feed.txt", 10, opts)[0]
    assert sheet.rows[0] == ["name", "amount"]  # synthesized from field names
    assert sheet.rows[1] == ["alice", "00042"]
    assert sheet.rows[2] == ["bob", "00099"]


def test_delimiter_by_extension_generic_path() -> None:
    # Tab / pipe extensions are recognised without a template.
    assert read_preview(io.BytesIO(b"a\tb\n1\t2\n"), "x.tsv", 5)[0].rows == [
        ["a", "b"],
        ["1", "2"],
    ]
    assert read_preview(io.BytesIO(b"a|b\n1|2\n"), "x.psv", 5)[0].rows == [
        ["a", "b"],
        ["1", "2"],
    ]


def test_delimiter_sniffing_via_template_options() -> None:
    # A delimited template with no explicit delimiter sniffs the content (";" here),
    # and parses an otherwise-ambiguous .txt feed.
    opts = ParseOptions(fmt="delimited", delimiter=None)
    rows = read_preview(io.BytesIO(b"a;b;c\n1;2;3\n"), "feed.txt", 5, opts)[0].rows
    assert rows[0] == ["a", "b", "c"]


def test_ambiguous_extension_rejected_without_template() -> None:
    from mmm_os.ingestion.parsing import UnsupportedFileTypeError

    try:
        read_preview(io.BytesIO(b"just text"), "notes.txt", 5)
    except UnsupportedFileTypeError:
        pass
    else:  # pragma: no cover - the assertion is the failure signal
        raise AssertionError(".txt should be unsupported without a feed template")


def test_feed_template_crud_and_preview(client: TestClient) -> None:
    tid = uuid.uuid4()
    base = f"/api/v1/tenants/{tid}/feed-templates"
    created = client.post(
        base,
        json={
            "name": "Daily sales (fixed)",
            "fmt": "fixed_width",
            "has_header": False,
            "fixed_fields": [
                {"name": "store", "start": 0, "width": 4},
                {"name": "spend", "start": 4, "width": 6},
            ],
            "expected_columns": ["store", "spend"],
        },
    )
    assert created.status_code == 201, created.text
    template_id = created.json()["id"]

    listing = client.get(base)
    assert listing.status_code == 200 and len(listing.json()) == 1

    sample = b"1001012345\n1002006789\n"
    preview = client.post(
        f"{base}/{template_id}/preview",
        files={"upload": ("sales_0101.txt", sample, "text/plain")},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["columns"] == ["store", "spend"]
    assert body["rows"][0] == ["1001", "012345"]
    assert body["signature_matches"] is True  # header matches expected_columns

    assert client.delete(f"{base}/{template_id}").status_code == 204
    assert client.get(base).json() == []


def test_fixed_width_template_requires_fields(client: TestClient) -> None:
    tid = uuid.uuid4()
    resp = client.post(
        f"/api/v1/tenants/{tid}/feed-templates",
        json={"name": "bad", "fmt": "fixed_width", "fixed_fields": []},
    )
    assert resp.status_code == 400
