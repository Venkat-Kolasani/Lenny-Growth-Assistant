import httpx

from app.errors import ModelTimeoutError, ModelUnavailableError
from app.settings import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def complete(messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
    if not settings.groq_api_key:
        raise ModelUnavailableError("GROQ_API_KEY is missing")
    timeout = httpx.Timeout(settings.model_timeout_seconds)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                },
            )
    except httpx.TimeoutException as exc:
        raise ModelTimeoutError(
            "The model didn't respond in time — retry, or switch provider."
        ) from exc
    except httpx.ConnectError as exc:
        raise ModelUnavailableError("Cloud model is unreachable.") from exc

    if response.status_code == 429:
        raise ModelUnavailableError("Cloud model is rate-limited. Wait a moment and retry.")
    if response.status_code >= 400:
        raise ModelUnavailableError(f"Groq error {response.status_code}: {response.text[:200]}")
    content = response.json()["choices"][0]["message"]["content"]
    if not content:
        raise ModelUnavailableError("Groq returned an empty response.")
    return content
