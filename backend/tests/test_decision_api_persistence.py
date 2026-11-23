from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_decisions_endpoint_persists_generated_decisions(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(
        "app.api.routes.Path",
        lambda value: (
            workspace if value == "../workspace"
            else Path(value)
        ),
    )

    client = TestClient(app)

    response = client.get(
        "/api/challenges/AI_DEAL_SCOPING_ASSISTANT/decisions"
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["challengeId"] == "AI_DEAL_SCOPING_ASSISTANT"
    assert payload["decisions"]

    saved = workspace / "AI_DEAL_SCOPING_ASSISTANT" / "decisions.json"
    assert saved.exists()


def test_verification_endpoint_returns_workspace_trace_artifacts(
    tmp_path,
    monkeypatch,
):
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(
        "app.api.routes.Path",
        lambda value: (
            workspace if value == "../workspace"
            else Path(value)
        ),
    )

    client = TestClient(app)
    response = client.get(
        "/api/challenges/AI_DEAL_SCOPING_ASSISTANT/verification"
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["challengeId"] == "AI_DEAL_SCOPING_ASSISTANT"
    assert "verification" in payload
    assert "provenance" in payload
    assert "contradictions" in payload
    assert payload["baseSelection"]["status"] in {"pending", "manual_review"}
