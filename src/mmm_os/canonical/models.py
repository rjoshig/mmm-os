"""Typed models describing the canonical schema and standard taxonomies.

These Pydantic v2 models define the *shape* of ``canonical_schema.yaml`` and
``taxonomies.yaml`` (see ``docs/canonical-schema.md``). They are the validation
contract the loader enforces at startup; nothing about the schema is hardcoded in
Python beyond this structure — the field list itself comes from the YAML.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FieldType(str, Enum):
    """Allowed canonical field types."""

    DATE = "date"
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    ENUM = "enum"
    ID = "id"
    TIMESTAMP = "timestamp"


class CanonicalField(BaseModel):
    """A single field in the canonical schema.

    Attributes:
        name: The canonical field name (snake_case).
        type: The field's data type.
        required: Whether the field is required for a row to be valid.
        taxonomy: For ``enum`` fields, the taxonomy that constrains the value.
        notes: Optional human-readable notes.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    type: FieldType
    required: bool = False
    taxonomy: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _enum_requires_taxonomy(self) -> CanonicalField:
        """Require a taxonomy on enum fields and forbid it on non-enum fields."""
        if self.type is FieldType.ENUM and not self.taxonomy:
            raise ValueError(f"enum field {self.name!r} must name a taxonomy")
        if self.type is not FieldType.ENUM and self.taxonomy is not None:
            raise ValueError(f"non-enum field {self.name!r} must not name a taxonomy")
        return self


class MeasurePolicy(BaseModel):
    """Policy governing measures (OQ-2.2)."""

    model_config = ConfigDict(extra="forbid")

    min_required: int = Field(ge=0, description="Minimum measures required per row.")


class CanonicalSchema(BaseModel):
    """The canonical target schema loaded from ``canonical_schema.yaml``."""

    model_config = ConfigDict(extra="forbid")

    version: int
    dimensions: list[CanonicalField]
    measures: list[CanonicalField]
    metadata: list[CanonicalField] = Field(default_factory=list)
    measure_policy: MeasurePolicy

    @model_validator(mode="after")
    def _unique_field_names(self) -> CanonicalSchema:
        """Ensure field names are unique across dimensions + measures + metadata."""
        names = [f.name for f in (*self.dimensions, *self.measures, *self.metadata)]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"duplicate canonical field name(s): {', '.join(duplicates)}")
        return self

    def required_dimensions(self) -> list[str]:
        """Return the names of required dimension fields."""
        return [f.name for f in self.dimensions if f.required]

    def enum_fields(self) -> list[CanonicalField]:
        """Return all enum-typed fields across dimensions, measures, and metadata."""
        return [
            f
            for f in (*self.dimensions, *self.measures, *self.metadata)
            if f.type is FieldType.ENUM
        ]


class Taxonomy(BaseModel):
    """A single controlled vocabulary: canonical terms plus synonym aliases."""

    model_config = ConfigDict(extra="forbid")

    terms: list[str] = Field(default_factory=list)
    aliases: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _aliases_reference_known_terms(self) -> Taxonomy:
        """Ensure every alias maps to a declared canonical term."""
        unknown = sorted(set(self.aliases) - set(self.terms))
        if unknown:
            raise ValueError(f"alias target(s) not in terms: {', '.join(unknown)}")
        return self


class Taxonomies(BaseModel):
    """All controlled vocabularies loaded from ``taxonomies.yaml``."""

    model_config = ConfigDict(extra="forbid")

    version: int
    taxonomies: dict[str, Taxonomy]

    def resolve(self, taxonomy: str, raw_value: str) -> str | None:
        """Resolve a raw value to its canonical term for a taxonomy.

        Matching is case-insensitive against both canonical terms and aliases.

        Args:
            taxonomy: The taxonomy name to resolve within.
            raw_value: The raw value to resolve.

        Returns:
            The canonical term, or ``None`` if no match is found (or the taxonomy
            is unknown).
        """
        tax = self.taxonomies.get(taxonomy)
        if tax is None:
            return None
        needle = raw_value.strip().casefold()
        for term in tax.terms:
            if term.casefold() == needle:
                return term
        for term, synonyms in tax.aliases.items():
            if any(syn.strip().casefold() == needle for syn in synonyms):
                return term
        return None
