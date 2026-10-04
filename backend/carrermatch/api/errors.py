"""Tratamento de erros — nenhum stack trace ou detalhe interno chega ao cliente.

- toda requisição recebe um correlation ID (header X-Request-ID, gerado se ausente
  ou inválido) devolvido na resposta e gravado no log;
- exceção não tratada → 500 com mensagem genérica em pt-BR + correlation_id;
- erro de validação → 422 com campo e motivo, SEM ecoar o valor enviado (o
  default do FastAPI devolve o `input`, que pode conter texto pessoal).
"""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("carrermatch.errors")

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
GENERIC_ERROR = "Ocorreu um erro interno. Tente novamente em instantes."


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def install_error_handling(app: FastAPI) -> None:
    @app.middleware("http")
    async def correlation_id(request: Request, call_next):
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        # nunca refletir um header arbitrário (log injection / header injection)
        request.state.request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex[:12]
        try:
            response = await call_next(request)
        except Exception:  # exceções que escapam do roteamento (ex.: em middlewares internos)
            log.exception("[%s] exceção não tratada em %s %s", request.state.request_id, request.method, request.url.path)
            response = JSONResponse(
                {"error": GENERIC_ERROR, "correlation_id": request.state.request_id}, status_code=500
            )
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # mensagens de HTTPException são escritas por nós — seguras para o cliente
        return JSONResponse(
            {"error": exc.detail, "correlation_id": _request_id(request)},
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"campo": ".".join(str(p) for p in err.get("loc", ()) if p != "body"), "motivo": err.get("msg", "")}
            for err in exc.errors()
        ]
        return JSONResponse(
            {"error": "Dados inválidos.", "detalhes": fields, "correlation_id": _request_id(request)},
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("[%s] exceção não tratada em %s %s", _request_id(request), request.method, request.url.path)
        return JSONResponse({"error": GENERIC_ERROR, "correlation_id": _request_id(request)}, status_code=500)
