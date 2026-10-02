"""Entidades de domínio puras do recomendador.

Sem dependência de banco, framework ou I/O — os engines operam só sobre estes
tipos, o que mantém tudo testável offline via InMemoryRepository.

Escalas: todo score interno é float em [0, 1]. A conversão para estrelas (1–5)
acontece apenas na borda da API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

# RN-03 / RN-04 / RN-05
MIN_PATHS = 6
MAX_PATHS = 21
# RN-01 / RN-02
MIN_EXPERIENCES = 3
MAX_EXPERIENCES = 5


class MarketTrend(StrEnum):
    EM_ALTA = "em_alta"
    ESTAVEL = "estavel"
    EMERGENTE = "emergente"

    @property
    def label(self) -> str:
        return {"em_alta": "Em Alta", "estavel": "Estável", "emergente": "Emergente"}[self.value]


class ExperienceKind(StrEnum):
    PROFESSIONAL = "professional"
    PERSONAL = "personal"
    EDUCATION = "education"
    VOLUNTEER = "volunteer"


class RecommendationSource(StrEnum):
    ITEM_BASED = "item_based"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    HYBRID = "hybrid"


def _check_unit(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} deve estar em [0, 1], recebido {value}")


@dataclass(frozen=True, slots=True)
class Sector:
    id: int
    slug: str
    name: str


@dataclass(frozen=True, slots=True)
class Skill:
    id: int
    slug: str
    name: str
    category: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RoleSkill:
    skill_id: int
    importance: float

    def __post_init__(self) -> None:
        if not 0.0 < self.importance <= 1.0:
            raise ValueError(f"importance deve estar em (0, 1], recebido {self.importance}")


@dataclass(frozen=True, slots=True)
class Role:
    id: int
    slug: str
    title: str
    sector_id: int
    market_trend: MarketTrend
    is_hybrid: bool = False
    skills: tuple[RoleSkill, ...] = ()
    related_sector_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ExperienceSkill:
    skill_id: int
    weight: float
    frequency: int = 1

    def __post_init__(self) -> None:
        if not 0.0 < self.weight <= 1.0:
            raise ValueError(f"weight deve estar em (0, 1], recebido {self.weight}")


@dataclass(frozen=True, slots=True)
class Experience:
    """Uma experiência relatada pelo usuário.

    RN-09: `kind` é registrado para analytics, mas NUNCA entra na ponderação.
    Uma experiência pessoal pesa o mesmo que uma profissional formal.
    """

    raw_text: str
    kind: ExperienceKind = ExperienceKind.PROFESSIONAL
    emotional_impact: float = 0.5
    mastery_level: float = 0.5
    recognition_score: float = 0.5
    skills: tuple[ExperienceSkill, ...] = ()
    id: UUID | None = None

    def __post_init__(self) -> None:
        if not self.raw_text.strip():
            raise ValueError("raw_text não pode ser vazio")
        _check_unit("emotional_impact", self.emotional_impact)
        _check_unit("mastery_level", self.mastery_level)
        _check_unit("recognition_score", self.recognition_score)


@dataclass(frozen=True, slots=True)
class UserProfile:
    experiences: tuple[Experience, ...]
    user_id: UUID | None = None
    risk_tolerance: float = 0.5  # 0 = conservador, 1 = aceita caminhos emergentes/distantes

    def __post_init__(self) -> None:
        n = len(self.experiences)
        if not MIN_EXPERIENCES <= n <= MAX_EXPERIENCES:
            raise ValueError(
                f"perfil exige entre {MIN_EXPERIENCES} e {MAX_EXPERIENCES} experiências, recebido {n}"
            )
        _check_unit("risk_tolerance", self.risk_tolerance)


@dataclass(frozen=True, slots=True)
class CareerTransition:
    from_role_id: int
    to_role_id: int
    observed_count: int
    confidence: float
    avg_years: float | None = None
    bridge_skill_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.from_role_id == self.to_role_id:
            raise ValueError("transição não pode ligar um cargo a ele mesmo")
        _check_unit("confidence", self.confidence)


@dataclass(slots=True)
class RecommendedPath:
    """Saída do pipeline. Mutável porque o ClaudeDescriptionService preenche
    `description` depois do ranking."""

    role: Role
    confidence_score: float
    source: RecommendationSource
    matched_skill_ids: tuple[int, ...] = ()   # habilidades do usuário que sustentam o caminho
    key_skill_ids: tuple[int, ...] = ()       # as 5 habilidades-chave exibidas
    industry_ids: tuple[int, ...] = ()        # as 3 indústrias exibidas
    description: str | None = None
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_unit("confidence_score", self.confidence_score)

    @property
    def relevance_stars(self) -> int:
        """1–5 estrelas a partir do confidence_score."""
        return max(1, min(5, round(self.confidence_score * 5 + 0.0001)))
