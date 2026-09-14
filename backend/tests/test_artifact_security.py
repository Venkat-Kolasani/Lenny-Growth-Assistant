from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _artifact_ts() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "frontend/src/artifact.ts",
        here.parents[1] / "frontend/src/artifact.ts",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("frontend/src/artifact.ts")


def test_providers_endpoint_needs_no_database():
    response = client.get("/config/providers")
    assert response.status_code == 200
    ids = {p["id"] for p in response.json()["providers"]}
    assert ids == {"groq", "ollama", "anthropic"}
    by_id = {p["id"]: p for p in response.json()["providers"]}
    assert by_id["ollama"]["available"] is True
    assert "available" in by_id["anthropic"]
    assert by_id["anthropic"]["byok"] is True


def test_html_iframe_sandbox_forbids_scripts():
    src = _artifact_ts().read_text()
    assert 'HTML_SANDBOX = "allow-same-origin"' in src
    assert "allow-scripts" not in src
    assert "allow-forms" not in src
    assert "default-src 'none'" in src
