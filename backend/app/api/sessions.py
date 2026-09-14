from uuid import UUID

import psycopg
import structlog
from fastapi import APIRouter, HTTPException, Response
from psycopg.types.json import Json

from app.agent import groq
from app.agent.provider import model_for
from app.agent.qa import INSUFFICIENT, history_window
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
    SessionPatch,
)
from app.retrieval.search import retrieve
from app.settings import settings

router = APIRouter()
log = structlog.get_logger()

_SESSION_COLS = """
s.id::text, s.model_provider, s.model_name,
COALESCE(NULLIF(btrim(s.title), ''), (
    SELECT LEFT(m.content, 80)
    FROM messages m
    WHERE m.session_id = s.id AND m.role = 'user'
    ORDER BY m.created_at
    LIMIT 1
)),
(s.archived_at IS NOT NULL)
"""


def _session_out(row) -> SessionOut:
    return SessionOut(
        id=row[0],
        model_provider=row[1],
        model_name=row[2],
        title=row[3],
        archived=bool(row[4]),
    )


def _conn() -> psycopg.Connection:
    return psycopg.connect(settings.database_url)


def _citations(chunks, text: str) -> list[dict]:
    if text == INSUFFICIENT:
        return []
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for chunk in chunks:
        key = (chunk.episode_guest, chunk.episode_title)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "guest": chunk.episode_guest,
                "episode_title": chunk.episode_title,
                "youtube_url": chunk.youtube_url,
                "chunk_id": chunk.id,
            }
        )
    return out


def _thinking(chunks) -> str | None:
    lines = []
    if chunks:
        seen: list[str] = []
        lines.append("Retrieved excerpts:")
        for chunk in chunks:
            label = f"{chunk.episode_guest} - {chunk.episode_title}"
            if label not in seen:
                seen.append(label)
                lines.append(f"• {label}")
    if groq.last_reasoning:
        if lines:
            lines.append("")
        lines.append(groq.last_reasoning)
    return "\n".join(lines) or None


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


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: UUID) -> Response:
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM retrieval_traces WHERE message_id IN (SELECT id FROM messages WHERE session_id = %s)",
                (str(session_id),),
            )
            cur.execute("DELETE FROM sessions WHERE id = %s RETURNING id", (str(session_id),))
            row = cur.fetchone()
            conn.commit()
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable: " + str(exc).split("\n")[0]) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=204)


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(archived: bool = False) -> list[SessionOut]:
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {_SESSION_COLS}
                FROM sessions s
                WHERE (s.archived_at IS NOT NULL) = %s
                ORDER BY s.updated_at DESC
                """,
                (archived,),
            )
            rows = cur.fetchall()
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable: " + str(exc).split("\n")[0]) from exc
    return [_session_out(r) for r in rows]


@router.patch("/sessions/{session_id}", response_model=SessionOut)
def patch_session(session_id: UUID, body: SessionPatch) -> SessionOut:
    sets = ["updated_at = now()"]
    args: list = []
    if "title" in body.model_fields_set:
        sets.append("title = %s")
        args.append((body.title or "").strip() or None)
    if body.archived is True:
        sets.append("archived_at = now()")
    elif body.archived is False:
        sets.append("archived_at = NULL")
    args.append(str(session_id))
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                f"UPDATE sessions SET {', '.join(sets)} WHERE id = %s RETURNING id",
                args,
            )
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Session not found")
            cur.execute(
                f"SELECT {_SESSION_COLS} FROM sessions s WHERE s.id = %s",
                (str(session_id),),
            )
            row = cur.fetchone()
            conn.commit()
    except HTTPException:
        raise
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable: " + str(exc).split("\n")[0]) from exc
    assert row is not None
    return _session_out(row)


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
                SELECT m.id::text, m.role, m.content, m.skill_used, m.citations, m.reasoning,
                       a.id::text, a.type, a.title
                FROM messages m
                LEFT JOIN artifacts a ON a.message_id = m.id
                WHERE m.session_id = %s
                ORDER BY m.created_at
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
                "reasoning": m[5],
                "artifact": {"id": m[6], "type": m[7], "title": m[8]} if m[6] else None,
            }
            for m in messages
        ],
        "artifacts": [
            {"id": a[0], "type": a[1], "title": a[2], "content": a[3]}
            for a in artifacts
        ],
    }


_PROVIDER_LABELS = {"groq": "Groq", "ollama": "Ollama (local)", "anthropic": "Anthropic"}


@router.post("/sessions/{session_id}/provider", response_model=SessionOut)
def switch_provider(session_id: UUID, body: ProviderSwitch) -> SessionOut:
    if body.provider not in _PROVIDER_LABELS:
        raise HTTPException(status_code=422, detail="Provider must be groq, ollama, or anthropic")
    if body.provider == "anthropic" and not settings.anthropic_api_key:
        raise HTTPException(
            status_code=400,
            detail="ANTHROPIC_API_KEY is missing. Add your key to .env, or use Groq or Ollama.",
        )
    name = model_for(body.provider)
    label = _PROVIDER_LABELS[body.provider]
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
            {
                "id": "groq",
                "label": "Groq",
                "model": model_for("groq"),
                "available": bool(settings.groq_api_key),
            },
            {
                "id": "ollama",
                "label": "Ollama (local)",
                "model": model_for("ollama"),
                "available": True,
            },
            {
                "id": "anthropic",
                "label": "Anthropic",
                "model": model_for("anthropic"),
                "available": bool(settings.anthropic_api_key),
            },
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
            hist_limit = history_window(provider)
            cur.execute(
                """
                SELECT role, content FROM messages
                WHERE session_id = %s AND role IN ('user', 'assistant')
                ORDER BY created_at DESC LIMIT %s
                """,
                (str(session_id), hist_limit),
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
            thinking = _thinking(chunks)
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
                INSERT INTO messages (session_id, role, content, skill_used, citations, reasoning)
                VALUES (%s, 'assistant', %s, %s, %s, %s)
                RETURNING id::text
                """,
                (str(session_id), text, skill, Json(citations), thinking),
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
        reasoning=thinking,
        artifact=artifact,
    )
