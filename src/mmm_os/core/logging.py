"""Structured logging setup.

Per ``CODING_STANDARDS.md``: logging is structured (JSON-capable), never uses
``print``, and includes ``tenant_id`` / ``job_id`` context where relevant. This
Phase-0 scaffold configures the standard library logger at the configured level;
richer structured/JSON formatting and request/job context binding are added in
later phases.
"""

from __future__ import annotations

import logging

from mmm_os.core.config import get_settings


def configure_logging() -> None:
    """Configure root logging level from settings.

    Idempotent enough for app startup; later phases replace this with a
    structured (JSON) handler that binds ``tenant_id`` and ``job_id``.
    """
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
