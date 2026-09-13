from app.ingestion.chunk import chunk_text


def test_chunk_snaps_to_sentences_and_overlaps():
    sentences = [f"This is sentence number {i} about activation metrics." for i in range(80)]
    text = " ".join(sentences)
    chunks = chunk_text(text, target_chars=400, overlap_ratio=0.2)
    assert len(chunks) >= 2
    assert all(chunk.endswith(".") for chunk in chunks)
    assert chunks[0][-40:] in chunks[1]
