from app.ingestion.chunk import chunk_text
from app.ingestion.pipeline import episode_prefix


def test_chunk_snaps_to_sentences_and_overlaps():
    sentences = [f"This is sentence number {i} about activation metrics." for i in range(80)]
    text = " ".join(sentences)
    chunks = chunk_text(text, target_chars=400, overlap_ratio=0.2)
    assert len(chunks) >= 2
    assert all(chunk.endswith(".") for chunk in chunks)
    assert chunks[0][-40:] in chunks[1]


def test_episode_prefix_names_guest_and_title():
    text = episode_prefix("Aishwarya Naresh Reganti", "Why most AI products fail")
    assert "Aishwarya Naresh Reganti" in text
    assert "Why most AI products fail" in text
