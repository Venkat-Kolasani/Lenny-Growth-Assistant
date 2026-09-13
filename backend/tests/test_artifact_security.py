from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def test_providers_endpoint_needs_no_database():
    response = client.get("/config/providers")
    assert response.status_code == 200
    ids = {p["id"] for p in response.json()["providers"]}
    assert ids == {"groq", "ollama"}


def test_html_iframe_sandbox_forbids_scripts():
    src = (ROOT / "frontend/src/artifact.ts").read_text()
    assert 'HTML_SANDBOX = "allow-same-origin"' in src
    assert "allow-scripts" not in src
    assert "allow-forms" not in src
    assert "default-src 'none'" in src
