from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException
from psycopg.types.json import Json

from app.agent import groq
from app.agent.qa import INSUFFICIENT, answer
from app.errors import ModelTimeoutError, ModelUnavailableError
from app.models import Citation, MessageIn, MessageOut, SessionCreate, SessionOut
from app.retrieval.search import retrieve
from app.settings import settings

router = APIRouter()


def _conn() -> psycopg.Connection:
    return psycopg.connect(settings.database_url)


@router.post("/sessions", response_model=SessionOut)
def create_session(body: SessionCreate) -> SessionOut:
    model_name = groq.GROQ_MODEL if settings.default_model_provider == "groq" else settings.ollama_model
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (user_metadata, model_provider, model_name)
                VALUES (%s, %s, %s)
                RETURNING id::text, model_provider, model_name
                """,
                (Json(body.user_metadata), settings.default_model_provider, model_name),
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
    }


@router.post("/sessions/{session_id}/messages", response_model=MessageOut)
def post_message(session_id: UUID, body: MessageIn) -> MessageOut:
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM sessions WHERE id = %s", (str(session_id),))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Session not found")
            cur.execute(
                """
                SELECT role, content FROM messages
                WHERE session_id = %s AND role IN ('user', 'assistant')
                ORDER BY created_at DESC LIMIT 6
                """,
                (str(session_id),),
            )
            history = [{"role": r[0], "content": r[1]} for r in reversed(cur.fetchall())]
            # ponytail: fold the last user turn into the retrieval query instead of a rewrite LLM call
            retrieval_query = body.content
            if history and len(body.content) < 80:
                prior = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
                if prior:
                    retrieval_query = f"{prior}\n{body.content}"

            chunks = retrieve(retrieval_query)
            try:
                text = answer(body.content, chunks, history)
            except ModelTimeoutError as exc:
                raise HTTPException(status_code=504, detail=str(exc)) from exc
            except ModelUnavailableError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc

            citations = [
                {
                    "guest": c.episode_guest,
                    "episode_title": c.episode_title,
                    "youtube_url": c.youtube_url,
                    "chunk_id": c.id,
                }
                for c in chunks
            ]
            if text == INSUFFICIENT:
                citations = []

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
                VALUES (%s, 'assistant', %s, 'qa', %s)
                RETURNING id::text
                """,
                (str(session_id), text, Json(citations)),
            )
            message_id = cur.fetchone()[0]
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
        skill_used="qa",
        citations=[Citation(**c) for c in citations],
    )
