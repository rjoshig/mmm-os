"""Portable logical backup + restore (Phase 10, P10-2).

A dialect-agnostic logical dump: every mapped table is exported to a JSONL archive
(one file per table) that restores into either SQLite or Postgres. This is the
"nightly logical dump as a portable fallback" from the DR design — independent of
any engine's native dump format, so a backup taken on one dialect restores on the
other (supporting the portability requirement + cross-environment DR drills).

Native, point-in-time backups (managed Postgres PITR, object-storage versioning)
remain the primary DR mechanism in production; this is the portable complement and
the mechanism used in restore drills/tests.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, delete, insert, select
from sqlalchemy.orm import Session

from mmm_os.db.base import Base

_MANIFEST = "manifest.json"


def _encode(value: Any) -> Any:
    """Convert a DB value into a JSON-safe, self-describing form."""
    if isinstance(value, uuid.UUID):
        return {"__uuid__": str(value)}
    if isinstance(value, datetime):
        return {"__dt__": value.isoformat()}
    if isinstance(value, date):
        return {"__date__": value.isoformat()}
    if isinstance(value, Decimal):
        return {"__dec__": str(value)}
    if isinstance(value, bytes):
        return {"__b64__": base64.b64encode(value).decode("ascii")}
    return value  # str/int/float/bool/None + JSON columns (dict/list)


def _decode(value: Any) -> Any:
    """Reverse :func:`_encode`."""
    if isinstance(value, dict) and len(value) == 1:
        key, inner = next(iter(value.items()))
        if key == "__uuid__":
            return uuid.UUID(inner)
        if key == "__dt__":
            return datetime.fromisoformat(inner)
        if key == "__date__":
            return date.fromisoformat(inner)
        if key == "__dec__":
            return Decimal(inner)
        if key == "__b64__":
            return base64.b64decode(inner)
    return value


def export_backup(engine: Engine, out_dir: Path) -> Path:
    """Write a portable logical backup of every table under ``out_dir``.

    Args:
        engine: The source database engine.
        out_dir: Directory to write the archive into (created if absent).

    Returns:
        The archive directory path (containing one ``<table>.jsonl`` per table plus
        a ``manifest.json``).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = list(Base.metadata.sorted_tables)
    counts: dict[str, int] = {}
    with Session(engine) as session:
        for table in tables:
            rows = session.execute(select(table)).mappings().all()
            path = out_dir / f"{table.name}.jsonl"
            with path.open("w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps({k: _encode(v) for k, v in row.items()}) + "\n")
            counts[table.name] = len(rows)
    manifest = {"tables": [t.name for t in tables], "counts": counts}
    (out_dir / _MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_dir


def import_backup(engine: Engine, in_dir: Path, *, truncate: bool = True) -> dict[str, int]:
    """Restore a logical backup into ``engine``.

    Inserts parents-first (``sorted_tables`` order) so foreign keys resolve; when
    ``truncate`` is set, existing rows are cleared children-first beforehand.

    Args:
        engine: The target database engine (schema must already exist).
        in_dir: The archive directory produced by :func:`export_backup`.
        truncate: Whether to clear existing rows before restoring.

    Returns:
        A map of table name -> rows restored.
    """
    tables = list(Base.metadata.sorted_tables)
    restored: dict[str, int] = {}
    with Session(engine) as session:
        if truncate:
            for table in reversed(tables):  # children first
                session.execute(delete(table))
        for table in tables:  # parents first
            path = in_dir / f"{table.name}.jsonl"
            if not path.exists():
                continue
            rows: list[dict[str, Any]] = []
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        rows.append({k: _decode(v) for k, v in json.loads(line).items()})
            if rows:
                session.execute(insert(table), rows)
            restored[table.name] = len(rows)
        session.commit()
    return restored


def _main() -> None:
    """CLI: ``python -m mmm_os.governance.backup {export|import} <dir> [--url URL]``.

    Defaults the engine to ``BACKEND_DATABASE_URL`` (via settings) so a nightly cron
    can dump the live backend; ``--url`` overrides (e.g. a silo DB or a restore
    target). Restore drills point ``import`` at a fresh database.
    """
    import argparse

    from sqlalchemy import create_engine

    from mmm_os.core.config import get_settings

    parser = argparse.ArgumentParser(description="mmm-os portable logical backup (P10-2)")
    parser.add_argument("action", choices=["export", "import"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--url", default=None, help="DB URL; defaults to BACKEND_DATABASE_URL")
    parser.add_argument(
        "--no-truncate", action="store_true", help="restore without clearing existing rows"
    )
    args = parser.parse_args()

    url = args.url or get_settings().backend_database_url
    engine = create_engine(url)
    if args.action == "export":
        out = export_backup(engine, args.directory)
        print(f"backup written to {out}")
    else:
        restored = import_backup(engine, args.directory, truncate=not args.no_truncate)
        print(f"restored {sum(restored.values())} rows across {len(restored)} tables")


if __name__ == "__main__":
    _main()
