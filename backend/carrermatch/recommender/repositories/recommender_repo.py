"""Repository Pattern do recomendador.

Os engines dependem apenas do Protocol `RecommenderRepository`. Duas
implementações:

- `PostgresRecommenderRepository` — asyncpg, raw SQL (produção).
- `InMemoryRepository` — dicionários em memória (testes e validação offline).

O vocabulário (skills/roles/sectors/transições) muda raramente e é pequeno no
MVP, então ambas as implementações o carregam inteiro e os engines trabalham em
memória. Se `career_transitions` passar de ~50k linhas (ADR-03), trocar
`list_transitions` por consultas por vizinhança.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol, runtime_checkable

import asyncpg

from carrermatch.recommender.models.domain import (
    CareerTransition,
    MarketTrend,
    Role,
    RoleSkill,
    Sector,
    Skill,
)

LOCALE = "pt-BR"


@runtime_checkable
class RecommenderRepository(Protocol):
    async def list_sectors(self) -> Sequence[Sector]: ...

    async def list_skills(self) -> Sequence[Skill]: ...

    async def list_roles(self) -> Sequence[Role]: ...

    async def list_transitions(self) -> Sequence[CareerTransition]: ...

    async def skill_cooccurrence(self) -> dict[tuple[int, int], float]:
        """Co-ocorrência observada de habilidades em experiências reais de
        usuários, par (a, b) com a < b → soma dos produtos de peso. Vazio no
        cold start; o item-based então usa só `role_skills`."""
        ...


class InMemoryRepository:
    def __init__(
        self,
        sectors: Iterable[Sector] = (),
        skills: Iterable[Skill] = (),
        roles: Iterable[Role] = (),
        transitions: Iterable[CareerTransition] = (),
        cooccurrence: dict[tuple[int, int], float] | None = None,
    ) -> None:
        self._sectors = {s.id: s for s in sectors}
        self._skills = {s.id: s for s in skills}
        self._roles = {r.id: r for r in roles}
        self._transitions = list(transitions)
        self._cooccurrence = dict(cooccurrence or {})
        self._validate_refs()

    def _validate_refs(self) -> None:
        for role in self._roles.values():
            if self._sectors and role.sector_id not in self._sectors:
                raise ValueError(f"role {role.slug}: setor {role.sector_id} inexistente")
            for rs in role.skills:
                if self._skills and rs.skill_id not in self._skills:
                    raise ValueError(f"role {role.slug}: skill {rs.skill_id} inexistente")
        for t in self._transitions:
            if self._roles and (t.from_role_id not in self._roles or t.to_role_id not in self._roles):
                raise ValueError(f"transição {t.from_role_id}->{t.to_role_id} referencia cargo inexistente")

    async def list_sectors(self) -> Sequence[Sector]:
        return list(self._sectors.values())

    async def list_skills(self) -> Sequence[Skill]:
        return list(self._skills.values())

    async def list_roles(self) -> Sequence[Role]:
        return list(self._roles.values())

    async def list_transitions(self) -> Sequence[CareerTransition]:
        return list(self._transitions)

    async def skill_cooccurrence(self) -> dict[tuple[int, int], float]:
        return dict(self._cooccurrence)


class PostgresRecommenderRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_sectors(self) -> Sequence[Sector]:
        rows = await self._pool.fetch(
            """
            SELECT s.id, s.slug, i.name
            FROM sectors s JOIN sectors_i18n i ON i.sector_id = s.id AND i.locale = $1
            ORDER BY s.id
            """,
            LOCALE,
        )
        return [Sector(id=r["id"], slug=r["slug"], name=r["name"]) for r in rows]

    async def list_skills(self) -> Sequence[Skill]:
        rows = await self._pool.fetch(
            """
            SELECT s.id, s.slug, s.category, i.name, i.aliases
            FROM skills s JOIN skills_i18n i ON i.skill_id = s.id AND i.locale = $1
            ORDER BY s.id
            """,
            LOCALE,
        )
        return [
            Skill(id=r["id"], slug=r["slug"], name=r["name"], category=r["category"], aliases=tuple(r["aliases"]))
            for r in rows
        ]

    async def list_roles(self) -> Sequence[Role]:
        async with self._pool.acquire() as conn:
            roles = await conn.fetch(
                """
                SELECT r.id, r.slug, r.sector_id, r.market_trend::text AS market_trend, r.is_hybrid, i.title
                FROM roles r JOIN roles_i18n i ON i.role_id = r.id AND i.locale = $1
                ORDER BY r.id
                """,
                LOCALE,
            )
            skills = await conn.fetch("SELECT role_id, skill_id, importance FROM role_skills")
            sectors = await conn.fetch("SELECT role_id, sector_id FROM role_sectors ORDER BY role_id, sector_id")

        skills_by_role: dict[int, list[RoleSkill]] = {}
        for r in skills:
            skills_by_role.setdefault(r["role_id"], []).append(
                RoleSkill(skill_id=r["skill_id"], importance=r["importance"])
            )
        sectors_by_role: dict[int, list[int]] = {}
        for r in sectors:
            sectors_by_role.setdefault(r["role_id"], []).append(r["sector_id"])

        return [
            Role(
                id=r["id"],
                slug=r["slug"],
                title=r["title"],
                sector_id=r["sector_id"],
                market_trend=MarketTrend(r["market_trend"]),
                is_hybrid=r["is_hybrid"],
                skills=tuple(skills_by_role.get(r["id"], ())),
                related_sector_ids=tuple(sectors_by_role.get(r["id"], ())),
            )
            for r in roles
        ]

    async def list_transitions(self) -> Sequence[CareerTransition]:
        rows = await self._pool.fetch(
            """
            SELECT from_role_id, to_role_id, observed_count, confidence, avg_years, bridge_skill_ids
            FROM career_transitions
            """
        )
        return [
            CareerTransition(
                from_role_id=r["from_role_id"],
                to_role_id=r["to_role_id"],
                observed_count=r["observed_count"],
                confidence=r["confidence"],
                avg_years=r["avg_years"],
                bridge_skill_ids=tuple(r["bridge_skill_ids"]),
            )
            for r in rows
        ]

    async def skill_cooccurrence(self) -> dict[tuple[int, int], float]:
        rows = await self._pool.fetch(
            """
            SELECT a.skill_id AS a, b.skill_id AS b, SUM(a.weight * b.weight) AS w
            FROM experience_skills a
            JOIN experience_skills b ON b.experience_id = a.experience_id AND a.skill_id < b.skill_id
            GROUP BY a.skill_id, b.skill_id
            """
        )
        return {(r["a"], r["b"]): float(r["w"]) for r in rows}
