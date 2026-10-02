"""Configuração via variáveis de ambiente / backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="postgresql://postgres@localhost:5432/caminhia")
    db_pool_min: int = 1
    db_pool_max: int = 10

    anthropic_api_key: SecretStr | None = None
    claude_model: str = "claude-sonnet-5-5"
    claude_temperature: float = 0.7
    claude_max_tokens: int = 4000
    claude_timeout_s: float = 15.0

    # lista separada por vírgula; nunca "*" em produção (TRD §10)
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
