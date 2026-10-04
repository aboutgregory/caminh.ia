"""Repositórios de escrita: eventos comportamentais e recomendações persistidas.

Separados do RecommenderRepository (leitura do vocabulário) porque têm ciclo de
vida e regras de privacidade diferentes.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import asyncpg

from carrermatch.recommender.models.domain import RecommendedPath, UserProfile


@dataclass(frozen=True, slots=True)
class BehavioralEvent:
    event_type: str
    session_id: UUID
    user_auth_id: UUID | None = None   # sub do Supabase; mapeado para users.id no Postgres
    request_id: UUID | None = None
    role_id: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class SavedRecommendation:
    user_auth_id: UUID
    email: str | None
    request_id: UUID
    profile: UserProfile
    paths: tuple[RecommendedPath, ...]
    descriptions: dict[int, str]
    model_version: str


class EventRepository(Protocol):
    async def insert(self, event: BehavioralEvent) -> None: ...


class RecommendationStore(Protocol):
    async def save(self, rec: SavedRecommendation) -> None: ...


class InMemoryEventRepository:
    def __init__(self) -> None:
        self.events: list[BehavioralEvent] = []

    async def insert(self, event: BehavioralEvent) -> None:
        self.events.append(event)


class InMemoryRecommendationStore:
    def __init__(self) -> None:
        self.saved: list[SavedRecommendation] = []

    async def save(self, rec: SavedRecommendation) -> None:
        self.saved.append(rec)


_UPSERT_USER = """
INSERT INTO users (auth_provider_id, email, consent_data_at)
VALUES ($1, $2, now())
ON CONFLICT (auth_provider_id) DO UPDATE
    SET email = COALESCE(EXCLUDED.email, users.email),
        consent_data_at = COALESCE(users.consent_data_at, EXCLUDED.consent_data_at)
RETURNING id
"""


class PostgresEventRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def insert(self, event: BehavioralEvent) -> None:
        await self._pool.execute(
            """
            INSERT INTO behavioral_events (occurred_at, user_id, session_id, event_type, request_id, role_id, payload)
            VALUES ($1, (SELECT id FROM users WHERE auth_provider_id = $2), $3, $4, $5, $6, $7::jsonb)
            """,
            event.occurred_at,
            str(event.user_auth_id) if event.user_auth_id else None,
            event.session_id,
            event.event_type,
            event.request_id,
            event.role_id,
            json.dumps(event.payload, ensure_ascii=False),
        )


class PostgresRecommendationStore:
    """Salva experiências + recomendações de usuário autenticado que consentiu (RN-07, LGPD)."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def save(self, rec: SavedRecommendation) -> None:
        async with self._pool.acquire() as conn, conn.transaction():
            user_id = await conn.fetchval(_UPSERT_USER, str(rec.user_auth_id), rec.email)
            # a última geração substitui o conjunto de experiências (máx. 5 posições, RN-02)
            await conn.execute("DELETE FROM experiences WHERE user_id = $1", user_id)
            for position, exp in enumerate(rec.profile.experiences, 1):
                exp_id = uuid4()
                await conn.execute(
                    """
                    INSERT INTO experiences (id, user_id, position, raw_text, kind,
                                             emotional_impact, mastery_level, recognition_score)
                    VALUES ($1, $2, $3, $4, $5::experience_kind, $6, $7, $8)
                    """,
                    exp_id, user_id, position, exp.raw_text, exp.kind.value,
                    exp.emotional_impact, exp.mastery_level, exp.recognition_score,
                )
                await conn.executemany(
                    "INSERT INTO experience_skills (experience_id, skill_id, weight, frequency) VALUES ($1, $2, $3, $4)",
                    [(exp_id, es.skill_id, es.weight, es.frequency) for es in exp.skills],
                )
            await conn.executemany(
                """
                INSERT INTO career_recommendations (user_id, request_id, role_id, rank, confidence_score, source,
                                                    description, key_skill_ids, model_version)
                VALUES ($1, $2, $3, $4, $5, $6::rec_source, $7, $8, $9)
                """,
                [
                    (user_id, rec.request_id, p.role.id, rank, p.confidence_score, p.source.value,
                     rec.descriptions.get(rank), list(p.key_skill_ids), rec.model_version)
                    for rank, p in enumerate(rec.paths, 1)
                ],
            )


def build_saved(
    *, user_auth_id: UUID, email: str | None, request_id: UUID, profile: UserProfile,
    paths: Sequence[RecommendedPath], descriptions: dict[int, str], model_version: str,
) -> SavedRecommendation:
    return SavedRecommendation(user_auth_id, email, request_id, profile, tuple(paths), descriptions, model_version)
