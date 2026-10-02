"""Carrega o seed curado (JSON) como objetos de domínio.

Fonte única da verdade do vocabulário inicial: os mesmos JSONs alimentam o
InMemoryRepository dos testes e o SQL gerado por `build_seed.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from carrermatch.recommender.models.domain import (
    CareerTransition,
    MarketTrend,
    Role,
    RoleSkill,
    Sector,
    Skill,
)
from carrermatch.recommender.repositories.recommender_repo import InMemoryRepository

DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class SeedData:
    sectors: tuple[Sector, ...]
    skills: tuple[Skill, ...]
    roles: tuple[Role, ...]
    transitions: tuple[CareerTransition, ...]
    # payload bruto, para o build_seed gerar i18n EN
    raw_sectors: tuple[dict, ...]
    raw_skills: tuple[dict, ...]
    raw_roles: tuple[dict, ...]


def _read(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@cache
def load_seed() -> SeedData:
    raw_sectors = _read("sectors.json")
    raw_skills = _read("skills.json")
    raw_roles = _read("roles.json")
    raw_transitions = _read("transitions.json")["transitions"]

    sector_by_slug = {s["slug"]: s["id"] for s in raw_sectors}
    skill_by_slug = {s["slug"]: s["id"] for s in raw_skills}
    _assert_unique("sector", raw_sectors)
    _assert_unique("skill", raw_skills)
    _assert_unique("role", raw_roles)

    sectors = tuple(Sector(id=s["id"], slug=s["slug"], name=s["pt"]) for s in raw_sectors)
    skills = tuple(
        Skill(id=s["id"], slug=s["slug"], name=s["pt"], category=s["cat"], aliases=tuple(s["aliases"]))
        for s in raw_skills
    )

    roles: list[Role] = []
    for r in raw_roles:
        try:
            sector_ids = [sector_by_slug[slug] for slug in r["sectors"]]
            role_skills = tuple(
                RoleSkill(skill_id=skill_by_slug[slug], importance=imp) for slug, imp in r["skills"].items()
            )
        except KeyError as exc:
            raise ValueError(f"role {r['slug']}: referência desconhecida {exc}") from None
        roles.append(
            Role(
                id=r["id"],
                slug=r["slug"],
                title=r["pt"],
                sector_id=sector_ids[0],
                market_trend=MarketTrend(r["trend"]),
                is_hybrid=r["hybrid"],
                skills=role_skills,
                related_sector_ids=tuple(sector_ids),
            )
        )

    role_by_slug = {r.slug: r for r in roles}
    transitions: list[CareerTransition] = []
    seen: set[tuple[int, int]] = set()
    for row in raw_transitions:
        from_slug, to_slug, confidence, count, years = row
        try:
            src, dst = role_by_slug[from_slug], role_by_slug[to_slug]
        except KeyError as exc:
            raise ValueError(f"transição {from_slug}->{to_slug}: cargo desconhecido {exc}") from None
        if (src.id, dst.id) in seen:
            raise ValueError(f"transição duplicada {from_slug}->{to_slug}")
        seen.add((src.id, dst.id))
        transitions.append(
            CareerTransition(
                from_role_id=src.id,
                to_role_id=dst.id,
                observed_count=count,
                confidence=confidence,
                avg_years=years,
                bridge_skill_ids=_bridge_skills(src, dst),
            )
        )

    return SeedData(
        sectors=sectors,
        skills=skills,
        roles=tuple(roles),
        transitions=tuple(transitions),
        raw_sectors=tuple(raw_sectors),
        raw_skills=tuple(raw_skills),
        raw_roles=tuple(raw_roles),
    )


def _bridge_skills(src: Role, dst: Role) -> tuple[int, ...]:
    """Habilidades compartilhadas entre origem e destino, ordenadas pela
    importância no destino — o que "leva" a pessoa de um cargo ao outro."""
    src_ids = {rs.skill_id for rs in src.skills}
    shared = [rs for rs in dst.skills if rs.skill_id in src_ids]
    return tuple(rs.skill_id for rs in sorted(shared, key=lambda rs: -rs.importance))


def _assert_unique(kind: str, rows: list[dict]) -> None:
    for key in ("id", "slug"):
        values = [r[key] for r in rows]
        dupes = {v for v in values if values.count(v) > 1}
        if dupes:
            raise ValueError(f"{kind}: {key} duplicado {sorted(dupes)}")


def seed_repository() -> InMemoryRepository:
    seed = load_seed()
    return InMemoryRepository(
        sectors=seed.sectors, skills=seed.skills, roles=seed.roles, transitions=seed.transitions
    )
