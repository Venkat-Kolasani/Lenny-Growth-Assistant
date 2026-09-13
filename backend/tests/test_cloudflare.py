import httpx
import pytest

from app.agent.cloudflare import UNAVAILABLE, complete
from app.errors import ModelTimeoutError, ModelUnavailableError


def test_cloudflare_unconfigured():
    with pytest.raises(ModelUnavailableError, match="isn't configured"):
        complete([{"role": "user", "content": "hi"}])
    assert "failover" in UNAVAILABLE


def test_cloudflare_timeout(monkeypatch):
    class Boom:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.TimeoutException("slow")

    monkeypatch.setattr("app.agent.cloudflare.settings.cloudflare_account_id", "acct")
    monkeypatch.setattr("app.agent.cloudflare.settings.cloudflare_api_token", "tok")
    monkeypatch.setattr("app.agent.cloudflare.httpx.Client", lambda timeout=None: Boom())
    with pytest.raises(ModelTimeoutError, match="didn't respond in time"):
        complete([{"role": "user", "content": "hi"}])
