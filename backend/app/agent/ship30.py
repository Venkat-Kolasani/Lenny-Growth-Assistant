from app.agent.provider import complete
from app.agent.qa import format_excerpts
from app.retrieval.search import RetrievedChunk

SYSTEM = """You write a Ship 30 for 30 online essay using ONLY the transcript excerpts.

Encode the published Ship 30/30 rules, not a vague "write in that style":
1. Name one specific topic in the H1. Do not write about "growth" or "product" in general.
2. State your credibility stance in the first 80 words (why this author, using these guests, is allowed to take this view).
3. Pick exactly one of the four angles: actionable, analytical, aspirational, or anthropological. Name the angle in an HTML comment on the first line: <!-- angle: ... -->
4. Commit to one organizing structure: steps, lessons, or mistakes. Never mix them.
5. Use wheels-and-spokes: one H1, H2 sections, H3 sub-points. No walls of undifferentiated paragraphs.
6. Alternate short and long sentences. A short sentence earns the next long one.
7. Reject the first, most obvious take on the topic. Write the non-obvious one. If the obvious take is "talk to customers," do not write that essay.
8. Target about 1,250 words. Cite guests by name after grounded claims.
9. Do not invent episodes, guests, or numbers that are not in the excerpts.

Return Markdown only. First line after the angle comment is the H1 title."""


def draft(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]],
    provider: str,
) -> str:
    messages = [
        {"role": "system", "content": SYSTEM + "\n\nExcerpts:\n" + format_excerpts(chunks)},
        *history[-6:],
        {"role": "user", "content": question},
    ]
    return complete(provider, messages, temperature=0.4, max_tokens=4096)
