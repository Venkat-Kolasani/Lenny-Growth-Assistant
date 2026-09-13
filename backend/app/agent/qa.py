from app.agent.provider import complete
from app.retrieval.search import RetrievedChunk

INSUFFICIENT = (
    "The transcripts don't cover this clearly enough to answer without guessing. "
    "Try a product, growth, or PM topic that showed up on Lenny's Podcast."
)

SYSTEM = """You answer product and growth questions using ONLY the transcript excerpts below.
If the excerpts are not enough, say so. Do not invent guests, episodes, or claims.
After a grounded claim, mention the guest name in the sentence.
Keep the answer concise."""


def format_excerpts(chunks: list[RetrievedChunk]) -> str:
    numbered = []
    for i, chunk in enumerate(chunks, start=1):
        numbered.append(
            f"[{i}] {chunk.episode_guest} — {chunk.episode_title}\n{chunk.chunk_text[:1200]}"
        )
    return "\n\n".join(numbered)


def answer(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]],
    provider: str = "groq",
) -> str:
    if not chunks:
        return INSUFFICIENT
    messages = [
        {"role": "system", "content": SYSTEM + "\n\nExcerpts:\n" + format_excerpts(chunks)},
        *history[-6:],
        {"role": "user", "content": question},
    ]
    return complete(provider, messages)
