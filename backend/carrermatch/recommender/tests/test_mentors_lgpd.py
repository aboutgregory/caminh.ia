"""Sprint 3 — MentorMatcher, POST /mentor-matches, solicitação de mentoria e direitos LGPD."""

import time
import uuid

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from carrermatch.api.deps import AppServices
from carrermatch.config import get_settings
from carrermatch.db.seeds.loader import load_seed
from carrermatch.main import create_app
from carrermatch.recommender.engines.mentor_matcher import MentorMatcher, MentorProfile
from carrermatch.recommender.engines.skill_extractor import skill_idf
from carrermatch.recommender.repositories.account_repo import InMemoryAccountStore
from carrermatch.recommender.repositories.write_repo import InMemoryEventRepository
from carrermatch.recommender.services.account_services import SupabaseAuthAdmin
from carrermatch.recommender.services.behavioral_service import BehavioralEventCollector
from carrermatch.recommender.tests.personas import SAMUEL_MEDINA

SECRET = "test-secret-only-for-unit-tests-0123456789"  # pragma: allowlist secret
SEED = load_seed()
SK = {s.slug: s.id for s in SEED.skills}
ROLE = {r.slug: r for r in SEED.roles}
IDF = skill_idf(SEED.skills, SEED.roles)


def mentor(name: str, *slugs: str, mid: uuid.UUID | None = None) -> MentorProfile:
    return MentorProfile(mid or uuid.uuid4(), name, f"headline de {name}", {SK[s]: 1.0 for s in slugs})


PERFORMANCE = mentor("Ana", "performance_humana", "vendas", "mentoria", "saude_fisica", "psicologia_comportamental")
GROWTH = mentor("Bia", "growth", "longevidade", "analise_dados", "saude_fisica")
DEV = mentor("Caio", "programacao", "cloud_devops", "resolucao_problemas")
SALES = mentor("Duda", "vendas", "vendas_consultivas", "comunicacao")
MENTORS = [PERFORMANCE, GROWTH, DEV, SALES]


def token(sub: uuid.UUID) -> str:
    claims = {"sub": str(sub), "aud": "authenticated", "exp": int(time.time()) + 600, "email": "pessoa@exemplo.com"}
    return jwt.encode(claims, SECRET, algorithm="HS256")


# ------------------------------------------------------------------ engine
class TestMentorMatcher:
    matcher = MentorMatcher(IDF)
    samuel = {SK["saude_fisica"]: 1.0, SK["disciplina"]: 0.8, SK["growth"]: 1.0, SK["vendas"]: 0.4}

    def test_best_mentor_combines_peer_similarity_and_role_fit(self):
        result = self.matcher.match(self.samuel, ROLE["consultor_performance_vendas"], MENTORS)
        assert result[0].mentor is PERFORMANCE
        assert all(0 <= m.similarity_score <= 1 for m in result)
        assert [m.similarity_score for m in result] == sorted((m.similarity_score for m in result), reverse=True)

    def test_mentor_without_any_role_skill_is_excluded(self):
        result = self.matcher.match(self.samuel, ROLE["consultor_performance_vendas"], MENTORS)
        assert DEV not in [m.mentor for m in result]

    def test_peer_similarity_breaks_ties_between_equally_fit_mentors(self):
        twin_a = mentor("A", "vendas", "mentoria", "growth")
        twin_b = mentor("B", "vendas", "mentoria", "programacao")
        role = ROLE["consultor_performance_vendas"]
        result = self.matcher.match({SK["growth"]: 1.0}, role, [twin_b, twin_a])
        assert result[0].mentor is twin_a

    def test_excludes_self_and_limits_to_k(self):
        many = [mentor(f"m{i}", "vendas", "mentoria") for i in range(9)]
        result = self.matcher.match(self.samuel, ROLE["consultor_performance_vendas"], many, exclude=many[0].id)
        assert len(result) == 5
        assert many[0] not in [m.mentor for m in result]

    def test_reasons_are_role_skills_prioritizing_shared_with_mentee(self):
        [top, *_] = self.matcher.match(self.samuel, ROLE["consultor_performance_vendas"], [PERFORMANCE])
        role_skills = {rs.skill_id for rs in ROLE["consultor_performance_vendas"].skills}
        assert set(top.reason_skill_ids) <= role_skills
        assert top.reason_skill_ids[0] in self.samuel

    def test_no_mentors_returns_empty(self):
        assert self.matcher.match(self.samuel, ROLE["growth_longevidade"], []) == []


# ------------------------------------------------------------------ API
@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("RATE_LIMIT_MENTOR_REQUESTS", "3/hour")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        base: AppServices = app.state.services
        store = InMemoryAccountStore(mentors=list(MENTORS), available={m.id for m in MENTORS if m is not SALES})
        events = InMemoryEventRepository()
        revoked: list[uuid.UUID] = []

        class FakeAdmin:
            ok = True

            async def delete_user(self, auth_id):
                revoked.append(auth_id)
                return self.ok

        app.state.services = AppServices(
            pipeline=base.pipeline, claude=base.claude, events=BehavioralEventCollector(events), store=None,
            accounts=store, mentor_matcher=MentorMatcher(base.pipeline.idf), auth_admin=FakeAdmin(),
        )
        client.store, client.events, client.revoked, client.admin = store, events, revoked, app.state.services.auth_admin
        yield client
    get_settings.cache_clear()


def auth(sub: uuid.UUID, session: bool = True) -> dict:
    h = {"Authorization": f"Bearer {token(sub)}"}
    if session:
        h["X-Session-ID"] = str(uuid.uuid4())
    return h


ROLE_ID = ROLE["consultor_performance_vendas"].id


class TestFindMentors:
    def test_requires_login(self, api):  # RN-08
        assert api.post("/mentor-matches", json={"role_id": ROLE_ID}).status_code == 401

    def test_with_experiences_in_body(self, api):
        resp = api.post("/mentor-matches", json={"role_id": ROLE_ID, "experiences": list(SAMUEL_MEDINA)},
                        headers=auth(uuid.uuid4()))
        assert resp.status_code == 200, resp.text
        mentors = resp.json()["mentors"]
        assert 1 <= len(mentors) <= 5
        assert mentors[0]["display_name"] == "Ana"
        assert all(m["match_reasons"] and all(m["match_reasons"]) for m in mentors)
        assert "Duda" not in [m["display_name"] for m in mentors]          # indisponível
        assert not any("email" in m for m in mentors)                      # contato só via backend

    def test_uses_saved_profile_when_no_experiences(self, api):
        sub = uuid.uuid4()
        api.store.saved_skills[sub] = {SK["performance_humana"]: 1.0, SK["vendas"]: 0.8}
        resp = api.post("/mentor-matches", json={"role_id": ROLE_ID}, headers=auth(sub))
        assert resp.status_code == 200
        assert resp.json()["mentors"][0]["display_name"] == "Ana"

    def test_no_profile_is_friendly_422(self, api):
        resp = api.post("/mentor-matches", json={"role_id": ROLE_ID}, headers=auth(uuid.uuid4()))
        assert resp.status_code == 422
        assert "experiências" in resp.json()["error"]

    def test_unknown_role_404(self, api):
        resp = api.post("/mentor-matches", json={"role_id": 9999}, headers=auth(uuid.uuid4()))
        assert resp.status_code == 404

    def test_invalid_experiences_rejected(self, api):
        resp = api.post("/mentor-matches", json={"role_id": ROLE_ID, "experiences": ["curto"]}, headers=auth(uuid.uuid4()))
        assert resp.status_code == 422

    def test_no_db_is_503(self, api):
        api.app.state.services.accounts = None
        resp = api.post("/mentor-matches", json={"role_id": ROLE_ID}, headers=auth(uuid.uuid4()))
        assert resp.status_code == 503


class TestMentorRequests:
    MSG = "Quero entender como levar minha experiência com treino para times de vendas."

    def url(self, m: MentorProfile) -> str:
        return f"/mentor-matches/{m.id}/requests"

    def test_create_logs_event_and_returns_201(self, api):
        sub = uuid.uuid4()
        resp = api.post(self.url(PERFORMANCE), json={"role_id": ROLE_ID, "message": self.MSG}, headers=auth(sub))
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == "requested"
        [(_, req)] = api.store.requests
        assert req.mentee_auth_id == sub and req.mentor_id == PERFORMANCE.id
        assert any(e.event_type == "mentor_contacted" for e in api.events.events)

    def test_score_is_computed_server_side(self, api):
        api.post(self.url(PERFORMANCE), json={"role_id": ROLE_ID, "message": self.MSG, "similarity_score": 1},
                 headers=auth(uuid.uuid4()))
        assert api.store.requests == []  # campo extra rejeitado (extra="forbid")

    def test_duplicate_pending_is_409(self, api):
        sub = uuid.uuid4()
        body = {"role_id": ROLE_ID, "message": self.MSG}
        assert api.post(self.url(PERFORMANCE), json=body, headers=auth(sub)).status_code == 201
        resp = api.post(self.url(PERFORMANCE), json=body, headers=auth(sub))
        assert resp.status_code == 409
        assert "pendente" in resp.json()["error"]

    @pytest.mark.parametrize("target", [SALES, mentor("Fantasma", "vendas")], ids=["indisponivel", "inexistente"])
    def test_unavailable_or_unknown_mentor_404(self, api, target):
        resp = api.post(self.url(target), json={"role_id": ROLE_ID, "message": self.MSG}, headers=auth(uuid.uuid4()))
        assert resp.status_code == 404

    def test_message_validation_strips_html(self, api):
        resp = api.post(self.url(PERFORMANCE), json={"role_id": ROLE_ID, "message": "<b>oi</b>" + " " * 30},
                        headers=auth(uuid.uuid4()))
        assert resp.status_code == 422

    def test_anti_spam_rate_limit(self, api):  # limite de teste: 3/hour
        sub = uuid.uuid4()
        codes = [
            api.post(self.url(m), json={"role_id": ROLE_ID, "message": self.MSG}, headers=auth(sub)).status_code
            for m in (PERFORMANCE, GROWTH, DEV, PERFORMANCE)
        ]
        assert codes[-1] == 429

    def test_requires_login(self, api):
        assert api.post(self.url(PERFORMANCE), json={"role_id": ROLE_ID, "message": self.MSG}).status_code == 401


class TestLgpd:
    def test_export_returns_attachment_and_audits(self, api):
        sub = uuid.uuid4()
        api.store.users[sub] = {"conta": {"email": "pessoa@exemplo.com"}, "experiencias": [{"raw_text": "x"}],
                                "recomendacoes": [], "mentorias": [], "eventos": []}
        resp = api.get("/users/me/data", headers=auth(sub))
        assert resp.status_code == 200
        assert "attachment" in resp.headers["Content-Disposition"]
        assert resp.json()["experiencias"] == [{"raw_text": "x"}]
        assert api.store.audit_log[-1] == ("data_exported", {"vazio": False})

    def test_export_without_saved_data_is_honest_empty(self, api):
        resp = api.get("/users/me/data", headers=auth(uuid.uuid4()))
        assert resp.status_code == 200
        assert resp.json()["conta"] is None and resp.json()["experiencias"] == []

    def test_delete_removes_everything_revokes_auth_and_audits_anonymously(self, api):
        sub = uuid.uuid4()
        api.store.users[sub] = {"conta": {}}
        api.store.saved_skills[sub] = {SK["vendas"]: 1.0}
        api.post(f"/mentor-matches/{PERFORMANCE.id}/requests",
                 json={"role_id": ROLE_ID, "message": TestMentorRequests.MSG}, headers=auth(sub))
        resp = api.delete("/users/me", headers=auth(sub))
        assert resp.status_code == 204
        assert sub not in api.store.users and sub not in api.store.saved_skills
        assert api.store.requests == []
        assert api.revoked == [sub]
        event, details = api.store.audit_log[-1]
        assert event == "account_deleted"
        assert str(sub) not in str(details)                    # auditoria sem identificador
        assert api.get("/users/me/data", headers=auth(sub)).json()["conta"] is None

    def test_delete_records_failed_auth_revocation(self, api):
        api.admin.ok = False
        sub = uuid.uuid4()
        api.store.users[sub] = {"conta": {}}
        assert api.delete("/users/me", headers=auth(sub)).status_code == 204
        assert api.store.audit_log[-1][0] == "auth_revocation_failed"

    def test_delete_is_idempotent_for_unknown_user(self, api):
        assert api.delete("/users/me", headers=auth(uuid.uuid4())).status_code == 204

    def test_lgpd_routes_require_login(self, api):
        assert api.get("/users/me/data").status_code == 401
        assert api.delete("/users/me").status_code == 401


class TestSupabaseAuthAdmin:
    @pytest.mark.parametrize(("code", "expected"), [(204, True), (200, True), (404, True), (500, False), (401, False)])
    async def test_status_handling(self, code, expected):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"], seen["auth"], seen["method"] = str(request.url), request.headers["Authorization"], request.method
            return httpx.Response(code)

        transport = httpx.MockTransport(handler)
        admin = SupabaseAuthAdmin("https://proj.supabase.co/", "srk-test", transport=transport)  # pragma: allowlist secret
        sub = uuid.uuid4()
        assert await admin.delete_user(sub) is expected
        assert seen == {"url": f"https://proj.supabase.co/auth/v1/admin/users/{sub}", "auth": "Bearer srk-test",
                        "method": "DELETE"}

    async def test_network_error_is_false(self):
        def handler(request):
            raise httpx.ConnectError("sem rede")

        admin = SupabaseAuthAdmin("https://p.supabase.co", "k", transport=httpx.MockTransport(handler))
        assert await admin.delete_user(uuid.uuid4()) is False
