from anthropic import Anthropic, APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from app.errors import ModelRateLimitedError, ModelTimeoutError, ModelUnavailableError
from app.settings import settings

UNAVAILABLE = "Anthropic is not configured. Add ANTHROPIC_API_KEY to .env, or switch to Groq or Ollama."


def _split(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system_parts: list[str] = []
    turns: list[dict[str, str]] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system":
            system_parts.append(content)
        elif role in {"user", "assistant"}:
            turns.append({"role": role, "content": content})
    if not turns or turns[0]["role"] != "user":
        turns.insert(0, {"role": "user", "content": "Continue."})
    return "\n\n".join(system_parts), turns


def complete(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    if not settings.anthropic_api_key:
        raise ModelUnavailableError(UNAVAILABLE)
    system, turns = _split(messages)
    client = Anthropic(api_key=settings.anthropic_api_key, timeout=settings.model_timeout_seconds)
    payload: dict = {
        "model": settings.anthropic_model,
        "messages": turns,
        "temperature": temperature,
        "max_tokens": max_tokens or 4096,
    }
    if system:
        payload["system"] = system
    try:
        response = client.messages.create(**payload)
    except APITimeoutError as exc:
        raise ModelTimeoutError(
            "The model didn't respond in time. Retry, or switch provider."
        ) from exc
    except RateLimitError as exc:
        raise ModelRateLimitedError("Cloud model is rate-limited. Wait a moment and retry.") from exc
    except APIConnectionError as exc:
        raise ModelUnavailableError("Cloud model is unreachable.") from exc
    except APIStatusError as exc:
        raise ModelUnavailableError(f"Anthropic error {exc.status_code}: {str(exc)[:200]}") from exc

    parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
    text = "".join(parts).strip()
    if not text:
        raise ModelUnavailableError("Anthropic returned an empty response.")
    return text
