"""Tests for the Phase 0.1 canonical schema + taxonomies loader."""

from __future__ import annotations

import pytest

from mmm_os.canonical import (
    CanonicalSchema,
    Taxonomies,
    load_and_validate,
    load_canonical_schema,
    load_taxonomies,
)
from mmm_os.canonical.loader import CanonicalConfigError
from mmm_os.canonical.models import CanonicalField, FieldType


def test_shipped_config_loads_and_validates() -> None:
    """The bundled schema + taxonomies load and cross-validate cleanly."""
    config = load_and_validate()
    assert isinstance(config.schema, CanonicalSchema)
    assert isinstance(config.taxonomies, Taxonomies)


def test_required_fields_match_oq_2_2() -> None:
    """date + channel are required; at least one measure is required (OQ-2.2)."""
    schema = load_canonical_schema()
    assert set(schema.required_dimensions()) == {"date", "channel"}
    assert schema.measure_policy.min_required == 1


def test_every_enum_field_references_a_known_taxonomy() -> None:
    """Cross-validation: enum fields only reference taxonomies that exist."""
    config = load_and_validate()
    known = set(config.taxonomies.taxonomies)
    for field in config.schema.enum_fields():
        assert field.taxonomy in known


def test_alias_resolution_is_case_insensitive() -> None:
    """FB / fb_ads / 'facebook ads' collapse to the canonical Facebook term."""
    taxonomies = load_taxonomies()
    for raw in ("FB", "fb_ads", "facebook ads", "FACEBOOK ADS"):
        assert taxonomies.resolve("channel", raw) == "Facebook"
    # A canonical term resolves to itself.
    assert taxonomies.resolve("channel", "google") == "Google"
    # An unknown value resolves to None.
    assert taxonomies.resolve("channel", "no-such-channel") is None
    # An unknown taxonomy resolves to None.
    assert taxonomies.resolve("nope", "FB") is None


def test_enum_field_without_taxonomy_is_rejected() -> None:
    """An enum field must name a taxonomy."""
    with pytest.raises(ValueError, match="must name a taxonomy"):
        CanonicalField(name="channel", type=FieldType.ENUM)


def test_non_enum_field_with_taxonomy_is_rejected() -> None:
    """A non-enum field must not name a taxonomy."""
    with pytest.raises(ValueError, match="must not name a taxonomy"):
        CanonicalField(name="spend", type=FieldType.NUMBER, taxonomy="channel")


def test_enum_referencing_missing_taxonomy_fails_cross_validation() -> None:
    """A schema whose enum references an absent taxonomy fails to load."""
    with pytest.raises(CanonicalConfigError, match="unknown taxonomy"):
        # geo exists in the schema but we point the loader at a taxonomy file
        # that omits it by loading a schema-only view against empty taxonomies.
        schema = load_canonical_schema()
        from mmm_os.canonical.loader import _cross_validate

        empty = Taxonomies(version=1, taxonomies={})
        _cross_validate(schema, empty)


def test_duplicate_field_names_are_rejected() -> None:
    """Field names must be unique across dimensions, measures, and metadata."""
    with pytest.raises(ValueError, match="duplicate canonical field name"):
        CanonicalSchema.model_validate(
            {
                "version": 1,
                "dimensions": [
                    {"name": "date", "type": "date", "required": True},
                    {"name": "date", "type": "date"},
                ],
                "measures": [{"name": "spend", "type": "number"}],
                "measure_policy": {"min_required": 1},
            }
        )
