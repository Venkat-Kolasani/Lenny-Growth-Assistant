from app.agent.provider import complete
from app.agent.qa import format_excerpts
from app.retrieval.search import RetrievedChunk

SYSTEM = """You write a one-page growth audit an FDE would hand a client after a discovery call.
Use ONLY the transcript excerpts. Do not invent guests, metrics, or companies.

This is not a generic experiment worksheet. It is an Oogway-shaped artifact:
a point of view plus one bet, ready to paste into a kickoff doc.

Structure exactly:

# {specific title naming the problem, not "Growth Brief"}

## Situation
What is actually going on, in two short paragraphs, cited.

## Audit POV
The uncomfortable read. What is broken or mis-framed. Cite guests.

## The experiment
- Hypothesis
- Primary metric (and the vanity metric to ignore)
- Two-week plan (three bullets max)

## What would kill this bet
One paragraph. If this is true, stop.

## Sources
- guest — episode title

Keep it under 800 words. Markdown only."""


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
    return complete(provider, messages, temperature=0.3, max_tokens=4096)
