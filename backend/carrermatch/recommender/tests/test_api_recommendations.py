"""Sprint 2 — POST /recommendations e POST /events, ponta a ponta com dublês (sem banco, sem Claude real)."""

import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from carrermatch.api.deps import AppServices
from carrermatch.api.rate_limit import SlidingWindowLimiter, parse_limits
from carrermatch.config import get_settings
from carrermatch.main import create_app
from carrermatch.recommender.repositories.write_repo import InMemoryEventRepository, InMemoryRecommendationStore
from carrermatch.recommender.services.behavioral_service import BehavioralEventCollector
from carrermatch.recommender.services.claude_service import ClaudeDescriptionService
from carrermatch.recommender.tests.fakes import FakeAnthropic
from carrermatch.recommender.tests.personas import SAMUEL_MEDINA

SECRET = "test-secret-only-for-unit-tests-0123456789"  # pragma: allowlist secret
SESSION = str(uuid.uuid4())


def token(sub: str | None = None) -> str:
    claims = {"sub": sub or str(uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 600, "email": "p@ex.com"}
    return jwt.encode(claims, SECRET, algorithm="HS256")


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("RATE_LIMIT_RECOMMENDATIONS", "3/minute")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        base: AppServices = app.state.services   # pipeline com o seed em memória (sem banco)
        fake = FakeAnthropic()
        events = InMemoryEventRepository()
        store = InMemoryRecommendationStore()
        app.state.services = AppServices(
            pipeline=base.pipeline,
            claude=ClaudeDescriptionService(
                fake, model="claude-sonnet-5-5",
                skill_names=base.pipeline.skill_names, sector_names=base.pipeline.sector_names,
            ),
            events=BehavioralEventCollector(events),
            store=store,
        )
        client.fake, client.events, client.store = fake, events, store
        yield client
    get_settings.cache_clear()


def post(api, body=None, **headers):
    return api.post(
        "/recommendations",
        json=body or {"experiences": list(SAMUEL_MEDINA)},
        headers={"X-Session-ID": SESSION, **headers},
    )


class TestRecommendations:
    def test_samuel_end_to_end_contract(self, api):  # PRD §6.2 / RN-03
        resp = post(api)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert 6 <= len(body["paths"]) <= 21
        assert body["model_version"] == "hybrid-v1+claude-sonnet-5-5"
        assert body["saved"] is False  # anônimo (RN-06/07)
        for i, p in enumerate(body["paths"], 1):
            assert p["id"] == i
            assert len(p["key_skills"]) == 5 and all(p["key_skills"])
            assert len(p["industries"]) == 3
            assert p["market_trend"] in {"Em Alta", "Estável", "Emergente"}
            assert 1 <= p["relevance"] <= 5
            assert p["description_source"] == "claude"
        titles = {p["title"] for p in body["paths"]}
        assert "Especialista em Growth para Longevidade" in titles

    def test_generated_event_logged_without_free_text(self, api):  # RN-10 + minimização
        post(api)
        [event] = [e for e in api.events.events if e.event_type == "recommendation_generated"]
        assert str(event.session_id) == SESSION
        assert event.user_auth_id is None
        assert set(event.payload) >= {"n_paths", "role_ids", "latency_ms"}
        assert all(not isinstance(v, str) for v in event.payload.values())

    @pytest.mark.parametrize(
        ("experiences", "fragment"),
        [
            (["a" * 20, "b" * 20], "experiences"),                      # RN-01
            (["x" * 20] * 6, "experiences"),                            # RN-02
            (["curto", "growth em startup", "terapia por anos"], "curta"),
            (["a" * 1501, "growth em startup", "terapia por anos"], "1500"),
        ],
    )
    def test_input_validation(self, api, experiences, fragment):
        resp = post(api, {"experiences": experiences})
        assert resp.status_code == 422
        assert fragment in resp.text

    def test_unknown_fields_rejected(self, api):
        resp = post(api, {"experiences": list(SAMUEL_MEDINA), "user_id": "x"})
        assert resp.status_code == 422

    def test_no_skills_friendly_422(self, api):  # RN-05
        resp = post(api, {"experiences": ["lorem ipsum dolor", "sit amet consectetur", "adipiscing elit sed"]})
        assert resp.status_code == 422
        assert "habilidades" in resp.json()["error"]
        assert any(e.event_type == "recommendation_failed" for e in api.events.events)

    def test_html_is_stripped_before_processing(self, api):
        exps = [f"<script>alert(1)</script>{t}" for t in SAMUEL_MEDINA[:3]]
        post(api, {"experiences": exps})
        prompt = api.fake.messages.calls[0]["messages"][0]["content"]
        assert "<script>" not in prompt

    def test_claude_failure_still_returns_200_with_fallback(self, api):
        api.fake.messages.mode = "refusal"
        resp = post(api)
        assert resp.status_code == 200
        assert {p["description_source"] for p in resp.json()["paths"]} == {"fallback"}


class TestPersistence:  # RN-07 + LGPD
    def test_authenticated_with_consent_is_saved(self, api):
        sub = str(uuid.uuid4())
        resp = post(api, {"experiences": list(SAMUEL_MEDINA), "consent_data": True}, Authorization=f"Bearer {token(sub)}")
        assert resp.json()["saved"] is True
        [saved] = api.store.saved
        assert str(saved.user_auth_id) == sub
        assert len(saved.paths) == len(resp.json()["paths"])

    def test_authenticated_without_consent_is_not_saved(self, api):
        resp = post(api, Authorization=f"Bearer {token()}")
        assert resp.json()["saved"] is False
        assert api.store.saved == []

    def test_anonymous_with_consent_is_not_saved(self, api):
        resp = post(api, {"experiences": list(SAMUEL_MEDINA), "consent_data": True})
        assert resp.json()["saved"] is False

    def test_invalid_token_is_401(self, api):
        assert post(api, Authorization="Bearer abc.def.ghi").status_code == 401


class TestRateLimit:
    def test_fourth_request_in_a_minute_is_429(self, api):  # limite de teste: 3/minute
        codes = [post(api).status_code for _ in range(4)]
        assert codes == [200, 200, 200, 429]
        resp = post(api)
        assert int(resp.headers["Retry-After"]) >= 1
        assert "Aguarde" in resp.json()["error"]

    def test_sliding_window_releases(self):
        now = [0.0]
        lim = SlidingWindowLimiter("2/minute;3/hour", clock=lambda: now[0])
        assert lim.hit("ip") is None and lim.hit("ip") is None
        assert lim.hit("ip") is not None          # 3ª no mesmo minuto
        now[0] = 61
        assert lim.hit("ip") is None              # minuto liberou (3ª da hora)
        now[0] = 125
        assert lim.hit("ip") is not None          # teto de 3/hora
        assert lim.hit("outro-ip") is None        # chaves independentes

    def test_parse_limits(self):
        assert parse_limits("10/minute;50/hour") == [(10, 60), (50, 3600)]
        with pytest.raises(ValueError):
            parse_limits("10 por minuto")


class TestEvents:
    def test_client_event_accepted(self, api):
        resp = api.post(
            "/events",
            json={"event_type": "career_expanded", "role_id": 30, "reading_time_ms": 4200},
            headers={"X-Session-ID": SESSION},
        )
        assert resp.status_code == 202
        [e] = api.events.events
        assert e.event_type == "career_expanded"
        assert e.payload["engagement_weight"] == 0.3

    @pytest.mark.parametrize(
        "body",
        [
            {"event_type": "recommendation_generated"},   # evento de servidor
            {"event_type": "mentor_contacted"},           # evento de servidor
            {"event_type": "career_expanded", "payload": {"texto": "livre"}},
            {"event_type": "rated_positive", "rating": 9},
        ],
    )
    def test_invalid_events_rejected(self, api, body):
        assert api.post("/events", json=body, headers={"X-Session-ID": SESSION}).status_code == 422

    def test_session_header_required(self, api):
        assert api.post("/events", json={"event_type": "dismissed"}).status_code == 422
