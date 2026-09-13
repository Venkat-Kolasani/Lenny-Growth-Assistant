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


@router.get("/health/dependencies")
def dependencies(response: Response) -> dict:
    checks = {
        "postgres": _postgres(),
        "ollama": _ollama(),
        "groq_api_key": _groq_key(),
    }
    required = ["postgres"]
    if settings.default_model_provider == "groq":
        required.append("groq_api_key")
    if settings.default_model_provider == "ollama":
        required.append("ollama")
    ok = all(checks[name]["ok"] for name in required)
    if not ok:
        response.status_code = 503
    return {"ok": ok, **checks}
