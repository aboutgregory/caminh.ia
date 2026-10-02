"""FastAPI app — lifespan gerencia o pool asyncpg."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from carrermatch.config import get_settings

log = logging.getLogger("carrermatch")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.pool = None
    try:
        app.state.pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max,
            command_timeout=10,
        )
    except (OSError, asyncpg.PostgresError) as exc:
        # sobe mesmo sem banco: /health reporta "degraded" em vez do processo morrer
        log.error("falha ao conectar no PostgreSQL: %s", exc)
    try:
        yield
    finally:
        if app.state.pool is not None:
            await app.state.pool.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="caminh.ia API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

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
