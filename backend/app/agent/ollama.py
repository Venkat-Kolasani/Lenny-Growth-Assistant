import httpx

from app.errors import ModelTimeoutError, ModelUnavailableError
from app.settings import settings

UNAVAILABLE = "Local model isn't running — start Ollama or switch to cloud."


def complete(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    url = settings.ollama_base_url.rstrip("/") + "/api/chat"
    options: dict = {"temperature": temperature}
    if max_tokens is not None:
        options["num_predict"] = max_tokens
    timeout = httpx.Timeout(settings.model_timeout_seconds)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                url,
                json={
                    "model": settings.ollama_model,
                    "messages": messages,
                    "stream": False,
                    "options": options,
                },
            )
    except httpx.TimeoutException as exc:
        raise ModelTimeoutError(
            "The model didn't respond in time — retry, or switch provider."
        ) from exc
    except httpx.ConnectError as exc:
        raise ModelUnavailableError(UNAVAILABLE) from exc

    if response.status_code >= 400:
        raise ModelUnavailableError(f"Ollama error {response.status_code}: {response.text[:200]}")
    content = response.json().get("message", {}).get("content")
    if not content:
        raise ModelUnavailableError("Ollama returned an empty response.")
    return content
