"""Extração de habilidades a partir de texto livre (TF-IDF sobre o vocabulário).

MVP: casamento de aliases do vocabulário controlado + ponderação TF-IDF, em que
o "corpus" para o IDF são os vetores de habilidades dos cargos. Habilidades que
aparecem em muitos cargos (ex.: comunicação) pesam menos que as distintivas
(ex.: longevidade). Fase 2: sentence-transformers substituem o casamento literal.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence

from carrermatch.recommender.models.domain import Experience, ExperienceSkill, Role, Skill


def normalize(text: str) -> str:
    """minúsculas, sem acentos, espaços colapsados."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents).strip()


def skill_idf(skills: Iterable[Skill], roles: Sequence[Role]) -> dict[int, float]:
    """IDF suavizado: log((1 + N) / (1 + df)) + 1, df = nº de cargos que usam a habilidade."""
    df = Counter(rs.skill_id for role in roles for rs in role.skills)
    n = len(roles)
    return {s.id: math.log((1 + n) / (1 + df.get(s.id, 0))) + 1.0 for s in skills}


class SkillExtractor:
    def __init__(self, skills: Sequence[Skill], idf: dict[int, float]) -> None:
        self._idf = idf
        # um padrão por habilidade, com os aliases mais longos primeiro para que
        # "disciplina corporal" seja consumido antes de "disciplina" na mesma habilidade
        self._patterns: list[tuple[int, re.Pattern[str]]] = []
        for skill in skills:
            terms = {normalize(a) for a in skill.aliases} | {normalize(skill.name)}
            alternation = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True) if t)
            if alternation:
                self._patterns.append((skill.id, re.compile(rf"(?<!\w)(?:{alternation})(?!\w)")))

    def extract(self, text: str) -> tuple[ExperienceSkill, ...]:
        """Retorna as habilidades do texto com peso TF-IDF normalizado para (0, 1]."""
        norm = normalize(text)
        tf: dict[int, int] = {}
        for skill_id, pattern in self._patterns:
            hits = len(pattern.findall(norm))
            if hits:
                tf[skill_id] = hits
        if not tf:
            return ()
        raw = {sid: (1 + math.log(count)) * self._idf.get(sid, 1.0) for sid, count in tf.items()}
        top = max(raw.values())
        return tuple(
            ExperienceSkill(skill_id=sid, weight=round(w / top, 4), frequency=tf[sid])
            for sid, w in sorted(raw.items(), key=lambda kv: -kv[1])
        )

    def enrich(self, experience: Experience) -> Experience:
        """Copia a experiência preenchendo `skills` (mantém as já informadas, se houver)."""
        if experience.skills:
            return experience
        return Experience(
            raw_text=experience.raw_text,
            kind=experience.kind,
            emotional_impact=experience.emotional_impact,
            mastery_level=experience.mastery_level,
            recognition_score=experience.recognition_score,
            skills=self.extract(experience.raw_text),
            id=experience.id,
        )
