from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.agent.qa import INSUFFICIENT
from app.api.sessions import _citations
from app.main import app
from app.retrieval.search import RetrievedChunk
from app.settings import settings

client = TestClient(app)


def _chunk(cid: str, guest="Adam Grenier", title="Same episode") -> RetrievedChunk:
    return RetrievedChunk(
        id=cid,
        episode_guest=guest,
        episode_title=title,
        youtube_url="https://youtu.be/x",
        chunk_text="x",
        score=1.0,
    )


def test_citations_dedup_by_episode():
    cites = _citations([_chunk("1"), _chunk("2"), _chunk("3", "Other", "Other ep")], "answer")
    assert [c["guest"] for c in cites] == ["Adam Grenier", "Other"]
    assert cites[0]["chunk_id"] == "1"


def test_citations_empty_when_insufficient():
    assert _citations([_chunk("1")], INSUFFICIENT) == []


def _db():
    try:
        conn = psycopg.connect(settings.database_url)
        conn.execute("SELECT 1")
        return conn
    except Exception:
        pytest.skip("postgres down")


def test_delete_session_cascades_and_404s():
    created = client.post("/sessions", json={})
    if created.status_code == 503:
        pytest.skip("postgres down")
    assert created.status_code == 200
    sid = created.json()["id"]
    with _db() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, 'user', %s)",
            (sid, "hello title here"),
        )
        mid = conn.execute("SELECT id FROM messages WHERE session_id = %s", (sid,)).fetchone()[0]
        conn.execute(
            "INSERT INTO artifacts (session_id, message_id, type, title, content) VALUES (%s, %s, 'markdown', 't', 'c')",
            (sid, mid),
        )
        conn.commit()
    listed = client.get("/sessions")
    assert listed.status_code == 200
    row = next(s for s in listed.json() if s["id"] == sid)
    assert row["title"] == "hello title here"
    gone = client.delete(f"/sessions/{sid}")
    assert gone.status_code == 204
    assert client.get(f"/sessions/{sid}").status_code == 404
    assert client.delete(f"/sessions/{sid}").status_code == 404
    with _db() as conn:
        assert conn.execute("SELECT count(*) FROM messages WHERE session_id = %s", (sid,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM artifacts WHERE session_id = %s", (sid,)).fetchone()[0] == 0


def test_delete_unknown_session_is_404():
    response = client.delete(f"/sessions/{uuid4()}")
    if response.status_code == 503:
        pytest.skip("postgres down")
    assert response.status_code == 404


def _seed_session(title="hello title here"):
    created = client.post("/sessions", json={})
    if created.status_code == 503:
        pytest.skip("postgres down")
    sid = created.json()["id"]
    with _db() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, 'user', %s)",
            (sid, title),
        )
        conn.commit()
    return sid


def test_rename_session_and_empty_title_falls_back():
    sid = _seed_session()
    renamed = client.patch(f"/sessions/{sid}", json={"title": "My thread"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "My thread"
    listed = client.get("/sessions")
    assert next(s for s in listed.json() if s["id"] == sid)["title"] == "My thread"
    cleared = client.patch(f"/sessions/{sid}", json={"title": "  "})
    assert cleared.status_code == 200
    assert cleared.json()["title"] == "hello title here"
    client.delete(f"/sessions/{sid}")


def test_archive_hides_from_default_list():
    sid = _seed_session("archive me")
    archived = client.patch(f"/sessions/{sid}", json={"archived": True})
    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert sid not in [s["id"] for s in client.get("/sessions").json()]
    shown = client.get("/sessions?archived=true")
    assert shown.status_code == 200
    row = next(s for s in shown.json() if s["id"] == sid)
    assert row["archived"] is True
    client.delete(f"/sessions/{sid}")


def test_unarchive_returns_to_default_list():
    sid = _seed_session("restore me")
    client.patch(f"/sessions/{sid}", json={"archived": True})
    restored = client.patch(f"/sessions/{sid}", json={"archived": False})
    assert restored.status_code == 200
    assert restored.json()["archived"] is False
    assert any(s["id"] == sid for s in client.get("/sessions").json())
    client.delete(f"/sessions/{sid}")
