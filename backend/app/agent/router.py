BRIEF_HINTS = (
    "growth brief",
    "experiment brief",
    "experiment doc",
    "growth experiment",
    "write a brief",
    "write me a brief",
)
ESSAY_HINTS = (
    "write an essay",
    "write me an essay",
    "ship 30",
    "ship30",
    "essay on",
    "essay about",
)


def route(text: str) -> str:
    lowered = text.lower()
    if any(hint in lowered for hint in BRIEF_HINTS):
        return "growth_brief"
    if any(hint in lowered for hint in ESSAY_HINTS):
        return "ship30_essay"
    return "qa"
