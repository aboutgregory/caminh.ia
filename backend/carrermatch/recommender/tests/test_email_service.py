"""Testes unitários para ResendEmailNotifier (RACI Antigravity)."""

import uuid

import httpx
import pytest
from pydantic import SecretStr

from carrermatch.recommender.services.email_service import ResendEmailNotifier


@pytest.mark.asyncio
async def test_notifier_without_key_does_nothing():
    notifier = ResendEmailNotifier(api_key=None)
    # Não deve lançar exceção
    await notifier.notify_mentor_request(uuid.uuid4())


@pytest.mark.asyncio
async def test_notifier_sends_email_with_resend_api():
    seen_requests = []

    def mock_transport(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(200, json={"id": "email_123"})

    class MockConn:
        async def fetchrow(self, query, *args):
            return {
                "id": args[0],
                "message": "Gostaria de mentoria em growth.",
                "mentor_email": "mentor@exemplo.com",
                "mentor_nome": "Carlos",
                "mentee_nome": "Samuel",
                "cargo_titulo": "Growth Hacker",
            }

    class MockPool:
        def acquire(self):
            return self

        async def __aenter__(self):
            return MockConn()

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    notifier = ResendEmailNotifier(
        api_key=SecretStr("re_test_key_123"),
        from_email="caminh.ia <notificacoes@caminh.ia>",
        pool=MockPool(),
        transport=httpx.MockTransport(mock_transport),
    )

    mid = uuid.uuid4()
    await notifier.notify_mentor_request(mid)

    assert len(seen_requests) == 1
    req = seen_requests[0]
    assert req.url == "https://api.resend.com/emails"
    assert req.headers["Authorization"] == "Bearer re_test_key_123"


# ---- revisão claude (008): escape de HTML no e-mail ao mentor ----
from carrermatch.recommender.services.email_service import (  # noqa: E402
    render_mentor_request_html,
    render_mentor_request_text,
)


def test_html_escapes_every_user_controlled_field():
    evil = '<img src=x onerror="alert(1)">'
    out = render_mentor_request_html(evil, evil, evil, evil + "\nlinha 2 & <b>x</b>")
    assert "<img" not in out
    assert "onerror=\"alert" not in out
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in out
    assert "&amp; &lt;b&gt;x&lt;/b&gt;" in out
    assert "<br>" in out  # quebra de linha preservada de forma segura


def test_email_uses_brand_palette_not_campaign_gold():
    out = render_mentor_request_html("Ana", "Bia", "Growth", "oi")
    assert "#0D0720" in out and "#B48DDA" in out
    for legacy in ("#C9A84C", "#E8C97A", "#F5EDD8", "201, 168, 76"):
        assert legacy not in out


def test_plain_text_version_has_content():
    txt = render_mentor_request_text("Ana", "Bia", "Growth", "quero mentoria")
    assert "Bia" in txt and "Growth" in txt and "quero mentoria" in txt
