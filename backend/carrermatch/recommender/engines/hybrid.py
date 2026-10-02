"""HybridPipeline — combina item-based + knowledge graph e seleciona 6–21 caminhos.

score bruto = W_ITEM · item_based + W_GRAPH · grafo_relativo
    × fator de combinação  (quantas experiências DIFERENTES sustentam o caminho)
    × ajuste de risco      (risk_tolerance favorece/penaliza cargos emergentes)

confidence_score = 1 − exp(−bruto / TAU): monotônica, em [0, 1), calibrada para
que um encaixe forte e multi-experiência fique acima de 0.7.

Regras: RN-03 (6–21), RN-04 (trunca em 21), RN-05 (<6 → InsufficientPathsError).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from carrermatch.recommender.engines.item_based import ItemBasedRecommender
from carrermatch.recommender.engines.knowledge_graph import GraphPath, KnowledgeGraphEngine
from carrermatch.recommender.engines.skill_extractor import SkillExtractor, skill_idf
from carrermatch.recommender.engines.vectors import skill_sources, user_vector
from carrermatch.recommender.models.domain import (
    MAX_PATHS,
    MIN_PATHS,
    Experience,
    MarketTrend,
    RecommendationSource,
    RecommendedPath,
    Role,
    UserProfile,
)
from carrermatch.recommender.repositories.recommender_repo import RecommenderRepository

W_ITEM = 0.6
W_GRAPH = 0.4
TAU = 0.35
MIN_CONFIDENCE = 0.25        # abaixo disso o caminho não é mostrado
SECTOR_DECAY = 0.85          # diversidade: cada caminho repetido no setor reduz os próximos em 15%
KEY_SKILLS = 5
INDUSTRIES = 3
RISK_STRENGTH = 0.15         # ±15% em cargos emergentes conforme risk_tolerance


class InsufficientPathsError(Exception):
    """RN-05: o pipeline não encontrou caminhos suficientes para o perfil."""

    def __init__(self, found: int) -> None:
        super().__init__(f"apenas {found} caminhos encontrados (mínimo {MIN_PATHS})")
        self.found = found


class NoSkillsDetectedError(InsufficientPathsError):
    """Nenhuma habilidade reconhecida no texto — pedir mais detalhes ao usuário."""

    def __init__(self) -> None:
        super().__init__(0)


@dataclass(frozen=True, slots=True)
class _Candidate:
    role: Role
    item_score: float
    graph: GraphPath | None
    graph_score: float
    combination: float
    raw: float


class HybridPipeline:
    def __init__(
        self,
        extractor: SkillExtractor,
        item_based: ItemBasedRecommender,
        graph: KnowledgeGraphEngine,
        roles: Sequence[Role],
    ) -> None:
        self._extractor = extractor
        self._item = item_based
        self._graph = graph
        self._roles = {r.id: r for r in roles}

    @classmethod
    async def from_repository(cls, repo: RecommenderRepository) -> HybridPipeline:
        skills = await repo.list_skills()
        roles = await repo.list_roles()
        idf = skill_idf(skills, roles)
        return cls(
            extractor=SkillExtractor(skills, idf),
            item_based=ItemBasedRecommender(roles, idf, await repo.skill_cooccurrence()),
            graph=KnowledgeGraphEngine(await repo.list_transitions()),
            roles=roles,
        )

    def build_profile(self, texts: Sequence[str], risk_tolerance: float = 0.5) -> UserProfile:
        """Perfil a partir dos textos livres do onboarding (pesos neutros, RN-09)."""
        return self.enrich(UserProfile(experiences=tuple(Experience(raw_text=t) for t in texts), risk_tolerance=risk_tolerance))

    def enrich(self, profile: UserProfile) -> UserProfile:
        return UserProfile(
            experiences=tuple(self._extractor.enrich(e) for e in profile.experiences),
            user_id=profile.user_id,
            risk_tolerance=profile.risk_tolerance,
        )

    def recommend(self, profile: UserProfile) -> list[RecommendedPath]:
        profile = self.enrich(profile)
        direct = user_vector(profile)
        if not direct:
            raise NoSkillsDetectedError()

        affinity = self._item.score_roles(profile, expand=False)
        item_scores = self._item.score_roles(profile, expand=True)
        graph_paths = self._graph.explore(affinity, direct)
        best_anchor = max(affinity.values(), default=0.0) or 1.0
        sources = skill_sources(profile)
        n_exp = len(profile.experiences)

        candidates: list[_Candidate] = []
        for role_id, role in self._roles.items():
            item = item_scores.get(role_id, 0.0)
            gp = graph_paths.get(role_id)
            # força do caminho relativa ao melhor encaixe atual: ≈ força das arestas percorridas
            graph = min(1.0, gp.strength / best_anchor) if gp else 0.0
            if item <= 0.0 and graph <= 0.0:
                continue
            supporting = set().union(*(sources.get(rs.skill_id, set()) for rs in role.skills))
            combination = len(supporting) / n_exp
            raw = (W_ITEM * item + W_GRAPH * graph) * (0.7 + 0.6 * combination) * self._risk_factor(role, profile)
            candidates.append(_Candidate(role, item, gp, graph, combination, raw))

        selected = self._select(candidates)
        if len(selected) < MIN_PATHS:
            raise InsufficientPathsError(len(selected))
        return [self._to_path(c, direct) for c in selected]

    @staticmethod
    def _risk_factor(role: Role, profile: UserProfile) -> float:
        if role.market_trend is MarketTrend.EMERGENTE:
            return 1 + RISK_STRENGTH * (2 * profile.risk_tolerance - 1)
        return 1.0

    @staticmethod
    def confidence(raw: float) -> float:
        return 1 - math.exp(-raw / TAU)

    def _select(self, candidates: list[_Candidate]) -> list[_Candidate]:
        """Seleção gulosa com penalidade de diversidade por setor (estilo MMR).

        Cada caminho já escolhido no mesmo setor principal multiplica o score dos
        próximos por SECTOR_DECAY. Diferente de um teto rígido, um cargo híbrido
        forte ainda entra mesmo que o setor já tenha vários caminhos. A
        confidence exibida continua sendo a do score sem penalidade.
        """
        pool = [c for c in candidates if self.confidence(c.raw) >= MIN_CONFIDENCE]
        per_sector: dict[int, int] = {}
        selected: list[_Candidate] = []
        while pool and len(selected) < MAX_PATHS:  # RN-04
            best = max(pool, key=lambda c: c.raw * SECTOR_DECAY ** per_sector.get(c.role.sector_id, 0))
            pool.remove(best)
            per_sector[best.role.sector_id] = per_sector.get(best.role.sector_id, 0) + 1
            selected.append(best)
        return selected

    def _to_path(self, c: _Candidate, direct: Mapping[int, float]) -> RecommendedPath:
        role = c.role
        matched = [rs for rs in role.skills if rs.skill_id in direct]
        others = [rs for rs in role.skills if rs.skill_id not in direct]
        key = [rs.skill_id for rs in sorted(matched, key=lambda r: -r.importance)]
        key += [rs.skill_id for rs in sorted(others, key=lambda r: -r.importance)]
        # cargos com <5 habilidades: completa com as habilidades mais fortes do próprio usuário
        for skill_id, _ in sorted(direct.items(), key=lambda kv: -kv[1]):
            if len(key) >= KEY_SKILLS:
                break
            if skill_id not in key:
                key.append(skill_id)

        if c.graph_score > 0 and c.item_score > 0:
            source = RecommendationSource.HYBRID
        elif c.graph_score > 0:
            source = RecommendationSource.KNOWLEDGE_GRAPH
        else:
            source = RecommendationSource.ITEM_BASED

        return RecommendedPath(
            role=role,
            confidence_score=round(self.confidence(c.raw), 4),
            source=source,
            matched_skill_ids=tuple(rs.skill_id for rs in matched),
            key_skill_ids=tuple(key[:KEY_SKILLS]),
            industry_ids=role.related_sector_ids[:INDUSTRIES],
            score_breakdown={
                "item_based": round(c.item_score, 4),
                "knowledge_graph": round(c.graph_score, 4),
                "combination": round(c.combination, 4),
                "raw": round(c.raw, 4),
            },
        )
