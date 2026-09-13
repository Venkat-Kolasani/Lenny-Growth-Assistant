from app.agent.qa import INSUFFICIENT
from app.agent.skills import first_heading, run
from app.retrieval.search import RetrievedChunk

CHUNK = RetrievedChunk(
    id="1",
    episode_guest="Brian Chesky",
    episode_title="Brian Chesky’s new playbook",
    youtube_url="https://youtube.com/watch?v=x",
    chunk_text="Be in the details.",
    score=0.9,
)


def test_first_heading_skips_html_comment():
    md = "<!-- angle: analytical -->\n# Stay in the details\n\nBody."
    assert first_heading(md) == "Stay in the details"


def test_run_qa_with_no_chunks_skips_model():
    text, title, md = run("qa", "what is pmf?", [], [], "groq")
    assert text == INSUFFICIENT
    assert title is None
    assert md is None


def test_run_essay_without_chunks_makes_no_artifact():
    text, title, md = run("ship30_essay", "write an essay on pricing", [], [], "groq")
    assert text == INSUFFICIENT
    assert md is None


def test_run_essay_returns_artifact(monkeypatch):
    monkeypatch.setattr(
        "app.agent.skills.ship30.draft",
        lambda *a, **k: "# The non-obvious pricing essay\n\nHello.",
    )
    text, title, md = run("ship30_essay", "write an essay on pricing", [CHUNK], [], "groq")
    assert title == "The non-obvious pricing essay"
    assert md.startswith("# The")
    assert "Artifact Viewer" in text
