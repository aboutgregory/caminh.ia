"""Vetores esparsos de habilidades (dict skill_id -> peso) e operações básicas.

Python puro: com ~80 habilidades e ~100 cargos no MVP, numpy não compensa a
dependência. Fase 2 troca isto por embeddings densos + Faiss.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from carrermatch.recommender.models.domain import Experience, Role, UserProfile

SparseVec = dict[int, float]


def cosine(a: Mapping[int, float], b: Mapping[int, float]) -> float:
    if not a or not b:
        return 0.0
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(w * large.get(k, 0.0) for k, w in small.items())
    if dot <= 0.0:
        return 0.0
    na = math.sqrt(sum(w * w for w in a.values()))
    nb = math.sqrt(sum(w * w for w in b.values()))
    return dot / (na * nb)


def experience_weight(exp: Experience) -> float:
    """Peso de uma experiência no perfil, em [0.5, 1.0].

    Média de emotional_impact, mastery_level e recognition_score, comprimida para
    que uma experiência marcada como "baixa" ainda conte (piso 0.5).
    RN-09: `exp.kind` NÃO participa — experiência pessoal pesa como profissional.
    """
    mean = (exp.emotional_impact + exp.mastery_level + exp.recognition_score) / 3.0
    return 0.5 + 0.5 * mean


def user_vector(profile: UserProfile) -> SparseVec:
    vec: SparseVec = {}
    for exp in profile.experiences:
        factor = experience_weight(exp)
        for es in exp.skills:
            vec[es.skill_id] = vec.get(es.skill_id, 0.0) + factor * es.weight
    return vec


def skill_sources(profile: UserProfile) -> dict[int, set[int]]:
    """skill_id -> índices das experiências em que a habilidade apareceu.

    Base do bônus de combinação: um caminho sustentado por várias experiências
    diferentes é exatamente a proposta de valor do produto.
    """
    sources: dict[int, set[int]] = {}
    for idx, exp in enumerate(profile.experiences):
        for es in exp.skills:
            sources.setdefault(es.skill_id, set()).add(idx)
    return sources


def role_vector(role: Role, idf: Mapping[int, float]) -> SparseVec:
    return {rs.skill_id: rs.importance * idf.get(rs.skill_id, 1.0) for rs in role.skills}


def role_vectors(roles: Sequence[Role], idf: Mapping[int, float]) -> dict[int, SparseVec]:
    return {role.id: role_vector(role, idf) for role in roles}
