"""Repositórios de mentoria e de conta (LGPD).

Identidade: o backend só conhece o `sub` do Supabase Auth; `users.auth_provider_id`
faz a ponte para o `users.id` interno.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import asyncpg

from carrermatch.recommender.engines.mentor_matcher import MentorProfile


class MentorUnavailableError(Exception):
    """Mentor inexistente, não-mentor ou não disponível."""


class DuplicateRequestError(Exception):
    """Já existe solicitação pendente deste mentorado para este mentor."""


@dataclass(frozen=True, slots=True)
class MentorRequest:
    mentee_auth_id: UUID
    mentee_email: str | None
    mentor_id: UUID
    role_id: int
    similarity_score: float
    message: str


class MentorRepository(Protocol):
    async def list_available_mentors(self) -> Sequence[MentorProfile]: ...

    async def user_skills(self, auth_id: UUID) -> dict[int, float] | None:
        """Vetor de habilidades das experiências SALVAS do usuário (None = nada salvo)."""
        ...

    async def create_request(self, req: MentorRequest) -> UUID: ...


class AccountRepository(Protocol):
    async def export_user_data(self, auth_id: UUID) -> dict[str, Any] | None: ...

    async def delete_user(self, auth_id: UUID) -> dict[str, int] | None:
        """Hard delete de tudo do usuário. Retorna contagens por tabela (None = usuário não existe)."""
        ...

    async def audit(self, event_type: str, details: dict[str, Any]) -> None: ...


class AccountStore(MentorRepository, AccountRepository, Protocol):
    """O que as rotas de mentoria e de conta precisam (uma implementação atende às duas)."""


# --------------------------------------------------------------------- memória
@dataclass
class InMemoryAccountStore:
    """Implementa MentorRepository e AccountRepository para testes."""

    mentors: list[MentorProfile] = field(default_factory=list)
    available: set[UUID] = field(default_factory=set)
    saved_skills: dict[UUID, dict[int, float]] = field(default_factory=dict)   # auth_id → vetor
    users: dict[UUID, dict[str, Any]] = field(default_factory=dict)            # auth_id → dados exportáveis
    requests: list[tuple[UUID, MentorRequest]] = field(default_factory=list)
    audit_log: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    async def list_available_mentors(self) -> Sequence[MentorProfile]:
        return [m for m in self.mentors if m.id in self.available]

    async def user_skills(self, auth_id: UUID) -> dict[int, float] | None:
        return self.saved_skills.get(auth_id)

    async def create_request(self, req: MentorRequest) -> UUID:
        if req.mentor_id not in self.available:
            raise MentorUnavailableError
        if any(r.mentee_auth_id == req.mentee_auth_id and r.mentor_id == req.mentor_id for _, r in self.requests):
            raise DuplicateRequestError
        match_id = uuid4()
        self.requests.append((match_id, req))
        return match_id

    async def export_user_data(self, auth_id: UUID) -> dict[str, Any] | None:
        return self.users.get(auth_id)

    async def delete_user(self, auth_id: UUID) -> dict[str, int] | None:
        if auth_id not in self.users:
            return None
        self.users.pop(auth_id)
        self.saved_skills.pop(auth_id, None)
        removed = [r for r in self.requests if r[1].mentee_auth_id == auth_id]
        self.requests = [r for r in self.requests if r[1].mentee_auth_id != auth_id]
        counts = {"users": 1, "mentor_matches": len(removed)}
        self.audit_log.append(("account_deleted", {"linhas_removidas": counts}))  # como no Postgres: mesma "transação"
        return counts

    async def audit(self, event_type: str, details: dict[str, Any]) -> None:
        self.audit_log.append((event_type, details))


# --------------------------------------------------------------------- postgres
_MENTORS_SQL = """
SELECT u.id, COALESCE(u.display_name, 'Mentor(a)') AS display_name, u.mentor_headline,
       es.skill_id, SUM(es.weight * (0.5 + 0.5 * (e.emotional_impact + e.mastery_level + e.recognition_score) / 3)) AS w
FROM users u
JOIN experiences e        ON e.user_id = u.id
JOIN experience_skills es ON es.experience_id = e.id
WHERE u.is_mentor AND u.mentor_status = 'available'
GROUP BY u.id, u.display_name, u.mentor_headline, es.skill_id
"""

_USER_SKILLS_SQL = """
SELECT es.skill_id, SUM(es.weight * (0.5 + 0.5 * (e.emotional_impact + e.mastery_level + e.recognition_score) / 3)) AS w
FROM users u
JOIN experiences e        ON e.user_id = u.id
JOIN experience_skills es ON es.experience_id = e.id
WHERE u.auth_provider_id = $1
GROUP BY es.skill_id
"""

# ordem de exclusão: tabelas com ON DELETE SET NULL primeiro (senão o dado sobreviveria
# anonimizado-pela-metade); o resto sai por cascata a partir de users.
_DELETE_STEPS: tuple[tuple[str, str], ...] = (
    ("behavioral_events", "DELETE FROM behavioral_events WHERE user_id = $1"),
    ("recommendation_feedback", "DELETE FROM recommendation_feedback WHERE user_id = $1"),
    ("mentor_matches", "DELETE FROM mentor_matches WHERE $1 IN (mentee_id, mentor_id)"),
    ("career_recommendations", "DELETE FROM career_recommendations WHERE user_id = $1"),
    ("experiences", "DELETE FROM experiences WHERE user_id = $1"),          # cascata: experience_skills
    ("onboarding_responses", "DELETE FROM onboarding_responses WHERE user_id = $1"),
    ("user_similarities", "DELETE FROM user_similarities WHERE $1 IN (user_a, user_b)"),
    ("plasticity_nodes", "DELETE FROM plasticity_nodes WHERE user_id = $1"),  # cascata: plasticity_edges
    ("ltp_predictions", "DELETE FROM ltp_predictions WHERE user_id = $1"),
    ("users", "DELETE FROM users WHERE id = $1"),
)


def _count(status: str) -> int:
    # asyncpg devolve "DELETE n"
    return int(status.rsplit(" ", 1)[-1]) if status.startswith("DELETE") else 0


class PostgresAccountRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_available_mentors(self) -> Sequence[MentorProfile]:
        rows = await self._pool.fetch(_MENTORS_SQL)
        by_user: dict[UUID, dict[str, Any]] = {}
        for r in rows:
            entry = by_user.setdefault(r["id"], {"name": r["display_name"], "headline": r["mentor_headline"], "skills": {}})
            entry["skills"][r["skill_id"]] = float(r["w"])
        return [MentorProfile(uid, d["name"], d["headline"], d["skills"]) for uid, d in by_user.items()]

    async def user_skills(self, auth_id: UUID) -> dict[int, float] | None:
        rows = await self._pool.fetch(_USER_SKILLS_SQL, str(auth_id))
        return {r["skill_id"]: float(r["w"]) for r in rows} or None

    async def create_request(self, req: MentorRequest) -> UUID:
        async with self._pool.acquire() as conn, conn.transaction():
            mentor_ok = await conn.fetchval(
                "SELECT true FROM users WHERE id = $1 AND is_mentor AND mentor_status = 'available'", req.mentor_id
            )
            if not mentor_ok:
                raise MentorUnavailableError
            mentee_id = await conn.fetchval(
                """
                INSERT INTO users (auth_provider_id, email) VALUES ($1, $2)
                ON CONFLICT (auth_provider_id) DO UPDATE SET email = COALESCE(EXCLUDED.email, users.email)
                RETURNING id
                """,
                str(req.mentee_auth_id), req.mentee_email,
            )
            if mentee_id == req.mentor_id:
                raise MentorUnavailableError
            try:
                return await conn.fetchval(
                    """
                    INSERT INTO mentor_matches (mentee_id, mentor_id, role_id, similarity_score, message)
                    VALUES ($1, $2, $3, $4, $5) RETURNING id
                    """,
                    mentee_id, req.mentor_id, req.role_id, req.similarity_score, req.message,
                )
            except asyncpg.UniqueViolationError:
                raise DuplicateRequestError from None

    async def export_user_data(self, auth_id: UUID) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id, email, display_name, is_mentor, mentor_status::text, mentor_headline, "
                "consent_data_at, created_at FROM users WHERE auth_provider_id = $1",
                str(auth_id),
            )
            if user is None:
                return None
            uid = user["id"]
            experiences = await conn.fetch(
                """
                SELECT e.position, e.raw_text, e.kind::text, e.created_at,
                       COALESCE(array_agg(si.name ORDER BY es.weight DESC) FILTER (WHERE si.name IS NOT NULL), '{}')
                           AS habilidades
                FROM experiences e
                LEFT JOIN experience_skills es ON es.experience_id = e.id
                LEFT JOIN skills_i18n si ON si.skill_id = es.skill_id AND si.locale = 'pt-BR'
                WHERE e.user_id = $1 GROUP BY e.id ORDER BY e.position
                """,
                uid,
            )
            recs = await conn.fetch(
                """
                SELECT cr.request_id, cr.rank, ri.title, cr.confidence_score, cr.description, cr.created_at
                FROM career_recommendations cr
                JOIN roles_i18n ri ON ri.role_id = cr.role_id AND ri.locale = 'pt-BR'
                WHERE cr.user_id = $1 ORDER BY cr.created_at DESC, cr.rank
                """,
                uid,
            )
            matches = await conn.fetch(
                """
                SELECT CASE WHEN mm.mentee_id = $1 THEN 'mentorado' ELSE 'mentor' END AS papel,
                       mm.status::text, mm.message, mm.created_at, ri.title AS cargo
                FROM mentor_matches mm
                LEFT JOIN roles_i18n ri ON ri.role_id = mm.role_id AND ri.locale = 'pt-BR'
                WHERE $1 IN (mm.mentee_id, mm.mentor_id) ORDER BY mm.created_at DESC
                """,
                uid,
            )
            events = await conn.fetch(
                "SELECT event_type, occurred_at, payload FROM behavioral_events WHERE user_id = $1 ORDER BY occurred_at",
                uid,
            )
        return {
            "conta": {k: v for k, v in dict(user).items() if k != "id"},
            "experiencias": [dict(r) for r in experiences],
            "recomendacoes": [dict(r) for r in recs],
            "mentorias": [dict(r) for r in matches],
            "eventos": [{**dict(r), "payload": json.loads(r["payload"]) if isinstance(r["payload"], str) else r["payload"]}
                        for r in events],
            "exportado_em": datetime.now(UTC),
        }

    async def delete_user(self, auth_id: UUID) -> dict[str, int] | None:
        async with self._pool.acquire() as conn, conn.transaction():
            uid = await conn.fetchval("SELECT id FROM users WHERE auth_provider_id = $1 FOR UPDATE", str(auth_id))
            if uid is None:
                return None
            counts = {}
            for table, sql in _DELETE_STEPS:
                counts[table] = _count(await conn.execute(sql, uid))
            await conn.execute(
                "INSERT INTO audit_log (event_type, details) VALUES ('account_deleted', $1::jsonb)",
                json.dumps({"linhas_removidas": counts}),
            )
            return counts

    async def audit(self, event_type: str, details: dict[str, Any]) -> None:
        await self._pool.execute(
            "INSERT INTO audit_log (event_type, details) VALUES ($1, $2::jsonb)", event_type, json.dumps(details)
        )
