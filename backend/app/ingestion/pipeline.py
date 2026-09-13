from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import httpx
import psycopg
import yaml

from app.errors import EmbedError
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


def episode_prefix(guest: str, title: str) -> str:
    return f'This excerpt is from Lenny\'s Podcast episode "{title}" with guest {guest}.'


def contextualize(chunk: str, guest: str, title: str) -> str:
    url = settings.ollama_base_url.rstrip("/") + "/api/generate"
    prompt = (
        f"In one sentence, situate this excerpt in Lenny's interview with {guest} "
        f"about {title}. No preamble.\n\nExcerpt:\n{chunk[:600]}"
    )
    timeout = httpx.Timeout(settings.model_timeout_seconds)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            url,
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
    return (response.json().get("response") or "").strip()


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

    prefixes = [
        contextualize(chunk, guest, title) if contextualize_chunks else episode_prefix(guest, title)
        for chunk in chunks
    ]
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


def run(limit: int | None, contextualize_chunks: bool) -> None:
    root = repo_root()
    source = root / "data" / "transcripts"
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
        help="LLM chunk prefixes via Ollama (slow). Default is a one-line title/guest template.",
    )
    args = parser.parse_args(argv)
    try:
        run(limit=args.limit, contextualize_chunks=args.contextualize)
    except EmbedError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main(sys.argv[1:])
