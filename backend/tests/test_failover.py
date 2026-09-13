import httpx
import pytest

from app.agent.groq import complete as groq_complete
from app.agent.provider import complete
from app.errors import ModelRateLimitedError, ModelUnavailableError


class Dummy:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = payload if isinstance(payload, str) else ""

    def json(self):
        return self._payload


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        self.calls += 1
        return self.responses.pop(0)


def test_groq_retries_once_on_429(monkeypatch):
    client = Client(
        [
            Dummy(429, "slow"),
            Dummy(200, {"choices": [{"message": {"content": "ok after wait"}}]}),
        ]
    )
    monkeypatch.setattr("app.agent.groq.settings.groq_api_key", "test-key")
    monkeypatch.setattr("app.agent.groq.time.sleep", lambda s: None)
    monkeypatch.setattr("app.agent.groq.httpx.Client", lambda timeout=None: client)
    assert groq_complete([{"role": "user", "content": "hi"}]) == "ok after wait"
    assert client.calls == 2


def test_groq_429_twice_is_rate_limited(monkeypatch):
    client = Client([Dummy(429, "slow"), Dummy(429, "still slow")])
    monkeypatch.setattr("app.agent.groq.settings.groq_api_key", "test-key")
    monkeypatch.setattr("app.agent.groq.time.sleep", lambda s: None)
    monkeypatch.setattr("app.agent.groq.httpx.Client", lambda timeout=None: client)
    with pytest.raises(ModelRateLimitedError, match="rate-limited"):
        groq_complete([{"role": "user", "content": "hi"}])


def test_groq_429_fails_over_to_cloudflare(monkeypatch):
    monkeypatch.setattr("app.agent.provider.settings.cloudflare_account_id", "acct")
    monkeypatch.setattr("app.agent.provider.settings.cloudflare_api_token", "tok")

    def boom(*args, **kwargs):
        raise ModelRateLimitedError("rate")

    monkeypatch.setattr("app.agent.provider.groq.complete", boom)
    monkeypatch.setattr("app.agent.provider.cloudflare.complete", lambda *a, **k: "from-cf")
    assert complete("groq", [{"role": "user", "content": "hi"}]) == "from-cf"


def test_groq_429_without_cloudflare_stays_unavailable(monkeypatch):
    monkeypatch.setattr("app.agent.provider.settings.cloudflare_account_id", "")
    monkeypatch.setattr("app.agent.provider.settings.cloudflare_api_token", "")

    def boom(*args, **kwargs):
        raise ModelRateLimitedError("rate")

    monkeypatch.setattr("app.agent.provider.groq.complete", boom)
    with pytest.raises(ModelUnavailableError, match="rate-limited"):
        complete("groq", [{"role": "user", "content": "hi"}])
