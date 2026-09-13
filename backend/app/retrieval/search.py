from dataclasses import dataclass
import re

import psycopg

from app.errors import EmbedError
from app.ingestion.pipeline import embed_texts
from app.retrieval.rrf import reciprocal_rank_fusion
from app.settings import settings

TOP_K = 8
DENSE_K = 20
SPARSE_K = 20
_TOKEN = re.compile(r"[A-Za-z0-9]+")


def or_websearch(text: str) -> str:
    # ponytail: plainto_tsquery ANDs every term, so a long question zeros sparse
    # even when the guest/title is in search_vector. OR the tokens; upgrade to a
    # query rewriter if eval stalls on short ambiguous questions.
    terms = [tok for tok in _TOKEN.findall(text) if len(tok) >= 3]
    return " OR ".join(terms) if terms else text


@dataclass
class RetrievedChunk:
    id: str
    episode_guest: str
    episode_title: str
    youtube_url: str | None
    chunk_text: str
    score: float


def _dense(conn: psycopg.Connection, embedding: list[float]) -> list[RetrievedChunk]:
    vector = "[" + ",".join(str(x) for x in embedding) + "]"
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id::text, episode_guest, episode_title, youtube_url, chunk_text,
                   1 - (embedding <=> %s::vector) AS score
            FROM transcript_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vector, vector, DENSE_K),
        )
        return [
            RetrievedChunk(id=r[0], episode_guest=r[1], episode_title=r[2], youtube_url=r[3], chunk_text=r[4], score=float(r[5] or 0))
            for r in cur.fetchall()
        ]


def _sparse(conn: psycopg.Connection, query: str, *, websearch: bool) -> list[RetrievedChunk]:
    fn = "websearch_to_tsquery" if websearch else "plainto_tsquery"
    tsquery = or_websearch(query) if websearch else query
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id::text, episode_guest, episode_title, youtube_url, chunk_text,
                   ts_rank(search_vector, {fn}('english', %s)) AS score
            FROM transcript_chunks
            WHERE search_vector @@ {fn}('english', %s)
            ORDER BY score DESC
            LIMIT %s
            """,
            (tsquery, tsquery, SPARSE_K),
        )
        return [
            RetrievedChunk(id=r[0], episode_guest=r[1], episode_title=r[2], youtube_url=r[3], chunk_text=r[4], score=float(r[5] or 0))
            for r in cur.fetchall()
        ]


def retrieve(query: str) -> list[RetrievedChunk]:
    dense: list[RetrievedChunk] = []
    sparse_and: list[RetrievedChunk] = []
    sparse_or: list[RetrievedChunk] = []
    with psycopg.connect(settings.database_url) as conn:
        try:
            embedding = embed_texts([query])[0]
            dense = _dense(conn, embedding)
        except EmbedError:
            dense = []
        sparse_and = _sparse(conn, query, websearch=False)
        sparse_or = _sparse(conn, query, websearch=True)

    by_id = {chunk.id: chunk for chunk in dense + sparse_and + sparse_or}
    fused = reciprocal_rank_fusion(
        [[c.id for c in dense], [c.id for c in sparse_and], [c.id for c in sparse_or]]
    )
    return [by_id[item_id] for item_id, _ in fused[:TOP_K] if item_id in by_id]
