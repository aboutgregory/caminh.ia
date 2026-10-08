"""Direitos do titular (LGPD art. 18): acesso/portabilidade e exclusão definitiva.

- GET /users/me/data → exportação JSON de tudo o que existe sobre o usuário.
- DELETE /users/me  → hard delete em todas as tabelas + revogação no Supabase Auth.
  Hard delete, não soft delete: o dado deixa de existir (seg. v2 §3.3).
  A trilha de auditoria registra só contagens, nunca quem foi excluído.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from carrermatch.api.auth import AuthUser, require_auth
from carrermatch.api.deps import AppServices, get_services
from carrermatch.api.rate_limit import rate_limit

log = logging.getLogger("carrermatch.users")
router = APIRouter(prefix="/users", tags=["conta (LGPD)"])


def _accounts(services: AppServices):
    if services.accounts is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço temporariamente indisponível.")
    return services.accounts


@router.get("/me/data", dependencies=[Depends(rate_limit("account"))])
async def export_my_data(
    user: AuthUser = Depends(require_auth),
    services: AppServices = Depends(get_services),
) -> JSONResponse:
    accounts = _accounts(services)
    data = await accounts.export_user_data(user.id)
    if data is None:
        # login feito, mas nada salvo: a resposta honesta é "não guardamos nada seu"
        data = {"conta": None, "experiencias": [], "recomendacoes": [], "mentorias": [], "eventos": []}
    await accounts.audit("data_exported", {"vazio": data["conta"] is None})
    return JSONResponse(
        jsonable_encoder(data),
        headers={"Content-Disposition": 'attachment; filename="caminhia-meus-dados.json"'},
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(rate_limit("account"))])
async def delete_my_account(
    user: AuthUser = Depends(require_auth),
    services: AppServices = Depends(get_services),
) -> Response:
    accounts = _accounts(services)
    counts = await accounts.delete_user(user.id)   # transação + auditoria 'account_deleted'
    revoked = await services.auth_admin.delete_user(user.id)
    if not revoked:
        # dados já apagados; a pendência fica registrada para reprocessar a revogação
        await accounts.audit("auth_revocation_failed", {"havia_dados": counts is not None})
        log.error("exclusão concluída no banco, mas revogação no Supabase Auth falhou")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
