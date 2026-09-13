import httpx

from app.errors import ModelTimeoutError, ModelUnavailableError
from app.settings import settings

UNAVAILABLE = "Cloudflare failover isn't configured."


def complete(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
        raise ModelUnavailableError(UNAVAILABLE)
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}"
        f"/ai/run/{settings.cloudflare_model}"
    )
    payload: dict = {"messages": messages}
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    timeout = httpx.Timeout(settings.model_timeout_seconds)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise ModelTimeoutError(
            "The model didn't respond in time. Retry, or switch provider."
        ) from exc
    except httpx.ConnectError as exc:
        raise ModelUnavailableError("Cloudflare is unreachable.") from exc

    if response.status_code >= 400:
        raise ModelUnavailableError(f"Cloudflare error {response.status_code}: {response.text[:200]}")
    body = response.json()
    result = body.get("result") or {}
    content = result.get("response")
    if not content and isinstance(result.get("message"), dict):
        content = result["message"].get("content")
    if not content:
        raise ModelUnavailableError("Cloudflare returned an empty response.")
    return content
