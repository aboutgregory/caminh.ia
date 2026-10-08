"""FastAPI app — lifespan gerencia o pool asyncpg."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anthropic
import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from carrermatch.api.deps import AppServices
from carrermatch.api.errors import install_error_handling
from carrermatch.api.rate_limit import SlidingWindowLimiter
from carrermatch.api.routes import events, mentors, recommendations, users
from carrermatch.config import get_settings
from carrermatch.db.seeds.loader import seed_repository
from carrermatch.recommender.engines.hybrid import HybridPipeline
from carrermatch.recommender.engines.mentor_matcher import MentorMatcher
from carrermatch.recommender.repositories.account_repo import PostgresAccountRepository
from carrermatch.recommender.repositories.recommender_repo import PostgresRecommenderRepository
from carrermatch.recommender.repositories.write_repo import (
    InMemoryEventRepository,
    PostgresEventRepository,
    PostgresRecommendationStore,
)
from carrermatch.recommender.services.account_services import NullAuthAdmin, SupabaseAuthAdmin
from carrermatch.recommender.services.behavioral_service import BehavioralEventCollector
from carrermatch.recommender.services.claude_service import ClaudeDescriptionService

log = logging.getLogger("carrermatch")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.pool = None
    try:
        if not settings.database_url:
            raise OSError("DATABASE_URL vazio — rodando sem banco")
        app.state.pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max,
            command_timeout=10,
            timeout=10,
            statement_cache_size=settings.db_statement_cache_size,
            # tabelas vivem no schema `app` (não exposto pelo PostgREST do Supabase)
            server_settings={"search_path": "app,public", "application_name": "caminhia-api"},
        )
    except (OSError, asyncpg.PostgresError) as exc:
        # sobe mesmo sem banco: /health reporta "degraded" em vez do processo morrer
        log.error("falha ao conectar no PostgreSQL: %s", type(exc).__name__)

    claude_client = (
        anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value(),
            timeout=settings.claude_timeout_s,
            max_retries=2,  # SDK repete 408/409/429/5xx com backoff exponencial
        )
        if settings.anthropic_api_key and settings.anthropic_api_key.get_secret_value()
        else None
    )
    if claude_client is None:
        log.warning("ANTHROPIC_API_KEY ausente: descrições usarão o fallback local")
    app.state.services = await build_services(app.state.pool, claude_client)
    try:
        yield
    finally:
        if claude_client is not None:
            await claude_client.close()
        if app.state.pool is not None:
            await app.state.pool.close()


async def build_services(pool: asyncpg.Pool | None, claude_client: anthropic.AsyncAnthropic | None) -> AppServices:
    settings = get_settings()
    pipeline: HybridPipeline | None = None
    if pool is not None:
        try:
            pipeline = await HybridPipeline.from_repository(PostgresRecommenderRepository(pool))
            if not pipeline.skill_names:
                log.warning("vocabulário vazio no banco (seed não aplicado?)")
                pipeline = None
        except asyncpg.PostgresError as exc:
            log.error("falha ao carregar vocabulário do banco: %s", type(exc).__name__)
    if pipeline is None and not settings.is_production:
        # desenvolvimento sem banco: usa o seed curado em memória
        log.warning("usando vocabulário do seed em memória (desenvolvimento)")
        pipeline = await HybridPipeline.from_repository(seed_repository())

    claude = None
    if pipeline is not None:
        claude = ClaudeDescriptionService(
            claude_client,
            model=settings.claude_model,
            skill_names=pipeline.skill_names,
            sector_names=pipeline.sector_names,
            timeout_s=settings.claude_timeout_s,
            max_tokens=settings.claude_max_tokens,
        )
    return AppServices(
        pipeline=pipeline,
        claude=claude,
        events=BehavioralEventCollector(PostgresEventRepository(pool) if pool else InMemoryEventRepository()),
        store=PostgresRecommendationStore(pool) if pool else None,
        accounts=PostgresAccountRepository(pool) if pool else None,
        mentor_matcher=MentorMatcher(pipeline.idf if pipeline else {}),
        auth_admin=(
            SupabaseAuthAdmin(settings.supabase_url, settings.supabase_service_role_key.get_secret_value())
            if settings.supabase_url and settings.supabase_service_role_key
            and settings.supabase_service_role_key.get_secret_value()
            else NullAuthAdmin()
        ),
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="caminh.ia API",
        version="0.1.0",
        lifespan=lifespan,
        # documentação interativa só fora de produção (reduz superfície exposta)
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    install_error_handling(app)
    # CORS restrito (nunca "*"; validado em Settings). allow_credentials=False:
    # a autenticação vai no header Authorization, não em cookie.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Session-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    app.state.limiters = {
        "recommendations": SlidingWindowLimiter(settings.rate_limit_recommendations),
        "events": SlidingWindowLimiter(settings.rate_limit_events),
        "mentor_search": SlidingWindowLimiter(settings.rate_limit_mentor_search),
        "mentor_requests": SlidingWindowLimiter(settings.rate_limit_mentor_requests),
        "account": SlidingWindowLimiter(settings.rate_limit_account),
    }
    app.include_router(recommendations.router)
    app.include_router(events.router)
    app.include_router(mentors.router)
    app.include_router(users.router)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/health")
    async def health(request: Request) -> JSONResponse:
        pool: asyncpg.Pool | None = request.app.state.pool
        db_ok = False
        transitions = 0
        if pool is not None:
            try:
                transitions = await pool.fetchval("SELECT count(*) FROM career_transitions")
                db_ok = True
            except asyncpg.PostgresError as exc:
                log.warning("health: consulta falhou: %s", exc)
        body = {"status": "ok" if db_ok else "degraded", "database": db_ok, "career_transitions": transitions}
        return JSONResponse(body, status_code=200 if db_ok else 503)

    return app


app = create_app()
