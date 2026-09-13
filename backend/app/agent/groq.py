import time

import httpx

from app.errors import ModelRateLimitedError, ModelTimeoutError, ModelUnavailableError
from app.settings import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
RATE_LIMIT_WAIT_SECONDS = 2
last_reasoning = ""


def complete(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    if not settings.groq_api_key:
        raise ModelUnavailableError("GROQ_API_KEY is missing")
    payload: dict = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": temperature,
        # ponytail: gpt-oss spends completion tokens on reasoning first; low effort leaves room for the actual answer
        "reasoning_effort": "low",
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    timeout = httpx.Timeout(settings.model_timeout_seconds)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json=payload,
            )
            if response.status_code == 429:
                time.sleep(RATE_LIMIT_WAIT_SECONDS)
                response = client.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    json=payload,
                )
    except httpx.TimeoutException as exc:
        raise ModelTimeoutError(
            "The model didn't respond in time. Retry, or switch provider."
        ) from exc
    except httpx.ConnectError as exc:
        raise ModelUnavailableError("Cloud model is unreachable.") from exc

    if response.status_code == 429:
        raise ModelRateLimitedError("Cloud model is rate-limited. Wait a moment and retry.")
    if response.status_code >= 400:
        raise ModelUnavailableError(f"Groq error {response.status_code}: {response.text[:200]}")
    global last_reasoning
    message = response.json()["choices"][0]["message"]
    last_reasoning = (message.get("reasoning") or message.get("reasoning_content") or "").strip()
    content = message.get("content")
    if not content:
        raise ModelUnavailableError("Groq returned an empty response.")
    return content
