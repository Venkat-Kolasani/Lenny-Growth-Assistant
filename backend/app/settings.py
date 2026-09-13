from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", ".env"),
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    database_url: str = "postgresql://lenny:lenny@localhost:5432/lenny"
    default_model_provider: str = "groq"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"
    model_timeout_seconds: int = 60
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    anthropic_api_key: str = ""


settings = Settings()
