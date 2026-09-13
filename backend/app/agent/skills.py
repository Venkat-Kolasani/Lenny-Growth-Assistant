from app.agent import growth_brief, ship30
from app.agent.qa import INSUFFICIENT, answer
from app.retrieval.search import RetrievedChunk


def first_heading(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()[:120]
    return "Untitled"


def run(
    skill: str,
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]],
    provider: str,
) -> tuple[str, str | None, str | None]:
    """Return (chat text, artifact title, artifact markdown)."""
    if skill == "qa":
        return answer(question, chunks, history, provider=provider), None, None
    if not chunks:
        return INSUFFICIENT, None, None
    if skill == "ship30_essay":
        markdown = ship30.draft(question, chunks, history, provider)
        title = first_heading(markdown)
        chat = f"Drafted a Ship 30/30 essay — {title}. It is in the Artifact Viewer."
        return chat, title, markdown
    markdown = growth_brief.draft(question, chunks, history, provider)
    title = first_heading(markdown)
    chat = f"Drafted a growth brief — {title}. It is in the Artifact Viewer."
    return chat, title, markdown
