"""Contratos HTTP de POST /recommendations e POST /events (PRD §6.2)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from carrermatch.recommender.models.domain import MAX_EXPERIENCE_CHARS, MAX_EXPERIENCES, MIN_EXPERIENCES
from carrermatch.recommender.services.pii import clean_user_text

MIN_EXPERIENCE_CHARS = 10


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiences: list[str] = Field(min_length=MIN_EXPERIENCES, max_length=MAX_EXPERIENCES)  # RN-01 / RN-02
    risk_tolerance: float = Field(default=0.5, ge=0, le=1)
    # LGPD: só persiste experiências de usuário autenticado que marcou o consentimento
    consent_data: bool = False

    @field_validator("experiences")
    @classmethod
    def _clean(cls, values: list[str]) -> list[str]:
        cleaned = [clean_user_text(v) for v in values]
        for i, text in enumerate(cleaned, 1):
            if len(text) < MIN_EXPERIENCE_CHARS:
                raise ValueError(f"experiência {i} muito curta: conte o que você fez e o que aprendeu")
            if len(text) > MAX_EXPERIENCE_CHARS:
                raise ValueError(f"experiência {i} passa de {MAX_EXPERIENCE_CHARS} caracteres")
        return cleaned


class CareerPathOut(BaseModel):
    id: int = Field(description="posição no ranking (1 = mais relevante)")
    role_slug: str
    title: str
    description: str
    description_source: Literal["claude", "fallback"]
    key_skills: list[str] = Field(min_length=5, max_length=5)
    relevance: int = Field(ge=1, le=5, description="estrelas")
    confidence_score: float = Field(ge=0, le=1)
    market_trend: Literal["Em Alta", "Estável", "Emergente"]
    industries: list[str] = Field(min_length=1, max_length=3)
    is_hybrid: bool
    source: Literal["item_based", "knowledge_graph", "hybrid"]


class RecommendationResponse(BaseModel):
    request_id: UUID
    model_version: str
    generated_in_ms: int
    saved: bool = Field(description="experiências e caminhos foram salvos na conta (RN-07)")
    paths: list[CareerPathOut] = Field(min_length=6, max_length=21)  # RN-03


ClientEventType = Literal[
    "recommendation_viewed", "career_expanded", "career_saved", "rated_positive", "rated_negative", "dismissed",
]


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: ClientEventType
    request_id: UUID | None = None
    role_id: int | None = Field(default=None, ge=1)
    rating: int | None = Field(default=None, ge=1, le=5)
    reading_time_ms: int | None = Field(default=None, ge=0, le=3_600_000)
