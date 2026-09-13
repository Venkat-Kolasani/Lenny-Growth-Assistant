import httpx
import pytest

from app.agent.groq import complete
from app.agent.qa import INSUFFICIENT, answer
from app.errors import ModelTimeoutError
from app.retrieval.search import RetrievedChunk


def test_empty_retrieval_skips_groq(monkeypatch):
    monkeypatch.setattr("app.agent.qa.complete", lambda *a, **k: "should not run")
    assert answer("what is a north star metric?", [], []) == INSUFFICIENT


def test_groq_timeout_becomes_readable_error(monkeypatch):
    class Boom:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.TimeoutException("slow")

    monkeypatch.setattr("app.agent.groq.settings.groq_api_key", "test-key")
    monkeypatch.setattr("app.agent.groq.httpx.Client", lambda timeout=None: Boom())
    with pytest.raises(ModelTimeoutError, match="didn't respond in time"):
        complete([{"role": "user", "content": "hi"}])


def test_qa_sends_chunks_to_groq(monkeypatch):
    captured = {}

    def fake_complete(provider, messages, **kwargs):
        captured["messages"] = messages
        captured["provider"] = provider
        return "Airbnb hosts matter. — Brian Chesky"

    monkeypatch.setattr("app.agent.qa.complete", fake_complete)
    chunk = RetrievedChunk(
        id="1",
        episode_guest="Brian Chesky",
        episode_title="Brian Chesky’s new playbook",
        youtube_url="https://youtube.com/watch?v=x",
        chunk_text="Be in the details.",
        score=0.9,
    )
    text = answer("how should a CEO run product?", [chunk], [])
    assert "Chesky" in text
    assert captured["provider"] == "groq"
    assert "Excerpts" in captured["messages"][0]["content"]
