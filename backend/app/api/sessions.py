from uuid import UUID

import psycopg
import structlog
from fastapi import APIRouter, HTTPException
from psycopg.types.json import Json

from app.agent.provider import model_for
from app.agent.qa import INSUFFICIENT
from app.agent.router import route
from app.agent.skills import run
from app.errors import ModelTimeoutError, ModelUnavailableError
from app.models import (
    ArtifactOut,
    Citation,
    MessageIn,
    MessageOut,
    ProviderSwitch,
    SessionCreate,
    SessionOut,
)
from app.retrieval.search import retrieve
from app.settings import settings

router = APIRouter()
log = structlog.get_logger()


def _conn() -> psycopg.Connection:
    return psycopg.connect(settings.database_url)


def _citations(chunks, text: str) -> list[dict]:
    if text == INSUFFICIENT:
        return []
    return [
        {
            "guest": c.episode_guest,
            "episode_title": c.episode_title,
            "youtube_url": c.youtube_url,
            "chunk_id": c.id,
        }
        for c in chunks
    ]


@router.post("/sessions", response_model=SessionOut)
def create_session(body: SessionCreate) -> SessionOut:
    provider = settings.default_model_provider
    name = model_for(provider)
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (user_metadata, model_provider, model_name)
                VALUES (%s, %s, %s)
                RETURNING id::text, model_provider, model_name
                """,
                (Json(body.user_metadata), provider, name),
            )
            row = cur.fetchone()
            conn.commit()
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable: " + str(exc).split("\n")[0]) from exc
    assert row is not None
    return SessionOut(id=row[0], model_provider=row[1], model_name=row[2])


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions() -> list[SessionOut]:
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id::text, model_provider, model_name FROM sessions ORDER BY updated_at DESC"
            )
            rows = cur.fetchall()
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable: " + str(exc).split("\n")[0]) from exc
    return [SessionOut(id=r[0], model_provider=r[1], model_name=r[2]) for r in rows]


@router.get("/sessions/{session_id}")
def get_session(session_id: UUID) -> dict:
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id::text, model_provider, model_name FROM sessions WHERE id = %s",
                (str(session_id),),
            )
            session = cur.fetchone()
            if session is None:
                raise HTTPException(status_code=404, detail="Session not found")
            cur.execute(
                """
                SELECT id::text, role, content, skill_used, citations
                FROM messages WHERE session_id = %s ORDER BY created_at
                """,
                (str(session_id),),
            )
            messages = cur.fetchall()
            cur.execute(
                """
                SELECT id::text, type, title, content
                FROM artifacts WHERE session_id = %s ORDER BY created_at
                """,
                (str(session_id),),
            )
            artifacts = cur.fetchall()
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable: " + str(exc).split("\n")[0]) from exc
    return {
        "id": session[0],
        "model_provider": session[1],
        "model_name": session[2],
        "messages": [
            {
                "id": m[0],
                "role": m[1],
                "content": m[2],
                "skill_used": m[3],
                "citations": m[4] or [],
            }
            for m in messages
        ],
        "artifacts": [
            {"id": a[0], "type": a[1], "title": a[2], "content": a[3]}
            for a in artifacts
        ],
    }


@router.post("/sessions/{session_id}/provider", response_model=SessionOut)
def switch_provider(session_id: UUID, body: ProviderSwitch) -> SessionOut:
    if body.provider not in {"groq", "ollama"}:
        raise HTTPException(status_code=422, detail="Provider must be groq or ollama")
    name = model_for(body.provider)
    label = "Ollama (local)" if body.provider == "ollama" else "Groq"
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM sessions WHERE id = %s", (str(session_id),))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Session not found")
            cur.execute(
                """
                UPDATE sessions
                SET model_provider = %s, model_name = %s, updated_at = now()
                WHERE id = %s
                RETURNING id::text, model_provider, model_name
                """,
                (body.provider, name, str(session_id)),
            )
            row = cur.fetchone()
            cur.execute(
                """
                INSERT INTO messages (session_id, role, content, skill_used)
                VALUES (%s, 'system', %s, 'provider_switch')
                """,
                (str(session_id), f"Now using {label} · {name}"),
            )
            conn.commit()
    except HTTPException:
        raise
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable: " + str(exc).split("\n")[0]) from exc
    assert row is not None
    return SessionOut(id=row[0], model_provider=row[1], model_name=row[2])


@router.get("/sessions/{session_id}/artifacts", response_model=list[ArtifactOut])
def list_artifacts(session_id: UUID) -> list[ArtifactOut]:
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM sessions WHERE id = %s", (str(session_id),))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Session not found")
            cur.execute(
                """
                SELECT id::text, type, title, content
                FROM artifacts WHERE session_id = %s ORDER BY created_at
                """,
                (str(session_id),),
            )
            rows = cur.fetchall()
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable: " + str(exc).split("\n")[0]) from exc
    return [ArtifactOut(id=r[0], type=r[1], title=r[2], content=r[3]) for r in rows]


@router.get("/artifacts/{artifact_id}", response_model=ArtifactOut)
def get_artifact(artifact_id: UUID) -> ArtifactOut:
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id::text, type, title, content FROM artifacts WHERE id = %s",
                (str(artifact_id),),
            )
            row = cur.fetchone()
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable: " + str(exc).split("\n")[0]) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return ArtifactOut(id=row[0], type=row[1], title=row[2], content=row[3])


@router.get("/config/providers")
def list_providers() -> dict:
    return {
        "providers": [
            {"id": "groq", "label": "Groq", "model": model_for("groq")},
            {"id": "ollama", "label": "Ollama (local)", "model": model_for("ollama")},
        ],
        "default": settings.default_model_provider,
    }


@router.post("/sessions/{session_id}/messages", response_model=MessageOut)
def post_message(session_id: UUID, body: MessageIn) -> MessageOut:
    skill = route(body.content)
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT model_provider FROM sessions WHERE id = %s",
                (str(session_id),),
            )
            session = cur.fetchone()
            if session is None:
                raise HTTPException(status_code=404, detail="Session not found")
            provider = session[0]
            cur.execute(
                """
                SELECT role, content FROM messages
                WHERE session_id = %s AND role IN ('user', 'assistant')
                ORDER BY created_at DESC LIMIT 6
                """,
                (str(session_id),),
            )
            history = [{"role": r[0], "content": r[1]} for r in reversed(cur.fetchall())]
            retrieval_query = body.content
            if history and len(body.content) < 80:
                prior = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
                if prior:
                    retrieval_query = f"{prior}\n{body.content}"

            chunks = retrieve(retrieval_query)
            try:
                text, title, markdown = run(skill, body.content, chunks, history, provider)
            except ModelTimeoutError as exc:
                log.warning("turn.timeout", skill=skill, provider=provider, chunks=len(chunks))
                raise HTTPException(status_code=504, detail=str(exc)) from exc
            except ModelUnavailableError as exc:
                log.warning("turn.unavailable", skill=skill, provider=provider, error=str(exc)[:160])
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            log.info(
                "turn",
                skill=skill,
                provider=provider,
                chunks=len(chunks),
                artifact=bool(markdown),
            )

            citations = _citations(chunks, text)
            artifact = None
            cur.execute(
                """
                INSERT INTO messages (session_id, role, content)
                VALUES (%s, 'user', %s)
                """,
                (str(session_id), body.content),
            )
            cur.execute(
                """
                INSERT INTO messages (session_id, role, content, skill_used, citations)
                VALUES (%s, 'assistant', %s, %s, %s)
                RETURNING id::text
                """,
                (str(session_id), text, skill, Json(citations)),
            )
            message_id = cur.fetchone()[0]
            if markdown:
                cur.execute(
                    """
                    INSERT INTO artifacts (session_id, message_id, type, title, content)
                    VALUES (%s, %s, 'markdown', %s, %s)
                    RETURNING id::text, type, title, content
                    """,
                    (str(session_id), message_id, title, markdown),
                )
                art = cur.fetchone()
                artifact = ArtifactOut(id=art[0], type=art[1], title=art[2], content=art[3])
            cur.execute("UPDATE sessions SET updated_at = now() WHERE id = %s", (str(session_id),))
            conn.commit()
    except HTTPException:
        raise
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable: " + str(exc).split("\n")[0]) from exc

    return MessageOut(
        id=message_id,
        role="assistant",
        content=text,
        skill_used=skill,
        citations=[Citation(**c) for c in citations],
        artifact=artifact,
    )
