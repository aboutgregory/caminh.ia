"""Sprint 0 — domínio, seed e repositório em memória."""

from collections import Counter

import pytest
from fastapi.testclient import TestClient

from carrermatch.db.seeds.loader import load_seed, seed_repository
from carrermatch.recommender.models.domain import (
    CareerTransition,
    Experience,
    ExperienceKind,
    MarketTrend,
    RecommendationSource,
    RecommendedPath,
    Role,
    UserProfile,
)
from carrermatch.recommender.repositories.recommender_repo import RecommenderRepository


def _exp(text: str = "x", **kw) -> Experience:
    return Experience(raw_text=text, **kw)


class TestDomain:
    @pytest.mark.parametrize("n", [2, 6])
    def test_profile_rejects_out_of_range_experience_count(self, n):  # RN-01 / RN-02
        with pytest.raises(ValueError):
            UserProfile(experiences=tuple(_exp() for _ in range(n)))

    @pytest.mark.parametrize("n", [3, 4, 5])
    def test_profile_accepts_3_to_5(self, n):
        assert len(UserProfile(experiences=tuple(_exp() for _ in range(n))).experiences) == n

    def test_blank_experience_rejected(self):
        with pytest.raises(ValueError):
            _exp("   ")

    def test_unit_scores_validated(self):
        with pytest.raises(ValueError):
            _exp(emotional_impact=1.2)

    def test_personal_and_professional_default_to_same_weights(self):  # RN-09
        personal = _exp(kind=ExperienceKind.PERSONAL)
        professional = _exp(kind=ExperienceKind.PROFESSIONAL)
        attrs = ("emotional_impact", "mastery_level", "recognition_score")
        assert [getattr(personal, a) for a in attrs] == [getattr(professional, a) for a in attrs]

    def test_self_transition_rejected(self):
        with pytest.raises(ValueError):
            CareerTransition(from_role_id=1, to_role_id=1, observed_count=1, confidence=0.5)

    @pytest.mark.parametrize(("score", "stars"), [(0.0, 1), (0.19, 1), (0.5, 3), (0.7, 4), (1.0, 5)])
    def test_relevance_stars(self, score, stars):
        role = Role(id=1, slug="r", title="R", sector_id=1, market_trend=MarketTrend.ESTAVEL)
        assert RecommendedPath(role=role, confidence_score=score, source=RecommendationSource.HYBRID).relevance_stars == stars


class TestSeed:
    def test_knowledge_graph_meets_sprint0_gate(self):
        assert len(load_seed().transitions) >= 200

    def test_every_role_has_at_least_five_skills_and_three_industries(self):  # PRD §6.2 — 5 habilidades-chave
        for role in load_seed().roles:
            assert len(role.skills) >= 5, role.slug
            assert len(role.related_sector_ids) == 3, role.slug
            assert len(set(role.related_sector_ids)) == 3, role.slug

    def test_every_role_is_reachable_or_has_exits(self):
        seed = load_seed()
        touched = {t.from_role_id for t in seed.transitions} | {t.to_role_id for t in seed.transitions}
        orphans = [r.slug for r in seed.roles if r.id not in touched]
        assert orphans == []

    def test_skill_aliases_are_unique_per_skill_and_lowercase(self):
        for skill in load_seed().skills:
            assert skill.aliases, skill.slug
            assert all(a == a.lower() for a in skill.aliases), skill.slug
            assert len(set(skill.aliases)) == len(skill.aliases), skill.slug

    def test_all_three_market_trends_represented(self):
        trends = Counter(r.market_trend for r in load_seed().roles)
        assert set(trends) == set(MarketTrend)

    def test_samuel_hybrid_roles_exist(self):
        slugs = {r.slug for r in load_seed().roles}
        assert {"consultor_performance_vendas", "head_cs_healthtech", "growth_longevidade"} <= slugs


class TestInMemoryRepository:
    async def test_satisfies_protocol_and_loads(self):
        repo = seed_repository()
        assert isinstance(repo, RecommenderRepository)
        assert len(await repo.list_roles()) == len(load_seed().roles)
        assert await repo.skill_cooccurrence() == {}

    def test_rejects_dangling_transition(self):
        from carrermatch.recommender.repositories.recommender_repo import InMemoryRepository

        seed = load_seed()
        bad = CareerTransition(from_role_id=seed.roles[0].id, to_role_id=9999, observed_count=1, confidence=0.5)
        with pytest.raises(ValueError):
            InMemoryRepository(roles=seed.roles, transitions=[bad])


def test_health_degraded_without_database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:x@127.0.0.1:1/none")
    from carrermatch.config import get_settings

    get_settings.cache_clear()
    from carrermatch.main import create_app

    with TestClient(create_app()) as client:
        resp = client.get("/health")
    get_settings.cache_clear()
    assert resp.status_code == 503
    assert resp.json()["database"] is False
