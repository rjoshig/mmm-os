"""The file-backed ingestion source — the first real :class:`SourceConnector`.

Uploads (and, later, SFTP drops — both file families) land here. ``fetch`` reads
the immutable stored bytes through the object-storage abstraction and **reuses**
the existing Phase-1 machinery — :func:`~mmm_os.ingestion.parsing.read_preview`
plus :func:`~mmm_os.ingestion.structure.detect_header` /
:func:`~mmm_os.ingestion.structure.infer_columns` — to emit the common
:class:`~mmm_os.sources.landed.LandedDataset`. No parsing logic is duplicated:
this is a thin adapter that expresses "a file is just one kind of source".
"""

from __future__ import annotations

from mmm_os.ingestion.parsing import ParseOptions, read_preview
from mmm_os.ingestion.structure import detect_header, infer_columns
from mmm_os.sources.base import FetchRequest, SourceConnector
from mmm_os.sources.landed import SOURCE_TYPE_UPLOAD, LandedDataset, LandedTable
from mmm_os.storage.base import ObjectStorage

DEFAULT_PREVIEW_ROWS = 200


class FileSource(SourceConnector):
    """A :class:`SourceConnector` over a stored CSV / multi-tab XLSX file.

    Args:
        storage: The object-storage backend holding the immutable raw bytes.
        source_type: The source family to tag emitted datasets with (defaults to
            ``"upload"``; SFTP reuses the same parsing with ``"sftp"``).
    """

    def __init__(self, storage: ObjectStorage, *, source_type: str = SOURCE_TYPE_UPLOAD) -> None:
        """Bind the source to a storage backend and a source-family tag."""
        self.storage = storage
        self.source_type = source_type

    def fetch(self, request: FetchRequest) -> LandedDataset:
        """Read the stored file and land its non-empty sheets as a dataset.

        Args:
            request: Its ``ref`` must carry ``storage_key`` and ``filename``; an
                optional ``options["preview_rows"]`` bounds the detection preview.
                Any ``ref["file_id"]`` is echoed into ``source_ref`` (CC-3).

        Returns:
            A :class:`LandedDataset` with one :class:`LandedTable` per non-empty
            sheet, carrying detected header index + column structure.
        """
        storage_key = str(request.ref["storage_key"])
        filename = str(request.ref["filename"])
        preview_rows = DEFAULT_PREVIEW_ROWS
        parse_options: ParseOptions | None = None
        if request.options is not None:
            preview_rows = int(request.options.get("preview_rows", preview_rows))
            candidate = request.options.get("parse_options")
            if isinstance(candidate, ParseOptions):
                parse_options = candidate

        with self.storage.open(storage_key) as stream:
            preview = read_preview(stream, filename, preview_rows, parse_options)

        tables: list[LandedTable] = []
        for raw in preview:
            if raw.is_empty():
                continue
            detection = detect_header(raw.rows)
            columns = infer_columns(raw.rows, detection.index)
            tables.append(
                LandedTable(
                    name=raw.name,
                    index=raw.index,
                    header_row_index=detection.index,
                    columns=[c.as_dict() for c in columns],
                    confident=detection.confident,
                )
            )

        source_ref = {"file_id": request.ref.get("file_id")}
        return LandedDataset(source_type=self.source_type, source_ref=source_ref, tables=tables)
