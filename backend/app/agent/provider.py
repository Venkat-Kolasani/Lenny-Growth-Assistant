from app.agent import groq, ollama
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
    return groq.complete(messages, temperature=temperature, max_tokens=max_tokens)


def model_for(provider: str) -> str:
    if provider == "ollama":
        return settings.ollama_model
    return settings.groq_model
