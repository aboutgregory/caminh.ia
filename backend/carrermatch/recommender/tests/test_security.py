"""Sprint 1 — controles de segurança: erros sem stack trace, JWT, CORS, limites de input."""

import time
import uuid

import jwt
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from carrermatch.api.auth import AuthUser, get_current_user, require_auth
from carrermatch.config import Settings, get_settings
from carrermatch.main import create_app
from carrermatch.recommender.models.domain import MAX_EXPERIENCE_CHARS, Experience

SECRET = "test-secret-only-for-unit-tests-0123456789"  # pragma: allowlist secret
ORIGIN = "http://localhost:5173"


def make_token(**overrides) -> str:
    claims = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "exp": int(time.time()) + 600,
        "email": "pessoa@exemplo.com",
    }
    claims.update(overrides)
    return jwt.encode(claims, overrides.pop("_key", SECRET), algorithm="HS256")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:x@127.0.0.1:1/none")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("CORS_ORIGINS", ORIGIN)
    get_settings.cache_clear()
    app = create_app()

    class Echo(BaseModel):
        texto: str

    @app.get("/_test/boom")
    async def boom():
        raise RuntimeError("detalhe interno: senha=hunter2 em /srv/app/db.py linha 42")

    @app.get("/_test/private")
    async def private(user: AuthUser = Depends(require_auth)):
        return {"id": str(user.id)}

    @app.get("/_test/optional")
    async def optional(user: AuthUser | None = Depends(get_current_user)):
        return {"anon": user is None}

    @app.post("/_test/echo")
    async def echo(body: Echo):
        return body

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    get_settings.cache_clear()


class TestErrorHandling:
    def test_500_is_generic_with_correlation_id(self, client):
        resp = client.get("/_test/boom")
        assert resp.status_code == 500
        body = resp.json()
        assert set(body) == {"error", "correlation_id"}
        for leak in ("hunter2", "Traceback", "RuntimeError", "db.py"):
            assert leak not in resp.text
        assert resp.headers["X-Request-ID"] == body["correlation_id"]

    def test_valid_request_id_is_propagated(self, client):
        resp = client.get("/health", headers={"X-Request-ID": "abc12345-req"})
        assert resp.headers["X-Request-ID"] == "abc12345-req"

    def test_malicious_request_id_is_replaced(self, client):
        resp = client.get("/health", headers={"X-Request-ID": "x\r\nSet-Cookie: a=b"})
        assert "Set-Cookie" not in resp.headers.get("X-Request-ID", "")

    def test_validation_error_does_not_echo_input(self, client):
        resp = client.post("/_test/echo", json={"texto": 123456789, "extra_pii": "joao@empresa.com"})
        # texto numérico → 422; o valor enviado não volta na resposta
        assert resp.status_code == 422
        assert "123456789" not in resp.text
        assert "joao@empresa.com" not in resp.text
        assert resp.json()["detalhes"][0]["campo"] == "texto"

    def test_security_headers(self, client):
        resp = client.get("/health")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["Cache-Control"] == "no-store"


class TestAuth:
    def test_anonymous_allowed_on_optional_route(self, client):  # RN-06
        assert client.get("/_test/optional").json() == {"anon": True}

    def test_private_route_requires_token(self, client):  # RN-08
        resp = client.get("/_test/private")
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_valid_token(self, client):
        sub = str(uuid.uuid4())
        resp = client.get("/_test/private", headers={"Authorization": f"Bearer {make_token(sub=sub)}"})
        assert resp.status_code == 200
        assert resp.json() == {"id": sub}

    @pytest.mark.parametrize(
        "token",
        [
            pytest.param(lambda: make_token(exp=int(time.time()) - 10), id="expirado"),
            pytest.param(lambda: make_token(aud="anon"), id="audience-errada"),
            pytest.param(lambda: make_token(_key="outra-chave-qualquer-0123456789abcdef"), id="assinatura-errada"),
            pytest.param(lambda: make_token(sub="nao-e-uuid"), id="sub-invalido"),
            pytest.param(lambda: "abc.def.ghi", id="lixo"),
            pytest.param(
                lambda: jwt.encode(
                    {"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60}, None, algorithm="none"
                ),
                id="alg-none",
            ),
        ],
    )
    def test_invalid_tokens_rejected(self, client, token):
        resp = client.get("/_test/private", headers={"Authorization": f"Bearer {token()}"})
        assert resp.status_code == 401

    def test_bad_token_on_optional_route_is_401_not_anonymous(self, client):
        resp = client.get("/_test/optional", headers={"Authorization": "Bearer abc.def.ghi"})
        assert resp.status_code == 401

    def test_token_in_query_string_is_ignored(self, client):
        resp = client.get(f"/_test/private?access_token={make_token()}")
        assert resp.status_code == 401


class TestCors:
    def test_allowed_origin(self, client):
        resp = client.options(
            "/health", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET"}
        )
        assert resp.headers.get("access-control-allow-origin") == ORIGIN

    def test_foreign_origin_not_allowed(self, client):
        resp = client.options(
            "/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
        )
        assert "access-control-allow-origin" not in resp.headers

    def test_wildcard_rejected_in_production(self):
        with pytest.raises(ValidationError):
            Settings(environment="production", cors_origins="*", _env_file=None)

    def test_http_origin_rejected_in_production(self):
        with pytest.raises(ValidationError):
            Settings(environment="production", cors_origins="http://caminhia.app", _env_file=None)

    def test_docs_hidden_in_production(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("CORS_ORIGINS", "https://caminhia.vercel.app")
        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:x@127.0.0.1:1/none")
        get_settings.cache_clear()
        with TestClient(create_app()) as c:
            assert c.get("/docs").status_code == 404
            assert c.get("/openapi.json").status_code == 404
        get_settings.cache_clear()


def test_experience_length_limit():
    with pytest.raises(ValueError):
        Experience(raw_text="a" * (MAX_EXPERIENCE_CHARS + 1))
    assert Experience(raw_text="a" * MAX_EXPERIENCE_CHARS)
