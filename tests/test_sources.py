"""Unit tests for the source-agnostic ingestion layer (FileSource → LandedDataset)."""

from __future__ import annotations

import io
from collections.abc import Callable

from mmm_os.sources import (
    SOURCE_TYPE_UPLOAD,
    FetchRequest,
    FileSource,
    LandedDataset,
)
from mmm_os.storage.local import LocalObjectStorage


def _land(storage: LocalObjectStorage, key: str, filename: str, data: bytes) -> LandedDataset:
    storage.put(key, io.BytesIO(data))
    request = FetchRequest(
        ref={"file_id": "f-1", "storage_key": key, "filename": filename},
        options={"preview_rows": 50},
    )
    return FileSource(storage).fetch(request)


def test_file_source_lands_csv(storage: LocalObjectStorage) -> None:
    """A CSV lands as one table with the header on row 0 and typed columns."""
    data = b"date,channel,spend\n2026-01-01,Facebook,100\n2026-01-02,Google,200\n"
    dataset = _land(storage, "t/1/data.csv", "data.csv", data)

    assert dataset.source_type == SOURCE_TYPE_UPLOAD
    assert dataset.source_ref == {"file_id": "f-1"}
    assert len(dataset.tables) == 1
    table = dataset.tables[0]
    assert table.header_row_index == 0
    assert table.confident is True
    types = {c["name"]: c["type"] for c in table.columns}
    assert types == {"date": "date", "channel": "string", "spend": "number"}


def test_file_source_lands_multitab_xlsx_and_skips_empty(
    storage: LocalObjectStorage,
    make_xlsx: Callable[[dict[str, list[list[object]]]], bytes],
) -> None:
    """A 3-sheet workbook lands 2 non-empty tables; the empty sheet is skipped."""
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
    dataset = _land(storage, "t/2/book.xlsx", "book.xlsx", xlsx)

    tables = {t.name: t for t in dataset.tables}
    assert set(tables) == {"Titled", "Clean"}  # empty sheet skipped
    assert tables["Titled"].header_row_index == 2
    assert tables["Clean"].header_row_index == 0
    assert tables["Titled"].index == 1  # stable ordinal within the workbook


def test_file_source_defaults_preview_rows(storage: LocalObjectStorage) -> None:
    """fetch works when no options are supplied (uses the default preview bound)."""
    storage.put("t/3/data.csv", io.BytesIO(b"a,b\n1,2\n"))
    dataset = FileSource(storage).fetch(
        FetchRequest(ref={"storage_key": "t/3/data.csv", "filename": "data.csv"})
    )
    assert len(dataset.tables) == 1
    assert dataset.source_ref == {"file_id": None}
