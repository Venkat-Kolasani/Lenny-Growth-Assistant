import pytest
from fastapi.testclient import TestClient

from app.agent.anthropic_provider import UNAVAILABLE, complete
from app.errors import ModelUnavailableError
from app.main import app

client = TestClient(app)


def test_anthropic_without_key_is_readable(monkeypatch):
    monkeypatch.setattr("app.agent.anthropic_provider.settings.anthropic_api_key", "")
    with pytest.raises(ModelUnavailableError, match="API key"):
        complete([{"role": "user", "content": "hi"}])
    assert "Groq" in UNAVAILABLE


def test_anthropic_accepts_client_key(monkeypatch):
    monkeypatch.setattr("app.agent.anthropic_provider.settings.anthropic_api_key", "")

    class FakeBlock:
        type = "text"
        text = "ok"

    class FakeResponse:
        content = [FakeBlock()]

    class FakeMessages:
        def create(self, **_kwargs):
            return FakeResponse()

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr("app.agent.anthropic_provider.Anthropic", lambda **_kwargs: FakeClient())
    assert complete([{"role": "user", "content": "hi"}], api_key="sk-ant-test") == "ok"


def test_switch_to_anthropic_without_key_is_400(monkeypatch):
    monkeypatch.setattr("app.api.sessions.settings.anthropic_api_key", "")
    created = client.post("/sessions", json={})
    if created.status_code == 503:
        pytest.skip("postgres down")
    sid = created.json()["id"]
    response = client.post(f"/sessions/{sid}/provider", json={"provider": "anthropic"})
    assert response.status_code == 400
    assert "Claude API key" in response.json()["detail"]
    client.delete(f"/sessions/{sid}")


def test_switch_to_anthropic_with_client_key_header(monkeypatch):
    monkeypatch.setattr("app.api.sessions.settings.anthropic_api_key", "")
    created = client.post("/sessions", json={})
    if created.status_code == 503:
        pytest.skip("postgres down")
    sid = created.json()["id"]
    response = client.post(
        f"/sessions/{sid}/provider",
        json={"provider": "anthropic"},
        headers={"X-Anthropic-API-Key": "sk-ant-test"},
    )
    assert response.status_code == 200
    assert response.json()["model_provider"] == "anthropic"
    client.delete(f"/sessions/{sid}")


def test_health_anthropic_required_only_when_default(monkeypatch):
    monkeypatch.setattr("app.api.health.settings.default_model_provider", "anthropic")
    monkeypatch.setattr("app.api.health._postgres", lambda: {"ok": True, "detail": "reachable"})
    monkeypatch.setattr("app.api.health._ollama", lambda: {"ok": True, "detail": "reachable"})
    monkeypatch.setattr("app.api.health._groq_key", lambda: {"ok": True, "detail": "set"})
    monkeypatch.setattr("app.api.health._anthropic_key", lambda: {"ok": False, "detail": "missing"})
    response = client.get("/health/dependencies")
    assert response.status_code == 503
    assert response.json()["anthropic_api_key"]["ok"] is False
