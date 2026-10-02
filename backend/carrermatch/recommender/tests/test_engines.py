"""Sprint 1 — extração, item-based, knowledge graph e pipeline híbrido (offline, InMemoryRepository)."""

import dataclasses

import pytest

from carrermatch.db.seeds.loader import load_seed, seed_repository
from carrermatch.recommender.engines.hybrid import (
    HybridPipeline,
    InsufficientPathsError,
    NoSkillsDetectedError,
)
from carrermatch.recommender.engines.item_based import ItemBasedRecommender
from carrermatch.recommender.engines.knowledge_graph import KnowledgeGraphEngine
from carrermatch.recommender.engines.skill_extractor import SkillExtractor, normalize, skill_idf
from carrermatch.recommender.engines.vectors import cosine, experience_weight
from carrermatch.recommender.models.domain import (
    MAX_PATHS,
    MIN_PATHS,
    CareerTransition,
    Experience,
    ExperienceKind,
    ExperienceSkill,
    MarketTrend,
    Role,
    RoleSkill,
    UserProfile,
)
from carrermatch.recommender.tests.personas import DEV_DADOS, EDUCADORA_COMUNITARIA, SAMUEL_MEDINA

SEED = load_seed()
SKILL = {s.slug: s.id for s in SEED.skills}
ROLE = {r.slug: r.id for r in SEED.roles}
IDF = skill_idf(SEED.skills, SEED.roles)


@pytest.fixture(scope="module")
async def pipeline() -> HybridPipeline:
    return await HybridPipeline.from_repository(seed_repository())


def slugs(paths) -> list[str]:
    return [p.role.slug for p in paths]


# ---------------------------------------------------------------- extração
class TestSkillExtractor:
    extractor = SkillExtractor(SEED.skills, IDF)

    def ids(self, text: str) -> set[int]:
        return {es.skill_id for es in self.extractor.extract(text)}

    def test_normalize_strips_accents_and_case(self):
        assert normalize("  Automações   em  HOME Office ") == "automacoes em home office"

    def test_accent_insensitive_match(self):
        assert SKILL["automacao"] in self.ids("fiz automacoes sem acento")

    def test_multiword_alias(self):
        found = self.ids("mantenho uma disciplina corporal rígida")
        assert {SKILL["saude_fisica"], SKILL["performance_humana"], SKILL["disciplina"]} <= found

    def test_word_boundary_prevents_substring_match(self):
        # "ux" não pode casar dentro de "luxo"; "ui" não pode casar em "construir"
        assert SKILL["ux_design"] not in self.ids("trabalhei com luxo e quis construir algo")

    def test_weights_normalized_to_unit_max(self):
        weights = [es.weight for es in self.extractor.extract("growth, funil, retenção e terapia")]
        assert max(weights) == 1.0
        assert all(0 < w <= 1 for w in weights)

    def test_idf_downweights_generic_skills(self):
        assert IDF[SKILL["comunicacao"]] < IDF[SKILL["longevidade"]]

    def test_no_match_returns_empty(self):
        assert self.extractor.extract("xyz qwerty") == ()


# ---------------------------------------------------------------- vetores
def test_cosine_bounds():
    assert cosine({1: 1.0}, {1: 2.0}) == pytest.approx(1.0)
    assert cosine({1: 1.0}, {2: 1.0}) == 0.0
    assert cosine({}, {1: 1.0}) == 0.0


def test_experience_weight_floor_and_ignores_kind():  # RN-09
    low = Experience(raw_text="x", emotional_impact=0, mastery_level=0, recognition_score=0)
    assert experience_weight(low) == 0.5
    personal = Experience(raw_text="x", kind=ExperienceKind.PERSONAL, emotional_impact=0.9)
    professional = dataclasses.replace(personal, kind=ExperienceKind.PROFESSIONAL)
    assert experience_weight(personal) == experience_weight(professional)


# ---------------------------------------------------------------- item-based
class TestItemBased:
    rec = ItemBasedRecommender(SEED.roles, IDF)

    def profile(self, *skill_slugs: str) -> UserProfile:
        skills = tuple(ExperienceSkill(SKILL[s], 1.0) for s in skill_slugs)
        exps = (Experience(raw_text="a", skills=skills), Experience(raw_text="b"), Experience(raw_text="c"))
        return UserProfile(experiences=exps)

    def test_exact_skill_profile_ranks_matching_role_first(self):
        top = self.rec.recommend(self.profile("programacao", "resolucao_problemas", "autodidatismo"), limit=3)
        assert top[0].role.slug == "desenvolvedor_software"

    def test_matched_skills_are_subset_of_role_skills(self):
        for path in self.rec.recommend(self.profile("growth", "analise_dados"), limit=10):
            assert set(path.matched_skill_ids) <= {rs.skill_id for rs in path.role.skills}

    def test_expansion_adds_neighbors_with_lower_weight(self):
        base = {SKILL["growth"]: 1.0}
        expanded = self.rec.expand(base)
        assert len(expanded) > 1
        assert all(w < 1.0 for s, w in expanded.items() if s != SKILL["growth"])

    def test_cooccurrence_changes_neighbors(self):
        a, b = sorted((SKILL["saude_fisica"], SKILL["vendas"]))
        with_data = ItemBasedRecommender(SEED.roles, IDF, cooccurrence={(a, b): 10.0})
        assert SKILL["vendas"] in dict(with_data.neighbors(SKILL["saude_fisica"]))

    def test_unrelated_profile_scores_zero(self):
        empty = UserProfile(experiences=tuple(Experience(raw_text=t) for t in "abc"))
        assert self.rec.recommend(empty) == []


# ---------------------------------------------------------------- knowledge graph
class TestKnowledgeGraph:
    def test_two_hop_path_with_decay(self):
        t = [
            CareerTransition(1, 2, observed_count=10, confidence=1.0),
            CareerTransition(2, 3, observed_count=10, confidence=1.0),
        ]
        paths = KnowledgeGraphEngine(t).explore({1: 1.0}, {})
        assert paths[2].role_ids == (1, 2)
        assert paths[3].role_ids == (1, 2, 3)
        assert paths[3].strength < paths[2].strength

    def test_hop_limit(self):
        t = [CareerTransition(i, i + 1, observed_count=1, confidence=0.9) for i in range(1, 6)]
        assert set(KnowledgeGraphEngine(t).explore({1: 1.0}, {})) == {2, 3}

    def test_bridge_skills_boost_edge(self):
        t = CareerTransition(1, 2, observed_count=5, confidence=0.5, bridge_skill_ids=(7,))
        eng = KnowledgeGraphEngine([t])
        assert eng.edge_strength(t, {7: 1.0}) > eng.edge_strength(t, {})

    def test_weak_affinity_is_not_an_anchor(self):
        t = [CareerTransition(1, 2, observed_count=5, confidence=0.9)]
        assert KnowledgeGraphEngine(t).explore({1: 0.01}, {}) == {}

    def test_no_cycles(self):
        t = [CareerTransition(1, 2, 5, 0.9), CareerTransition(2, 1, 5, 0.9)]
        paths = KnowledgeGraphEngine(t).explore({1: 1.0}, {})
        assert 1 not in paths


# ---------------------------------------------------------------- pipeline híbrido
class TestHybridPipeline:
    async def test_samuel_medina_sprint1_gate(self, pipeline):
        """Gate do sprint 1: 6–21 caminhos e ao menos 6 com confidence > 0.5."""
        paths = pipeline.recommend(pipeline.build_profile(SAMUEL_MEDINA))
        assert MIN_PATHS <= len(paths) <= MAX_PATHS
        assert sum(p.confidence_score > 0.5 for p in paths) >= 6
        # combinações não óbvias que o caso Samuel validou no beta
        assert {"consultor_performance_vendas", "growth_longevidade"} <= set(slugs(paths))

    async def test_samuel_top5_are_multi_experience(self, pipeline):
        paths = pipeline.recommend(pipeline.build_profile(SAMUEL_MEDINA))
        assert all(p.score_breakdown["combination"] >= 0.4 for p in paths[:5])

    @pytest.mark.parametrize("texts", [DEV_DADOS, EDUCADORA_COMUNITARIA])
    async def test_other_personas_get_coherent_top3(self, pipeline, texts):
        top3 = pipeline.recommend(pipeline.build_profile(texts))[:3]
        expected = {
            DEV_DADOS: {"cientista_dados", "especialista_ia_aplicada", "analista_dados"},
            EDUCADORA_COMUNITARIA: {
                "criador_conteudo", "articulador_comunitario", "gestor_impacto_social", "designer_instrucional",
            },
        }[texts]
        assert len(set(slugs(top3)) & expected) >= 2

    async def test_output_contract(self, pipeline):  # PRD §6.2
        for p in pipeline.recommend(pipeline.build_profile(SAMUEL_MEDINA)):
            assert len(p.key_skill_ids) == 5
            assert len(set(p.key_skill_ids)) == 5
            assert len(p.industry_ids) == 3
            assert 1 <= p.relevance_stars <= 5
            assert 0 < p.confidence_score < 1
            assert p.description is None  # ADR-02: descrição é papel do ClaudeDescriptionService

    async def test_no_duplicate_roles(self, pipeline):
        names = slugs(pipeline.recommend(pipeline.build_profile(SAMUEL_MEDINA)))
        assert len(names) == len(set(names))

    async def test_deterministic(self, pipeline):
        prof = pipeline.build_profile(SAMUEL_MEDINA)
        assert slugs(pipeline.recommend(prof)) == slugs(pipeline.recommend(prof))

    async def test_rn09_kind_does_not_change_results(self, pipeline):
        prof = pipeline.build_profile(SAMUEL_MEDINA)
        as_personal = UserProfile(
            experiences=tuple(dataclasses.replace(e, kind=ExperienceKind.PERSONAL) for e in prof.experiences)
        )
        a = [(p.role.slug, p.confidence_score) for p in pipeline.recommend(prof)]
        b = [(p.role.slug, p.confidence_score) for p in pipeline.recommend(as_personal)]
        assert a == b

    async def test_rn05_no_skills_raises(self, pipeline):
        with pytest.raises(NoSkillsDetectedError):
            pipeline.recommend(pipeline.build_profile(("lorem ipsum", "dolor sit", "amet xyz")))

    async def test_rn05_too_few_paths_raises(self):
        # vocabulário mínimo: 2 cargos → impossível chegar a 6
        skills = SEED.skills
        roles = [
            Role(1, "a", "A", 1, MarketTrend.ESTAVEL, skills=(RoleSkill(SKILL["growth"], 1.0),), related_sector_ids=(1, 2, 3)),
            Role(2, "b", "B", 1, MarketTrend.ESTAVEL, skills=(RoleSkill(SKILL["vendas"], 1.0),), related_sector_ids=(1, 2, 3)),
        ]
        from carrermatch.recommender.repositories.recommender_repo import InMemoryRepository

        tiny = await HybridPipeline.from_repository(InMemoryRepository(skills=skills, roles=roles))
        with pytest.raises(InsufficientPathsError) as exc:
            tiny.recommend(tiny.build_profile(("growth", "vendas", "growth e vendas")))
        assert exc.value.found < MIN_PATHS

    async def test_rn04_never_more_than_21(self, pipeline):
        broad = (
            "growth, vendas, automação, dados, programação e liderança de equipe",
            "terapia, treino, nutrição, saúde mental e performance",
            "aulas, mentoria, eventos, comunidade, conteúdo e storytelling",
        )
        assert len(pipeline.recommend(pipeline.build_profile(broad))) <= MAX_PATHS

    async def test_risk_tolerance_favors_emerging(self, pipeline):
        def emerging_share(risk: float) -> float:
            paths = pipeline.recommend(pipeline.build_profile(SAMUEL_MEDINA, risk_tolerance=risk))
            top = paths[:10]
            return sum(p.role.market_trend is MarketTrend.EMERGENTE for p in top) / len(top)

        assert emerging_share(1.0) >= emerging_share(0.0)

    async def test_sector_diversity(self, pipeline):
        paths = pipeline.recommend(pipeline.build_profile(SAMUEL_MEDINA))
        assert len({p.role.sector_id for p in paths}) >= 4
