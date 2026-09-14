from __future__ import annotations

import httpx
import psycopg
from fastapi import APIRouter, Response

from app.settings import settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _postgres() -> dict:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return {"ok": True, "detail": "reachable"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc).split("\n")[0]}


def _ollama() -> dict:
    url = settings.ollama_base_url.rstrip("/") + "/api/tags"
    try:
        with httpx.Client(timeout=httpx.Timeout(3.0)) as client:
            response = client.get(url)
            response.raise_for_status()
        return {"ok": True, "detail": "reachable"}
    except httpx.TimeoutException:
        return {"ok": False, "detail": "timed out"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc).split("\n")[0]}


def _groq_key() -> dict:
    if settings.groq_api_key:
        return {"ok": True, "detail": "set"}
    return {"ok": False, "detail": "GROQ_API_KEY is missing"}


def _cloudflare() -> dict:
    if settings.cloudflare_account_id and settings.cloudflare_api_token:
        return {"ok": True, "detail": "configured"}
    return {"ok": False, "detail": "not configured (Groq 429 failover disabled)"}


def _anthropic_key() -> dict:
    if settings.anthropic_api_key:
        return {"ok": True, "detail": "set"}
    return {"ok": False, "detail": "ANTHROPIC_API_KEY is missing (BYOK)"}


def _corpus() -> dict:
    """Surface empty ingest so demos don't look like an Ollama failure."""
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM transcript_chunks WHERE embedding IS NOT NULL"
            ).fetchone()
        count = int(row[0]) if row else 0
        if count == 0:
            return {
                "ok": False,
                "detail": "0 embedded chunks — run `python scripts/ingest.py`",
            }
        return {"ok": True, "detail": f"{count} embedded chunks"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc).split("\n")[0]}


@router.get("/health/dependencies")
def dependencies(response: Response) -> dict:
    checks = {
        "postgres": _postgres(),
        "ollama": _ollama(),
        "groq_api_key": _groq_key(),
        "cloudflare": _cloudflare(),
        "anthropic_api_key": _anthropic_key(),
        "corpus": _corpus(),
    }
    required = ["postgres"]
    if settings.default_model_provider == "groq":
        required.append("groq_api_key")
    if settings.default_model_provider == "ollama":
        required.append("ollama")
    if settings.default_model_provider == "anthropic":
        required.append("anthropic_api_key")
    # Corpus is diagnostic: empty DB makes every sample look like a model failure.
    ok = all(checks[name]["ok"] for name in required)
    if not ok:
        response.status_code = 503
    return {"ok": ok, **checks}
