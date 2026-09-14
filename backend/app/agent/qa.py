from app.agent.provider import complete
from app.retrieval.search import RetrievedChunk

INSUFFICIENT = (
    "The transcripts don't cover this clearly enough to answer without guessing. "
    "Try a product, growth, or PM topic that showed up on Lenny's Podcast."
)

SYSTEM = """You answer product and growth questions using ONLY the transcript excerpts below.
If the excerpts are not enough, say so. Do not invent guests, episodes, or claims.
After a grounded claim, mention the guest name in the sentence.
Keep the answer concise.
Answer only the latest user question. Do not revisit earlier turns unless asked."""

# llama3.2:3b loses the thread when the system prompt + history get long; keep local context tight.
_OLLAMA_HISTORY = 2
_CLOUD_HISTORY = 6
_OLLAMA_EXCERPT_CHARS = 700
_OLLAMA_EXCERPT_CHUNKS = 6
_CLOUD_EXCERPT_CHARS = 1200


def history_window(provider: str) -> int:
    return _OLLAMA_HISTORY if provider == "ollama" else _CLOUD_HISTORY


def format_excerpts(
    chunks: list[RetrievedChunk],
    *,
    provider: str = "groq",
) -> str:
    max_chars = _OLLAMA_EXCERPT_CHARS if provider == "ollama" else _CLOUD_EXCERPT_CHARS
    selected = chunks[:_OLLAMA_EXCERPT_CHUNKS] if provider == "ollama" else chunks
    numbered = []
    for i, chunk in enumerate(selected, start=1):
        numbered.append(
            f"[{i}] {chunk.episode_guest} — {chunk.episode_title}\n{chunk.chunk_text[:max_chars]}"
        )
    return "\n\n".join(numbered)


def answer(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]],
    provider: str = "groq",
    *,
    anthropic_api_key: str | None = None,
) -> str:
    if not chunks:
        return INSUFFICIENT
    window = history_window(provider)
    messages = [
        {
            "role": "system",
            "content": SYSTEM + "\n\nExcerpts:\n" + format_excerpts(chunks, provider=provider),
        },
        *history[-window:],
        {"role": "user", "content": question},
    ]
    return complete(provider, messages, anthropic_api_key=anthropic_api_key)
