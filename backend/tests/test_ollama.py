import httpx
import pytest

from app.agent.ollama import UNAVAILABLE, complete
from app.errors import ModelTimeoutError, ModelUnavailableError


class _Boom:
    def __init__(self, exc):
        self.exc = exc

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        raise self.exc


def test_ollama_timeout_is_readable(monkeypatch):
    monkeypatch.setattr("app.agent.ollama.httpx.Client", lambda timeout=None: _Boom(httpx.TimeoutException("slow")))
    with pytest.raises(ModelTimeoutError, match="didn't respond in time"):
        complete([{"role": "user", "content": "hi"}])


def test_ollama_down_is_readable(monkeypatch):
    monkeypatch.setattr("app.agent.ollama.httpx.Client", lambda timeout=None: _Boom(httpx.ConnectError("refused")))
    with pytest.raises(ModelUnavailableError, match="start Ollama"):
        complete([{"role": "user", "content": "hi"}])
    assert "Local model" in UNAVAILABLE
