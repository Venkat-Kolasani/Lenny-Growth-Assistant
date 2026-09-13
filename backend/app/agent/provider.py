from app.agent import cloudflare, groq, ollama
from app.errors import ModelRateLimitedError, ModelUnavailableError
from app.settings import settings


def complete(
    provider: str,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    if provider == "ollama":
        return ollama.complete(messages, temperature=temperature, max_tokens=max_tokens)
    if provider == "cloudflare":
        return cloudflare.complete(messages, temperature=temperature, max_tokens=max_tokens)
    try:
        return groq.complete(messages, temperature=temperature, max_tokens=max_tokens)
    except ModelRateLimitedError:
        if settings.cloudflare_account_id and settings.cloudflare_api_token:
            return cloudflare.complete(messages, temperature=temperature, max_tokens=max_tokens)
        raise ModelUnavailableError("Cloud model is rate-limited. Wait a moment and retry.")


def model_for(provider: str) -> str:
    if provider == "ollama":
        return settings.ollama_model
    if provider == "cloudflare":
        return settings.cloudflare_model
    return settings.groq_model
