"""Unit tests for the suggestion service with a fake LLM client (05.2)."""

from __future__ import annotations

import pytest

from mmm_os.ai.errors import LLMResponseError
from mmm_os.ai.suggestions import SuggestionService


class FakeLLM:
    """A fake LLM client returning a canned response and capturing the prompt."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.last_user: str | None = None
        self.last_system: str | None = None

    def complete(self, *, system: str, user: str) -> str:
        self.last_system = system
        self.last_user = user
        return self.response


def test_suggest_column_mappings_parses_and_sends_profile_only() -> None:
    """Mapping suggestions are parsed; the prompt carries profile stats, not rows."""
    fake = FakeLLM(
        '[{"source_column":"chan","canonical_field":"channel","confidence":0.9,"rationale":"r"}]'
    )
    service = SuggestionService(fake)
    out = service.suggest_column_mappings(
        [{"name": "chan", "sample_values": ["FB"], "distinct_count": 1}], ["channel", "date"]
    )
    assert out[0].canonical_field == "channel"
    assert out[0].confidence == 0.9
    # P5-1: profile shape (samples + distinct counts) is what we send.
    assert '"sample_values"' in (fake.last_user or "")
    assert '"distinct_count"' in (fake.last_user or "")


def test_suggest_handles_fenced_json() -> None:
    """A ```json fenced response is parsed."""
    fake = FakeLLM('```json\n{"canonical_term":"Facebook","confidence":0.8,"rationale":"r"}\n```')
    result = SuggestionService(fake).suggest_taxonomy_term(["FB", "fb_ads"], ["Facebook"])
    assert result.canonical_term == "Facebook"
    assert result.confidence == 0.8


def test_explain_anomaly() -> None:
    """An anomaly explanation is extracted."""
    fake = FakeLLM('{"explanation":"likely duplicate import"}')
    assert SuggestionService(fake).explain_anomaly("spend spike") == "likely duplicate import"


def test_bad_json_raises() -> None:
    """A non-JSON response raises a clear error."""
    with pytest.raises(LLMResponseError):
        SuggestionService(FakeLLM("not json at all")).explain_anomaly("x")
