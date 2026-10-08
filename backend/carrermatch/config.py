"""Configuração via variáveis de ambiente / backend/.env.

Nenhuma chave tem valor padrão real: segredos ausentes desligam a funcionalidade
correspondente (ex.: sem SUPABASE_JWT_SECRET/URL, rotas autenticadas respondem
401) em vez de o app subir com credencial embutida.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"

    database_url: str = Field(default="postgresql://postgres@localhost:5432/caminhia")
    db_pool_min: int = 1
    db_pool_max: int = 10
    # 0 obrigatório atrás do pooler em modo transação do Supabase (porta 6543), que não suporta prepared statements
    db_statement_cache_size: int = 100

    anthropic_api_key: SecretStr | None = None
    claude_model: str = "claude-sonnet-5-5"
    # sem claude_temperature: o claude-sonnet-5-5 rejeita temperature diferente do padrão (400)
    claude_max_tokens: int = 3000       # por lote de 3 caminhos (~150 palavras cada + JSON)
    claude_timeout_s: float = 12.0      # por lote; os lotes rodam em paralelo → cabe nos 15 s do TRD

    # rate limiting por IP (gate de go-live #1) — formato "N/unidade;M/unidade"
    rate_limit_recommendations: str = "10/minute;50/hour"
    rate_limit_events: str = "120/minute"
    rate_limit_mentor_search: str = "20/minute"
    rate_limit_mentor_requests: str = "5/hour;20/day"   # anti-spam no formulário de mentoria (seg. v2 risco #8)
    rate_limit_account: str = "10/hour"

    # Supabase Auth — só autenticação (o banco é PostgreSQL próprio)
    supabase_url: str | None = None                 # habilita JWKS (chaves assimétricas ES256/RS256)
    supabase_jwt_secret: SecretStr | None = None    # chave legada HS256
    supabase_jwt_audience: str = "authenticated"
    # só para DELETE /users/me (revogar o usuário no Supabase Auth). nunca vai ao frontend.
    supabase_service_role_key: SecretStr | None = None

    # lista separada por vírgula; aceita CORS_ORIGINS ou ALLOWED_ORIGINS
    cors_origins: str = Field(
        default="http://localhost:5173", validation_alias=AliasChoices("cors_origins", "allowed_origins")
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def _no_wildcard_cors_in_production(self) -> "Settings":
        # TRD §10 / seg. v2 §4.3: CORS nunca "*" em produção
        if self.is_production and any(o == "*" for o in self.cors_origin_list):
            raise ValueError("CORS '*' não é permitido em produção")
        if self.is_production and any(o.startswith("http://") for o in self.cors_origin_list):
            raise ValueError("em produção as origens CORS devem ser https")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
