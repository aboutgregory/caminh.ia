"""MentorMatcher — user-based collaborative filtering para mentoria (PRD §6.4).

score = W_PEER · cos(mentorado, mentor)        "quem já viveu algo parecido com você"
      + W_ROLE · cos(mentor, cargo-alvo)       "quem já está no caminho que você quer seguir"

Os dois termos importam: um mentor idêntico ao mentorado mas sem nada do cargo
alvo não ajuda na transição, e um especialista no cargo sem nenhuma ponte com a
trajetória do mentorado tende a dar conselhos genéricos. Mentores sem nenhuma
habilidade do cargo-alvo (fit = 0) são descartados.

MVP: cálculo sob demanda (poucos mentores). Com a base crescendo, o termo
mentorado×mentor passa a vir do cache `user_similarities` (batch diário, ADR-03).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from carrermatch.recommender.engines.vectors import SparseVec, cosine, role_vector
from carrermatch.recommender.models.domain import Role

W_PEER = 0.5
W_ROLE = 0.5
TOP_K = 5
MAX_REASONS = 3


@dataclass(frozen=True, slots=True)
class MentorProfile:
    id: UUID
    display_name: str
    headline: str | None
    skills: Mapping[int, float]   # vetor agregado das experiências do mentor


@dataclass(frozen=True, slots=True)
class MentorMatch:
    mentor: MentorProfile
    similarity_score: float        # [0, 1]
    peer_similarity: float
    role_fit: float
    reason_skill_ids: tuple[int, ...]


class MentorMatcher:
    def __init__(self, idf: Mapping[int, float]) -> None:
        self._idf = idf

    def _weighted(self, vec: Mapping[int, float]) -> SparseVec:
        # mesmo espaço TF-IDF dos cargos: habilidades raras pesam mais que as genéricas
        return {s: w * self._idf.get(s, 1.0) for s, w in vec.items()}

    def match(
        self,
        mentee_skills: Mapping[int, float],
        target_role: Role,
        mentors: Sequence[MentorProfile],
        *,
        exclude: UUID | None = None,
        k: int = TOP_K,
    ) -> list[MentorMatch]:
        mentee = self._weighted(mentee_skills)
        rvec = role_vector(target_role, self._idf)
        role_importance = {rs.skill_id: rs.importance for rs in target_role.skills}

        matches: list[MentorMatch] = []
        for mentor in mentors:
            if mentor.id == exclude or not mentor.skills:
                continue
            mvec = self._weighted(mentor.skills)
            fit = cosine(mvec, rvec)
            if fit <= 0.0:
                continue
            peer = cosine(mentee, mvec)
            score = W_PEER * peer + W_ROLE * fit
            # razões: habilidades do cargo que o mentor domina, priorizando as que o mentorado também tem
            shared = [s for s in mentor.skills if s in role_importance]
            shared.sort(key=lambda s: (s not in mentee_skills, -role_importance[s], -mentor.skills[s]))
            matches.append(MentorMatch(mentor, round(min(1.0, score), 4), round(peer, 4), round(fit, 4),
                                       tuple(shared[:MAX_REASONS])))
        matches.sort(key=lambda m: (-m.similarity_score, str(m.mentor.id)))  # desempate estável
        return matches[:k]
