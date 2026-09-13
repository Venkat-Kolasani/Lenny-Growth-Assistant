from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import httpx
import psycopg
import yaml

from app.errors import EmbedError, ModelTimeoutError, ModelUnavailableError
from app.ingestion.chunk import chunk_text
from app.settings import settings

TRANSCRIPT_REPO = "https://github.com/ChatPRD/lennys-podcast-transcripts.git"
INDEX_LINK = re.compile(r"\[[^\]]+\]\(\.\./episodes/([^/]+)/transcript\.md\)")


def repo_root() -> Path:
    for path in Path(__file__).resolve().parents:
        if (path / "docker-compose.yml").exists():
            return path
    raise SystemExit("could not find repo root (docker-compose.yml)")


def ensure_transcripts(dest: Path) -> None:
    if (dest / "episodes").is_dir():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"cloning transcripts into {dest}", flush=True)
    subprocess.check_call(["git", "clone", "--depth", "1", TRANSCRIPT_REPO, str(dest)])


def topic_tags_by_folder(index_dir: Path) -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    if not index_dir.is_dir():
        return tags
    for path in index_dir.glob("*.md"):
        if path.name.lower() == "readme.md":
            continue
        topic = path.stem
        for folder in INDEX_LINK.findall(path.read_text(encoding="utf-8")):
            tags.setdefault(folder, []).append(topic)
    return tags


def parse_transcript(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"no YAML frontmatter in {path}")
    meta = yaml.safe_load(parts[1]) or {}
    return meta, parts[2].strip()


def embed_texts(texts: list[str]) -> list[list[float]]:
    url = settings.ollama_base_url.rstrip("/") + "/api/embed"
    timeout = httpx.Timeout(settings.model_timeout_seconds)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                url,
                json={"model": settings.ollama_embed_model, "input": texts},
            )
            response.raise_for_status()
    except httpx.ConnectError as exc:
        raise EmbedError(
            f"Ollama unreachable at {settings.ollama_base_url}. "
            "Start it on the host and pull nomic-embed-text."
        ) from exc
    except httpx.TimeoutException as exc:
        raise EmbedError(
            f"Ollama embed timed out after {settings.model_timeout_seconds}s."
        ) from exc
    payload = response.json()
    embeddings = payload.get("embeddings")
    if not embeddings:
        raise EmbedError(f"unexpected embed response: {payload!r}")
    return embeddings


TEMPLATE_PREFIX_START = "This excerpt is from Lenny's Podcast episode"


def episode_prefix(guest: str, title: str) -> str:
    return f'This excerpt is from Lenny\'s Podcast episode "{title}" with guest {guest}.'


def _situate_prompt(chunk: str, guest: str, title: str) -> str:
    return (
        f'Start with "{guest}:". One sentence on what this excerpt from '
        f'the episode "{title}" is about. No preamble.\n\nExcerpt:\n{chunk[:600]}'
    )


def contextualize(chunk: str, guest: str, title: str) -> str:
    url = settings.ollama_base_url.rstrip("/") + "/api/generate"
    timeout = httpx.Timeout(settings.model_timeout_seconds)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            url,
            json={
                "model": settings.ollama_model,
                "prompt": _situate_prompt(chunk, guest, title),
                "stream": False,
            },
        )
        response.raise_for_status()
    return (response.json().get("response") or "").strip()


def llm_prefix(chunk: str, guest: str, title: str) -> str:
    if settings.groq_api_key:
        from app.agent.provider import complete

        try:
            text = complete(
                "groq",
                [{"role": "user", "content": _situate_prompt(chunk, guest, title)}],
                temperature=0.1,
                max_tokens=120,
            ).strip()
            if text:
                return text
        except (ModelUnavailableError, ModelTimeoutError):
            pass
    try:
        return contextualize(chunk, guest, title) or episode_prefix(guest, title)
    except Exception:
        return episode_prefix(guest, title)


def prefixes_for_episode(
    chunks: list[str],
    guest: str,
    title: str,
    *,
    contextualize_chunks: bool,
) -> list[str]:
    if not chunks:
        return []
    # ponytail: one LLM sentence per episode, not per chunk. 10k Ollama calls
    # is ~27h; Groq's free daily cap is ~1k. Per-chunk if eval still misses.
    if contextualize_chunks:
        one = llm_prefix(chunks[0], guest, title)
        return [one] * len(chunks)
    one = episode_prefix(guest, title)
    return [one] * len(chunks)


def load_episode(
    conn: psycopg.Connection,
    meta: dict,
    body: str,
    extra_tags: list[str],
    *,
    contextualize_chunks: bool,
) -> int:
    guest = str(meta.get("guest") or "Unknown")
    title = str(meta.get("title") or "Untitled")
    youtube_url = meta.get("youtube_url")
    publish_date = meta.get("publish_date")
    keywords = meta.get("keywords") or []
    tags = sorted({*extra_tags, *[str(k) for k in keywords]})
    chunks = chunk_text(body)
    if not chunks:
        return 0

    prefixes = prefixes_for_episode(
        chunks, guest, title, contextualize_chunks=contextualize_chunks
    )
    to_embed = [
        f"{prefix}\n\n{chunk}" if prefix else chunk
        for prefix, chunk in zip(prefixes, chunks, strict=True)
    ]
    embeddings = embed_texts(to_embed)
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM transcript_chunks WHERE episode_guest = %s AND episode_title = %s",
            (guest, title),
        )
        for index, (chunk, prefix, embedding) in enumerate(
            zip(chunks, prefixes, embeddings, strict=True)
        ):
            cur.execute(
                """
                INSERT INTO transcript_chunks (
                    episode_guest, episode_title, youtube_url, publish_date,
                    topic_tags, chunk_index, contextual_prefix, chunk_text, embedding
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                """,
                (
                    guest,
                    title,
                    youtube_url,
                    publish_date,
                    tags,
                    index,
                    prefix,
                    chunk,
                    "[" + ",".join(str(x) for x in embedding) + "]",
                ),
            )
    conn.commit()
    return len(chunks)


def backfill_contextualize(conn: psycopg.Connection, limit: int | None) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT episode_guest, episode_title
            FROM transcript_chunks
            WHERE contextual_prefix IS NULL
               OR contextual_prefix LIKE %s
            ORDER BY episode_guest, episode_title
            """,
            (TEMPLATE_PREFIX_START + "%",),
        )
        episodes = cur.fetchall()
    if limit is not None:
        episodes = episodes[:limit]
    updated = 0
    for index, (guest, title) in enumerate(episodes, start=1):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, chunk_text
                FROM transcript_chunks
                WHERE episode_guest = %s AND episode_title = %s
                ORDER BY chunk_index
                """,
                (guest, title),
            )
            rows = cur.fetchall()
        if not rows:
            continue
        ids = [row[0] for row in rows]
        chunks = [row[1] for row in rows]
        prefixes = prefixes_for_episode(chunks, guest, title, contextualize_chunks=True)
        embeddings = embed_texts(
            [f"{prefix}\n\n{chunk}" for prefix, chunk in zip(prefixes, chunks, strict=True)]
        )
        with conn.cursor() as cur:
            for chunk_id, prefix, embedding in zip(ids, prefixes, embeddings, strict=True):
                cur.execute(
                    """
                    UPDATE transcript_chunks
                    SET contextual_prefix = %s, embedding = %s::vector
                    WHERE id = %s::uuid
                    """,
                    (
                        prefix,
                        "[" + ",".join(str(x) for x in embedding) + "]",
                        chunk_id,
                    ),
                )
        conn.commit()
        updated += len(rows)
        print(f"  {index}/{len(episodes)} {guest}: {len(rows)} chunks", flush=True)
    return updated


def run(limit: int | None, contextualize_chunks: bool) -> None:
    root = repo_root()
    source = root / "data" / "transcripts"
    if contextualize_chunks:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT EXISTS (SELECT 1 FROM transcript_chunks)")
                has_chunks = bool(cur.fetchone()[0])
            if has_chunks:
                print("backfilling LLM prefixes on existing chunks (no re-chunk)", flush=True)
                loaded = backfill_contextualize(conn, limit)
                print(f"done: {loaded} chunks", flush=True)
                return

    ensure_transcripts(source)
    tags = topic_tags_by_folder(source / "index")
    paths = sorted((source / "episodes").glob("*/transcript.md"))
    if limit is not None:
        paths = paths[:limit]
    if not paths:
        raise SystemExit(f"no transcripts under {source / 'episodes'}")

    print(f"ingesting {len(paths)} episodes from {source}", flush=True)
    loaded = 0
    with psycopg.connect(settings.database_url) as conn:
        for path in paths:
            meta, body = parse_transcript(path)
            n = load_episode(
                conn,
                meta,
                body,
                tags.get(path.parent.name, []),
                contextualize_chunks=contextualize_chunks,
            )
            loaded += n
            print(f"  {path.parent.name}: {n} chunks", flush=True)
    print(f"done: {loaded} chunks", flush=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest Lenny's Podcast transcripts")
    parser.add_argument("--limit", type=int, default=None, help="ingest only N episodes (debug)")
    parser.add_argument(
        "--contextualize",
        action="store_true",
        help="LLM episode prefixes (Groq, else Ollama) then re-embed. Default is a title/guest template.",
    )
    args = parser.parse_args(argv)
    try:
        run(limit=args.limit, contextualize_chunks=args.contextualize)
    except EmbedError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main(sys.argv[1:])
