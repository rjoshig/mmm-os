"""Load and validate the canonical schema and taxonomies at startup.

The YAML resources are bundled as package data under ``mmm_os.resources``. The
loader parses them into the typed models (``models.py``), cross-validates that
every ``enum`` field references an existing taxonomy, and fails fast on any
problem so the application never boots with invalid config (P0.1-6).
"""

from __future__ import annotations

from importlib import resources
from typing import Any

import yaml
from pydantic import ValidationError

from mmm_os.canonical.models import CanonicalSchema, Taxonomies

CANONICAL_SCHEMA_RESOURCE = "canonical_schema.yaml"
TAXONOMIES_RESOURCE = "taxonomies.yaml"


class CanonicalConfigError(RuntimeError):
    """Raised when the canonical schema or taxonomies fail to load or validate."""


class CanonicalConfig:
    """The validated pair of canonical schema + taxonomies.

    Attributes:
        schema: The parsed and validated canonical schema.
        taxonomies: The parsed and validated taxonomies.
    """

    def __init__(self, schema: CanonicalSchema, taxonomies: Taxonomies) -> None:
        """Store the validated schema and taxonomies.

        Args:
            schema: The validated canonical schema.
            taxonomies: The validated taxonomies.
        """
        self.schema = schema
        self.taxonomies = taxonomies


def _read_resource(name: str) -> dict[str, Any]:
    """Read and YAML-parse a bundled resource into a mapping.

    Args:
        name: The resource filename under ``mmm_os.resources``.

    Returns:
        The parsed YAML as a dictionary.

    Raises:
        CanonicalConfigError: If the resource is missing, unparseable, or not a mapping.
    """
    try:
        text = resources.files("mmm_os.resources").joinpath(name).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError) as exc:  # pragma: no cover - packaging guard
        raise CanonicalConfigError(f"resource {name!r} not found") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise CanonicalConfigError(f"resource {name!r} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise CanonicalConfigError(f"resource {name!r} must contain a mapping at the top level")
    return data


def load_canonical_schema(name: str = CANONICAL_SCHEMA_RESOURCE) -> CanonicalSchema:
    """Load and validate the canonical schema resource.

    Args:
        name: The resource filename to load.

    Returns:
        The validated ``CanonicalSchema``.

    Raises:
        CanonicalConfigError: If the resource fails structural validation.
    """
    try:
        return CanonicalSchema.model_validate(_read_resource(name))
    except ValidationError as exc:
        raise CanonicalConfigError(f"invalid canonical schema {name!r}: {exc}") from exc


def load_taxonomies(name: str = TAXONOMIES_RESOURCE) -> Taxonomies:
    """Load and validate the taxonomies resource.

    Args:
        name: The resource filename to load.

    Returns:
        The validated ``Taxonomies``.

    Raises:
        CanonicalConfigError: If the resource fails structural validation.
    """
    try:
        return Taxonomies.model_validate(_read_resource(name))
    except ValidationError as exc:
        raise CanonicalConfigError(f"invalid taxonomies {name!r}: {exc}") from exc


def _cross_validate(schema: CanonicalSchema, taxonomies: Taxonomies) -> None:
    """Ensure every enum field references a taxonomy that exists (P0.1-4).

    Args:
        schema: The loaded canonical schema.
        taxonomies: The loaded taxonomies.

    Raises:
        CanonicalConfigError: If an enum field names an unknown taxonomy.
    """
    known = set(taxonomies.taxonomies)
    missing = {
        f.taxonomy
        for f in schema.enum_fields()
        if f.taxonomy is not None and f.taxonomy not in known
    }
    if missing:
        raise CanonicalConfigError(
            f"enum field(s) reference unknown taxonomy: {', '.join(sorted(missing))}"
        )


def load_and_validate(
    schema_name: str = CANONICAL_SCHEMA_RESOURCE,
    taxonomies_name: str = TAXONOMIES_RESOURCE,
) -> CanonicalConfig:
    """Load both resources, cross-validate, and return the validated config.

    Args:
        schema_name: The canonical-schema resource filename.
        taxonomies_name: The taxonomies resource filename.

    Returns:
        A ``CanonicalConfig`` holding the validated schema and taxonomies.

    Raises:
        CanonicalConfigError: On any load, parse, or validation failure.
    """
    schema = load_canonical_schema(schema_name)
    taxonomies = load_taxonomies(taxonomies_name)
    _cross_validate(schema, taxonomies)
    return CanonicalConfig(schema=schema, taxonomies=taxonomies)
