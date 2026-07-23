"""Integration tests for the AI suggestion API with a fake LLM client (05.2)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mmm_os.api.deps import get_llm_client
from mmm_os.api.main import app

_MAPPING_RESPONSE = (
    '[{"source_column":"date","canonical_field":"date","confidence":0.97,"rationale":"iso"},'
    '{"source_column":"channel","canonical_field":"channel","confidence":0.9,"rationale":"names"},'
    '{"source_column":"spend","canonical_field":"spend","confidence":0.6,"rationale":"numeric"}]'
)


class FakeLLM:
    def complete(self, *, system: str, user: str) -> str:
        return _MAPPING_RESPONSE


@pytest.fixture
def ai_client(client: TestClient) -> Iterator[TestClient]:
    """A TestClient with the LLM dependency overridden to a fake."""
    app.dependency_overrides[get_llm_client] = lambda: FakeLLM()
    yield client
    app.dependency_overrides.pop(get_llm_client, None)


def _sheet_id(client: TestClient, tenant_id: uuid.UUID) -> str:
    upload = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={
            "upload": ("data.csv", b"date,channel,spend\n2026-01-01,Facebook,100\n", "text/csv")
        },
    )
    file_id = upload.json()["file"]["id"]
    processed = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    sheet_id: str = processed.json()["sheets"][0]["id"]
    return sheet_id


def test_suggest_persists_with_confidence_and_disposition(ai_client: TestClient) -> None:
    """Suggestions persist pending with confidence, rationale, and a disposition."""
    tenant_id = uuid.uuid4()
    sheet_id = _sheet_id(ai_client, tenant_id)
    response = ai_client.post(f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/suggest-mapping")
    assert response.status_code == 201, response.text
    suggestions = {s["payload"]["source_column"]: s for s in response.json()["suggestions"]}
    assert suggestions["date"]["state"] == "pending"
    assert suggestions["date"]["confidence"] == 0.97
    assert suggestions["date"]["payload"]["disposition"] == "auto_fill"
    assert suggestions["spend"]["payload"]["disposition"] == "review"  # 0.6


def test_accept_writes_mapping_config(ai_client: TestClient) -> None:
    """Accepting a mapping suggestion writes it into the mapping-config store (P5-8)."""
    tenant_id = uuid.uuid4()
    sheet_id = _sheet_id(ai_client, tenant_id)
    suggestions = ai_client.post(
        f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/suggest-mapping"
    ).json()["suggestions"]
    date_suggestion = next(s for s in suggestions if s["payload"]["source_column"] == "date")

    accepted = ai_client.post(
        f"/api/v1/tenants/{tenant_id}/suggestions/{date_suggestion['id']}/accept"
    )
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["suggestion"]["state"] == "accepted"
    assert body["mapping_config_version"] == 1


def test_reject_updates_state(ai_client: TestClient) -> None:
    """Rejecting a suggestion records the decision without writing config."""
    tenant_id = uuid.uuid4()
    sheet_id = _sheet_id(ai_client, tenant_id)
    suggestions = ai_client.post(
        f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/suggest-mapping"
    ).json()["suggestions"]
    rejected = ai_client.post(
        f"/api/v1/tenants/{tenant_id}/suggestions/{suggestions[0]['id']}/reject"
    )
    assert rejected.status_code == 200
    assert rejected.json()["state"] == "rejected"


_TRANSFORM_RESPONSE = (
    '[{"target_field":"channel","operation":"normalize_text","params":{"lower":true},'
    '"confidence":0.9,"rationale":"trim/case"},'
    '{"target_field":"spend","operation":"nope","params":{},"confidence":0.8,"rationale":"x"}]'
)


class FakeTransformLLM:
    def complete(self, *, system: str, user: str) -> str:
        return _TRANSFORM_RESPONSE


def test_suggest_transforms_persists_and_accept_appends_rule(client: TestClient) -> None:
    """AI transform suggestions persist (bad ops filtered); accepting appends a rule."""
    app.dependency_overrides[get_llm_client] = lambda: FakeTransformLLM()
    try:
        tenant_id = uuid.uuid4()
        sheet_id = _sheet_id(client, tenant_id)
        resp = client.post(f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/suggest-transforms")
        assert resp.status_code == 201, resp.text
        suggestions = resp.json()["suggestions"]
        # The invalid "nope" operation is filtered out; only normalize_text remains.
        assert len(suggestions) == 1
        assert suggestions[0]["payload"]["operation"] == "normalize_text"
        assert suggestions[0]["kind"] == "transform_rule"

        accepted = client.post(
            f"/api/v1/tenants/{tenant_id}/suggestions/{suggestions[0]['id']}/accept"
        )
        assert accepted.status_code == 200, accepted.text
        # Accepting appends the rule to the sheet's rule set (a new version).
        assert accepted.json()["mapping_config_version"] == 1

        rule_set = client.get(f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/rule-set")
        assert rule_set.status_code == 200, rule_set.text
        ops = [r["operation"] for r in rule_set.json()["rules"]]
        assert ops == ["normalize_text"]
    finally:
        app.dependency_overrides.pop(get_llm_client, None)


def test_suggest_when_disabled_returns_503(client: TestClient) -> None:
    """With the LLM off (default) and no override, suggesting returns 503."""
    tenant_id = uuid.uuid4()
    sheet_id = _sheet_id(client, tenant_id)
    response = client.post(f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/suggest-mapping")
    assert response.status_code == 503
