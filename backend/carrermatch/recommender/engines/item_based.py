"""ItemBasedRecommender — filtragem colaborativa item-based sobre habilidades.

"Item" = habilidade. A similaridade item-item é o cosseno entre as colunas de
habilidade da matriz cargo × habilidade (cold start), misturada com a
co-ocorrência observada em experiências reais quando ela existir.

Fluxo:
    1. vetor do usuário (TF-IDF × peso da experiência)
    2. expansão: habilidades vizinhas às do usuário entram com peso reduzido —
       é o que conecta "disciplina corporal" a "performance humana" mesmo sem
       o usuário ter escrito a segunda
    3. cosseno entre o vetor expandido e o vetor de cada cargo
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from carrermatch.recommender.engines.vectors import SparseVec, cosine, role_vectors, user_vector
from carrermatch.recommender.models.domain import RecommendationSource, RecommendedPath, Role, UserProfile

EXPANSION_WEIGHT = 0.35   # quanto uma habilidade vizinha vale frente a uma declarada
NEIGHBORS_PER_SKILL = 5
MIN_ITEM_SIMILARITY = 0.25
COOCCURRENCE_BLEND = 0.3  # peso da co-ocorrência observada (quando houver dados)


class ItemBasedRecommender:
    def __init__(
        self,
        roles: Sequence[Role],
        idf: Mapping[int, float],
        cooccurrence: Mapping[tuple[int, int], float] | None = None,
    ) -> None:
        self._roles = {r.id: r for r in roles}
        self._role_vecs = role_vectors(roles, idf)
        self._neighbors = self._build_neighbors(cooccurrence or {})

    def _build_neighbors(self, cooccurrence: Mapping[tuple[int, int], float]) -> dict[int, list[tuple[int, float]]]:
        # colunas: habilidade -> {cargo: peso}
        columns: dict[int, SparseVec] = {}
        for role_id, vec in self._role_vecs.items():
            for skill_id, w in vec.items():
                columns.setdefault(skill_id, {})[role_id] = w

        max_co = max(cooccurrence.values(), default=0.0)
        skill_ids = sorted(columns)
        sims: dict[int, list[tuple[int, float]]] = {s: [] for s in skill_ids}
        for i, a in enumerate(skill_ids):
            for b in skill_ids[i + 1 :]:
                sim = cosine(columns[a], columns[b])
                if max_co:
                    co = cooccurrence.get((a, b), 0.0) / max_co
                    sim = (1 - COOCCURRENCE_BLEND) * sim + COOCCURRENCE_BLEND * co
                if sim >= MIN_ITEM_SIMILARITY:
                    sims[a].append((b, sim))
                    sims[b].append((a, sim))
        return {s: sorted(n, key=lambda x: -x[1])[:NEIGHBORS_PER_SKILL] for s, n in sims.items()}

    def neighbors(self, skill_id: int) -> list[tuple[int, float]]:
        return list(self._neighbors.get(skill_id, ()))

    def expand(self, vec: SparseVec) -> SparseVec:
        expanded = dict(vec)
        for skill_id, w in vec.items():
            for neighbor, sim in self._neighbors.get(skill_id, ()):
                if neighbor in vec:
                    continue
                expanded[neighbor] = max(expanded.get(neighbor, 0.0), EXPANSION_WEIGHT * w * sim)
        return expanded

    def score_roles(self, profile: UserProfile, *, expand: bool = True) -> dict[int, float]:
        """cosseno perfil × cargo para todos os cargos (0 quando não há sobreposição)."""
        vec = user_vector(profile)
        if expand:
            vec = self.expand(vec)
        return {role_id: cosine(vec, rvec) for role_id, rvec in self._role_vecs.items()}

    def recommend(self, profile: UserProfile, limit: int | None = None) -> list[RecommendedPath]:
        direct = user_vector(profile)
        scores = self.score_roles(profile)
        paths: list[RecommendedPath] = []
        for role_id, score in sorted(scores.items(), key=lambda kv: -kv[1]):
            if score <= 0.0:
                break
            role = self._roles[role_id]
            matched = tuple(rs.skill_id for rs in role.skills if rs.skill_id in direct)
            paths.append(
                RecommendedPath(
                    role=role,
                    confidence_score=min(1.0, score),
                    source=RecommendationSource.ITEM_BASED,
                    matched_skill_ids=matched,
                    score_breakdown={"item_based": score},
                )
            )
            if limit is not None and len(paths) >= limit:
                break
        return paths
