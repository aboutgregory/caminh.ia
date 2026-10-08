"""Integrações externas da conta: revogação no Supabase Auth e aviso ao mentor.

- `SupabaseAuthAdmin.delete_user`: remove o usuário do Supabase Auth (Admin API,
  service role). Sem a chave configurada, `NullAuthAdmin` registra que a
  revogação não aconteceu, para o fluxo de exclusão auditar a pendência.
- `MentorNotifier`: o envio de e-mail (Resend) é do antigravity, que implementa
  `services/email_service.py` com esta interface. Até lá, `LoggingNotifier`
  só registra o id da solicitação, sem e-mail nem texto.
"""

from __future__ import annotations

import logging
from typing import Protocol
from uuid import UUID

import httpx

log = logging.getLogger("carrermatch.account")


class AuthAdmin(Protocol):
    async def delete_user(self, auth_id: UUID) -> bool: ...


class NullAuthAdmin:
    async def delete_user(self, auth_id: UUID) -> bool:
        log.warning("SUPABASE_SERVICE_ROLE_KEY ausente: usuário não removido do Supabase Auth")
        return False


class SupabaseAuthAdmin:
    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        timeout_s: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,   # injetável em testes
    ) -> None:
        self._base = supabase_url.rstrip("/") + "/auth/v1/admin/users/"
        self._headers = {"apikey": service_role_key, "Authorization": f"Bearer {service_role_key}"}
        self._timeout = timeout_s
        self._transport = transport

    async def delete_user(self, auth_id: UUID) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                resp = await client.delete(self._base + str(auth_id), headers=self._headers)
        except httpx.HTTPError as exc:
            log.error("falha ao revogar usuário no Supabase Auth: %s", type(exc).__name__)
            return False
        if resp.status_code in (200, 204, 404):  # 404: já não existia — objetivo atingido
            return True
        log.error("Supabase Auth recusou a revogação: HTTP %s", resp.status_code)
        return False


class MentorNotifier(Protocol):
    async def notify_mentor_request(self, match_id: UUID) -> None: ...


class LoggingNotifier:
    async def notify_mentor_request(self, match_id: UUID) -> None:
        log.info("solicitação de mentoria %s criada (envio de e-mail pendente: Resend/antigravity)", match_id)
