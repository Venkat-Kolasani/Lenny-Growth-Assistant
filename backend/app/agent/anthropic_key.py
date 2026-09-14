from app.settings import settings


def resolve(header: str | None = None) -> str:
    return (header or "").strip() or (settings.anthropic_api_key or "").strip()
