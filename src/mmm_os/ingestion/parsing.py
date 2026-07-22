"""Low-level file readers for CSV and multi-tab XLSX (P1-2).

Reads are streamed/chunked (P1-6): structure detection uses a bounded row preview,
and profiling (01.3) iterates a single sheet lazily. Cells are normalised to
``str | None`` so CSV and XLSX are handled uniformly downstream.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import IO

from openpyxl import load_workbook

Cell = str | None
Row = list[Cell]


class ParseError(RuntimeError):
    """Raised when a file cannot be parsed."""


class UnsupportedFileTypeError(ParseError):
    """Raised for a file extension we do not support yet."""


@dataclass
class RawSheet:
    """A bounded preview of one sheet's rows.

    Attributes:
        name: The sheet name.
        index: The zero-based sheet index within the workbook.
        rows: A bounded list of normalised rows (each a list of ``str | None``).
        truncated: Whether more rows exist beyond the preview.
    """

    name: str
    index: int
    rows: list[Row] = field(default_factory=list)
    truncated: bool = False

    def is_empty(self) -> bool:
        """Return whether the previewed sheet has no non-empty cell."""
        return all(cell is None for row in self.rows for cell in row)


def _normalize(value: object) -> Cell:
    """Normalise a raw cell value to a trimmed string or ``None``."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def file_kind(filename: str) -> str:
    """Return the parser kind for a filename (``"csv"`` or ``"xlsx"``).

    Args:
        filename: The file's name.

    Returns:
        ``"csv"`` or ``"xlsx"``.

    Raises:
        UnsupportedFileTypeError: For any other extension.
    """
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".xlsx":
        return "xlsx"
    raise UnsupportedFileTypeError(f"unsupported file type: {suffix or filename!r}")


def _csv_rows(stream: IO[bytes]) -> Iterator[Row]:
    text = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
    for raw in csv.reader(text):
        yield [_normalize(cell) for cell in raw]


def read_preview(stream: IO[bytes], filename: str, max_rows: int) -> list[RawSheet]:
    """Read a bounded preview of every sheet for structure detection.

    Args:
        stream: A readable binary stream of the file.
        filename: The file's name (selects the parser).
        max_rows: Maximum rows to read per sheet.

    Returns:
        One ``RawSheet`` per sheet (all sheets for XLSX; a single sheet for CSV).
    """
    kind = file_kind(filename)
    if kind == "csv":
        rows: list[Row] = []
        truncated = False
        for i, row in enumerate(_csv_rows(stream)):
            if i >= max_rows:
                truncated = True
                break
            rows.append(row)
        return [
            RawSheet(
                name=PurePosixPath(filename).stem or "Sheet1",
                index=0,
                rows=rows,
                truncated=truncated,
            )
        ]

    workbook = load_workbook(stream, read_only=True, data_only=True)
    try:
        sheets: list[RawSheet] = []
        for index, worksheet in enumerate(workbook.worksheets):
            rows = []
            truncated = False
            for i, row in enumerate(worksheet.iter_rows(values_only=True)):
                if i >= max_rows:
                    truncated = True
                    break
                rows.append([_normalize(cell) for cell in row])
            sheets.append(
                RawSheet(name=worksheet.title, index=index, rows=rows, truncated=truncated)
            )
        return sheets
    finally:
        workbook.close()


def iter_sheet_rows(stream: IO[bytes], filename: str, sheet_index: int) -> Iterator[Row]:
    """Iterate all rows of a single sheet lazily (for profiling).

    Args:
        stream: A readable binary stream of the file.
        filename: The file's name (selects the parser).
        sheet_index: The zero-based sheet index to iterate.

    Yields:
        Normalised rows of the requested sheet.
    """
    kind = file_kind(filename)
    if kind == "csv":
        yield from _csv_rows(stream)
        return

    workbook = load_workbook(stream, read_only=True, data_only=True)
    try:
        worksheet = workbook.worksheets[sheet_index]
        for row in worksheet.iter_rows(values_only=True):
            yield [_normalize(cell) for cell in row]
    finally:
        workbook.close()
