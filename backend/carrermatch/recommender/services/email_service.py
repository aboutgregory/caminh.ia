"""Serviço de envio de e-mails transacionais (Resend) — RACI Antigravity.

Implementa `MentorNotifier` para notificar mentores quando uma nova solicitação
for recebida via `POST /mentor-matches/{mentor_id}/requests`.

Se `RESEND_API_KEY` não estiver definida, opera em modo seguro/fallback (apenas registra no log),
garantindo que o fluxo da API nunca falhe por indisponibilidade de chave.
"""

from __future__ import annotations

import html
import logging
from uuid import UUID

import asyncpg
import httpx
from pydantic import SecretStr

from carrermatch.recommender.services.account_services import MentorNotifier

log = logging.getLogger("carrermatch.email")

RESEND_ENDPOINT = "https://api.resend.com/emails"

# e-mail segue "bho: sistema visual": Montserrat via Google Fonts (Apple Mail/iOS), Arial no
# Gmail/Outlook; escuros que puxam para o roxo, lavanda como destaque; nada de dourado (campanha).
_FONT = "Montserrat, Arial, sans-serif"


def render_mentor_request_html(mentor_nome: str, mentee_nome: str, cargo: str, message: str) -> str:
    """HTML do aviso ao mentor. TODO campo vindo do banco passa por html.escape: nomes podem vir
    de provedores de login e a mensagem é texto livre do mentorado (injeção de HTML no e-mail)."""
    e = html.escape
    body = e(message).replace("\n", "<br>")
    return (
        '<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">'
        f'<div style="font-family:{_FONT};max-width:600px;margin:0 auto;padding:24px;background-color:#0D0720;'
        'color:#FFFFFF;border-radius:12px;border:1px solid rgba(180,141,218,0.22);">'
        f'<h2 style="color:#FFFFFF;font-weight:700;margin:0 0 8px;">Olá, {e(mentor_nome)}!</h2>'
        '<p style="color:rgba(255,255,255,0.78);font-size:16px;line-height:1.6;margin:0;">'
        f"Você recebeu uma nova solicitação de mentoria de <strong>{e(mentee_nome)}</strong> "
        f'para o caminho de <strong style="color:#B48DDA;">{e(cargo)}</strong>.</p>'
        '<div style="background-color:#1E1040;border-left:3px solid #B48DDA;padding:12px 16px;margin:16px 0;'
        f'border-radius:4px;font-size:16px;line-height:1.6;color:#FFFFFF;">{body}</div>'
        '<p style="color:rgba(255,255,255,0.60);font-size:12px;margin-top:24px;">'
        "Esta mensagem foi intermediada pelo caminh.ia (CarrerMatch by bho:). Seu e-mail não foi compartilhado.</p>"
        "</div>"
    )


def render_mentor_request_text(mentor_nome: str, mentee_nome: str, cargo: str, message: str) -> str:
    """Versão texto puro (entregabilidade e leitores de tela)."""
    return (
        f"Olá, {mentor_nome}!\n\n"
        f"Você recebeu uma nova solicitação de mentoria de {mentee_nome} para o caminho de {cargo}.\n\n"
        f"Mensagem:\n{message}\n\n"
        "Esta mensagem foi intermediada pelo caminh.ia (CarrerMatch by bho:). Seu e-mail não foi compartilhado."
    )


class ResendEmailNotifier(MentorNotifier):
    def __init__(
        self,
        api_key: SecretStr | None,
        from_email: str = "caminh.ia <notificacoes@caminh.ia>",
        pool: asyncpg.Pool | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        self._api_key = api_key.get_secret_value() if api_key else None
        self._from = from_email
        self._pool = pool
        self._transport = transport
        self._timeout_s = timeout_s

    async def notify_mentor_request(self, match_id: UUID) -> None:
        if not self._api_key:
            log.info("RESEND_API_KEY ausente: notificação de mentoria %s registrada apenas em log", match_id)
            return

        if self._pool is None:
            log.warning("pool ausente: não é possível carregar dados para envio do e-mail da mentoria %s", match_id)
            return

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT mm.id, mm.message, u_mentor.email AS mentor_email,
                           COALESCE(u_mentor.display_name, 'Mentor(a)') AS mentor_nome,
                           COALESCE(u_mentee.display_name, 'Novo Mentorado') AS mentee_nome,
                           ri.title AS cargo_titulo
                    FROM mentor_matches mm
                    JOIN users u_mentor ON u_mentor.id = mm.mentor_id
                    JOIN users u_mentee ON u_mentee.id = mm.mentee_id
                    LEFT JOIN roles_i18n ri ON ri.role_id = mm.role_id AND ri.locale = 'pt-BR'
                    WHERE mm.id = $1
                    """,
                    match_id,
                )
        except Exception:
            log.exception("falha ao consultar detalhes do match %s para envio de e-mail", match_id)
            return

        if not row or not row["mentor_email"]:
            log.warning("mentor_match %s não encontrado ou mentor sem e-mail", match_id)
            return

        cargo = row["cargo_titulo"] or "Carreira"
        subject = f"Nova solicitação de mentoria no caminh.ia: {cargo}"
        payload = {
            "from": self._from,
            "to": [row["mentor_email"]],
            "subject": subject,
            "html": render_mentor_request_html(row["mentor_nome"], row["mentee_nome"], cargo, row["message"] or ""),
            "text": render_mentor_request_text(row["mentor_nome"], row["mentee_nome"], cargo, row["message"] or ""),
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout_s) as client:
                resp = await client.post(RESEND_ENDPOINT, json=payload, headers=headers)
                if resp.status_code in (200, 201):
                    log.info("e-mail de mentoria %s enviado com sucesso via Resend", match_id)
                else:
                    # só o status: o corpo da resposta pode ecoar destinatário/assunto (PII em log)
                    log.error("Resend recusou o envio da mentoria %s (HTTP %s)", match_id, resp.status_code)
        except Exception:
            log.exception("erro de comunicação com a API do Resend para o match %s", match_id)
