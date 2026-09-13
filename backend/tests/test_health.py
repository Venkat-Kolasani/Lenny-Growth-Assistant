from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness_ok_even_if_deps_are_down(monkeypatch):
    monkeypatch.setattr("app.api.health._postgres", lambda: {"ok": False, "detail": "down"})
    monkeypatch.setattr("app.api.health._ollama", lambda: {"ok": False, "detail": "down"})
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_postgres_down_returns_503(monkeypatch):
    monkeypatch.setattr("app.api.health._postgres", lambda: {"ok": False, "detail": "connection refused"})
    monkeypatch.setattr("app.api.health._ollama", lambda: {"ok": True, "detail": "reachable"})
    monkeypatch.setattr("app.api.health._groq_key", lambda: {"ok": True, "detail": "set"})
    response = client.get("/health/dependencies")
    assert response.status_code == 503
    body = response.json()
    assert body["ok"] is False
    assert "connection refused" in body["postgres"]["detail"]


def test_missing_groq_key_returns_503_when_groq_is_default(monkeypatch):
    monkeypatch.setattr("app.api.health.settings.default_model_provider", "groq")
    monkeypatch.setattr("app.api.health._postgres", lambda: {"ok": True, "detail": "reachable"})
    monkeypatch.setattr("app.api.health._ollama", lambda: {"ok": True, "detail": "reachable"})
    monkeypatch.setattr("app.api.health._groq_key", lambda: {"ok": False, "detail": "GROQ_API_KEY is missing"})
    response = client.get("/health/dependencies")
    assert response.status_code == 503
    assert response.json()["groq_api_key"]["ok"] is False


def test_ollama_down_is_reported_but_ok_when_using_groq(monkeypatch):
    monkeypatch.setattr("app.api.health.settings.default_model_provider", "groq")
    monkeypatch.setattr("app.api.health._postgres", lambda: {"ok": True, "detail": "reachable"})
    monkeypatch.setattr("app.api.health._ollama", lambda: {"ok": False, "detail": "timed out"})
    monkeypatch.setattr("app.api.health._groq_key", lambda: {"ok": True, "detail": "set"})
    response = client.get("/health/dependencies")
    assert response.status_code == 200
    assert response.json()["ollama"]["ok"] is False


def test_cloudflare_unconfigured_does_not_fail_health(monkeypatch):
    monkeypatch.setattr("app.api.health.settings.default_model_provider", "groq")
    monkeypatch.setattr("app.api.health._postgres", lambda: {"ok": True, "detail": "reachable"})
    monkeypatch.setattr("app.api.health._ollama", lambda: {"ok": True, "detail": "reachable"})
    monkeypatch.setattr("app.api.health._groq_key", lambda: {"ok": True, "detail": "set"})
    monkeypatch.setattr(
        "app.api.health._cloudflare",
        lambda: {"ok": False, "detail": "not configured"},
    )
    response = client.get("/health/dependencies")
    assert response.status_code == 200
    assert response.json()["cloudflare"]["ok"] is False
