import re

TARGET_CHARS = 3200  # ~800 tokens at ~4 chars/token
OVERLAP_RATIO = 0.15
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, target_chars: int = TARGET_CHARS, overlap_ratio: float = OVERLAP_RATIO) -> list[str]:
    sentences = [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:
        return []

    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    overlap_chars = int(target_chars * overlap_ratio)

    def flush() -> None:
        nonlocal buf, size
        if not buf:
            return
        chunks.append(" ".join(buf))
        kept: list[str] = []
        kept_size = 0
        for sentence in reversed(buf):
            if kept_size >= overlap_chars:
                break
            kept.append(sentence)
            kept_size += len(sentence) + 1
        buf = list(reversed(kept))
        size = sum(len(s) + 1 for s in buf)

    for sentence in sentences:
        extra = len(sentence) + 1
        if buf and size + extra > target_chars:
            flush()
        buf.append(sentence)
        size += extra
    if buf:
        chunks.append(" ".join(buf))
    return [c for c in chunks if len(c) >= 200]
