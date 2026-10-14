"""Contratos HTTP de mentoria (PRD §6.4) — espelham `.collab/tasks/004-sprint3-frontend.md`."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from carrermatch.api.schemas.recommendation_schema import clean_experiences
from carrermatch.recommender.services.pii import clean_user_text


class MentorMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: int = Field(ge=1)
    # opcional: sem isso, usa as experiências salvas do usuário (consent_data=true antes)
    experiences: list[str] | None = None

    @field_validator("experiences")
    @classmethod
    def _validate_experiences(cls, values: list[str] | None) -> list[str] | None:
        # mesmas regras de POST /recommendations (RN-01/02, limpeza de HTML, tamanhos)
        return None if values is None else clean_experiences(values)


class MentorOut(BaseModel):
    mentor_id: UUID
    display_name: str
    headline: str | None
    similarity_score: float = Field(ge=0, le=1)
    match_reasons: list[str]


class MentorMatchResponse(BaseModel):
    role_id: int
    mentors: list[MentorOut] = Field(max_length=5)


class MentorContactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: int = Field(ge=1)
    message: str = Field(min_length=20, max_length=1000)

    @field_validator("message")
    @classmethod
    def _clean(cls, value: str) -> str:
        cleaned = clean_user_text(value)
        if len(cleaned) < 20:
            raise ValueError("conte um pouco mais sobre o que você busca na mentoria (mínimo 20 caracteres)")
        return cleaned


class MentorContactResponse(BaseModel):
    match_id: UUID
    status: Literal["requested"] = "requested"
