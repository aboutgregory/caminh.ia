"""Autenticação — validação local de JWT emitido pelo Supabase Auth.

- `get_current_user`: opcional. Sem header → None (beta anônimo, RN-06).
  Header presente mas inválido/expirado → 401 (nunca "rebaixa" para anônimo,
  para não mascarar token adulterado).
- `require_auth`: rotas que exigem login (mentoria, salvamento — RN-07/RN-08).

Algoritmos aceitos são fixos (sem `alg: none`, sem confusão HS/RS):
  - HS256 com SUPABASE_JWT_SECRET (chave legada);
  - ES256/RS256 via JWKS em {SUPABASE_URL}/auth/v1/.well-known/jwks.json
    (chaves assimétricas — padrão dos projetos Supabase novos).
O token só é aceito do header Authorization: Bearer, nunca de query string.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from carrermatch.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)
ASYMMETRIC_ALGS = ("ES256", "RS256")
_UNAUTHORIZED = {"WWW-Authenticate": "Bearer"}


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: UUID
    email: str | None
    claims: dict


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=3600)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detail, headers=_UNAUTHORIZED)


def decode_token(token: str, settings: Settings) -> AuthUser:
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.InvalidTokenError:
        raise _unauthorized("Token inválido.") from None

    options = {"require": ["exp", "sub", "aud"]}
    try:
        if alg == "HS256":
            if settings.supabase_jwt_secret is None:
                raise _unauthorized("Autenticação indisponível.")
            claims = jwt.decode(
                token,
                settings.supabase_jwt_secret.get_secret_value(),
                algorithms=["HS256"],
                audience=settings.supabase_jwt_audience,
                options=options,
            )
        elif alg in ASYMMETRIC_ALGS:
            if not settings.supabase_url:
                raise _unauthorized("Autenticação indisponível.")
            jwks_url = settings.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
            key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token, key, algorithms=list(ASYMMETRIC_ALGS), audience=settings.supabase_jwt_audience, options=options
            )
        else:
            raise _unauthorized("Token inválido.")
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Sessão expirada. Faça login novamente.") from None
    except (jwt.InvalidTokenError, jwt.PyJWKClientError):
        raise _unauthorized("Token inválido.") from None

    try:
        user_id = UUID(claims["sub"])
    except (ValueError, TypeError):
        raise _unauthorized("Token inválido.") from None
    return AuthUser(id=user_id, email=claims.get("email"), claims=claims)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> AuthUser | None:
    if credentials is None:
        return None
    return decode_token(credentials.credentials, settings)


async def require_auth(user: AuthUser | None = Depends(get_current_user)) -> AuthUser:
    if user is None:
        raise _unauthorized("Autenticação necessária para esta ação.")
    return user
