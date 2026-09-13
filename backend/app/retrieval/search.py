from dataclasses import dataclass

import psycopg

from app.errors import EmbedError
from app.ingestion.pipeline import embed_texts
from app.retrieval.rrf import reciprocal_rank_fusion
from app.settings import settings

TOP_K = 8
DENSE_K = 20
SPARSE_K = 20


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


def _sparse(conn: psycopg.Connection, query: str) -> list[RetrievedChunk]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id::text, episode_guest, episode_title, youtube_url, chunk_text,
                   ts_rank(search_vector, plainto_tsquery('english', %s)) AS score
            FROM transcript_chunks
            WHERE search_vector @@ plainto_tsquery('english', %s)
            ORDER BY score DESC
            LIMIT %s
            """,
            (query, query, SPARSE_K),
        )
        return [
            RetrievedChunk(id=r[0], episode_guest=r[1], episode_title=r[2], youtube_url=r[3], chunk_text=r[4], score=float(r[5] or 0))
            for r in cur.fetchall()
        ]


def retrieve(query: str) -> list[RetrievedChunk]:
    dense: list[RetrievedChunk] = []
    sparse: list[RetrievedChunk] = []
    with psycopg.connect(settings.database_url) as conn:
        try:
            embedding = embed_texts([query])[0]
            dense = _dense(conn, embedding)
        except EmbedError:
            dense = []
        sparse = _sparse(conn, query)

    by_id = {chunk.id: chunk for chunk in dense + sparse}
    fused = reciprocal_rank_fusion(
        [[c.id for c in dense], [c.id for c in sparse]]
    )
    return [by_id[item_id] for item_id, _ in fused[:TOP_K] if item_id in by_id]
