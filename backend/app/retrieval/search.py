from dataclasses import dataclass
import math
import re

import psycopg

from app.errors import EmbedError
from app.ingestion.pipeline import embed_texts
from app.retrieval.rrf import reciprocal_rank_fusion
from app.settings import settings

TOP_K = 12
DENSE_K = 32
SPARSE_K = 32
RERANK_K = 32
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


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


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


def rerank_with_metadata(
    query_embedding: list[float],
    fused: list[tuple[str, float]],
    by_id: dict[str, RetrievedChunk],
) -> list[RetrievedChunk]:
    # ponytail: guest+title embed blend, not a cross-encoder; upgrade to one if eval stalls.
    pool = [(item_id, score) for item_id, score in fused[:RERANK_K] if item_id in by_id]
    if not pool or not query_embedding:
        return [by_id[item_id] for item_id, _ in fused[:TOP_K] if item_id in by_id]

    labels: list[str] = []
    index: dict[str, int] = {}
    for item_id, _ in pool:
        chunk = by_id[item_id]
        label = f"{chunk.episode_guest} · {chunk.episode_title}"
        if label not in index:
            index[label] = len(labels)
            labels.append(label)
    try:
        metas = embed_texts(labels)
    except EmbedError:
        return [by_id[item_id] for item_id, _ in fused[:TOP_K] if item_id in by_id]

    blended: list[tuple[str, float]] = []
    for item_id, rrf in pool:
        chunk = by_id[item_id]
        label = f"{chunk.episode_guest} · {chunk.episode_title}"
        sim = cosine(query_embedding, metas[index[label]])
        blended.append((item_id, rrf + 0.35 * sim))
    blended.sort(key=lambda pair: pair[1], reverse=True)
    return [by_id[item_id] for item_id, _ in blended[:TOP_K]]


def retrieve(query: str) -> list[RetrievedChunk]:
    dense: list[RetrievedChunk] = []
    sparse_and: list[RetrievedChunk] = []
    sparse_or: list[RetrievedChunk] = []
    embedding: list[float] = []
    with psycopg.connect(settings.database_url) as conn:
        try:
            embedding = embed_texts([query])[0]
            dense = _dense(conn, embedding)
        except EmbedError:
            embedding = []
            dense = []
        sparse_and = _sparse(conn, query, websearch=False)
        sparse_or = _sparse(conn, query, websearch=True)

    by_id = {chunk.id: chunk for chunk in dense + sparse_and + sparse_or}
    fused = reciprocal_rank_fusion(
        [[c.id for c in dense], [c.id for c in sparse_and], [c.id for c in sparse_or]]
    )
    if embedding:
        return rerank_with_metadata(embedding, fused, by_id)
    return [by_id[item_id] for item_id, _ in fused[:TOP_K] if item_id in by_id]
