"""Gera `seed.sql` a partir dos JSONs curados.

    python -m carrermatch.db.seeds.build_seed

SQL idempotente (ON CONFLICT DO UPDATE / DELETE+INSERT nas tabelas de junção),
com INSERTs multi-linha agrupados por tabela. Cada bloco entre marcadores
`-- @chunk` é autocontido (traz o próprio search_path), para poder ser aplicado
separadamente por ferramentas com limite de tamanho (ex.: MCP do Supabase).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from carrermatch.db.seeds.loader import load_seed

OUT = Path(__file__).resolve().parent / "seed.sql"
HEADER = "SET search_path = app, public;"


def q(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def arr_text(values) -> str:
    return "ARRAY[" + ", ".join(q(v) for v in values) + "]::text[]" if values else "'{}'::text[]"


def arr_int(values) -> str:
    return "ARRAY[" + ", ".join(str(v) for v in values) + "]::int[]" if values else "'{}'::int[]"


def insert(table: str, cols: str, rows: Iterable[str], conflict: str = "") -> str:
    body = ",\n".join(f"  ({r})" for r in rows)
    return f"INSERT INTO {table} ({cols}) VALUES\n{body}\n{conflict};".replace("\n;", ";")


def chunks() -> list[tuple[str, str]]:
    seed = load_seed()
    raw_role_by_id = {r["id"]: r for r in seed.raw_roles}
    out: list[tuple[str, str]] = []

    out.append(("setores e habilidades", "\n".join([
        insert("sectors", "id, slug", (f"{s['id']}, {q(s['slug'])}" for s in seed.raw_sectors),
               "ON CONFLICT (id) DO UPDATE SET slug = EXCLUDED.slug"),
        insert("sectors_i18n", "sector_id, locale, name",
               (f"{s['id']}, '{loc}', {q(s[key])}" for s in seed.raw_sectors for loc, key in (("pt-BR", "pt"), ("en", "en"))),
               "ON CONFLICT (sector_id, locale) DO UPDATE SET name = EXCLUDED.name"),
        insert("skills", "id, slug, category", (f"{s['id']}, {q(s['slug'])}, {q(s['cat'])}" for s in seed.raw_skills),
               "ON CONFLICT (id) DO UPDATE SET slug = EXCLUDED.slug, category = EXCLUDED.category"),
        insert("skills_i18n", "skill_id, locale, name, aliases",
               [f"{s['id']}, 'pt-BR', {q(s['pt'])}, {arr_text(s['aliases'])}" for s in seed.raw_skills]
               + [f"{s['id']}, 'en', {q(s['en'])}, '{{}}'::text[]" for s in seed.raw_skills],
               "ON CONFLICT (skill_id, locale) DO UPDATE SET name = EXCLUDED.name, aliases = EXCLUDED.aliases"),
    ])))

    role_ids = ", ".join(str(r.id) for r in seed.roles)
    out.append(("cargos", "\n".join([
        insert("roles", "id, slug, sector_id, market_trend, is_hybrid",
               (f"{r.id}, {q(r.slug)}, {r.sector_id}, '{r.market_trend.value}', {str(r.is_hybrid).lower()}" for r in seed.roles),
               "ON CONFLICT (id) DO UPDATE SET slug = EXCLUDED.slug, sector_id = EXCLUDED.sector_id, "
               "market_trend = EXCLUDED.market_trend, is_hybrid = EXCLUDED.is_hybrid"),
        insert("roles_i18n", "role_id, locale, title",
               (f"{r.id}, '{loc}', {q(raw_role_by_id[r.id][key])}"
                for r in seed.roles for loc, key in (("pt-BR", "pt"), ("en", "en"))),
               "ON CONFLICT (role_id, locale) DO UPDATE SET title = EXCLUDED.title"),
        f"DELETE FROM role_skills WHERE role_id IN ({role_ids});",
        insert("role_skills", "role_id, skill_id, importance",
               (f"{r.id}, {rs.skill_id}, {rs.importance}" for r in seed.roles for rs in r.skills)),
        f"DELETE FROM role_sectors WHERE role_id IN ({role_ids});",
        insert("role_sectors", "role_id, sector_id",
               (f"{r.id}, {sid}" for r in seed.roles for sid in r.related_sector_ids)),
    ])))

    out.append(("knowledge graph", insert(
        "career_transitions", "from_role_id, to_role_id, observed_count, confidence, avg_years, bridge_skill_ids, source",
        (f"{t.from_role_id}, {t.to_role_id}, {t.observed_count}, {t.confidence}, {t.avg_years}, "
         f"{arr_int(t.bridge_skill_ids)}, 'curated'" for t in seed.transitions),
        "ON CONFLICT (from_role_id, to_role_id) DO UPDATE SET observed_count = EXCLUDED.observed_count, "
        "confidence = EXCLUDED.confidence, avg_years = EXCLUDED.avg_years, bridge_skill_ids = EXCLUDED.bridge_skill_ids",
    )))
    return out


def build() -> str:
    parts = ["-- GERADO por build_seed.py — não editar à mão; edite data/*.json", ""]
    for name, sql in chunks():
        parts += [f"-- @chunk {name}", "BEGIN;", HEADER, sql, "COMMIT;", ""]
    return "\n".join(parts)


def main() -> None:
    seed = load_seed()
    OUT.write_text(build(), encoding="utf-8")
    print(
        f"seed.sql gerado ({OUT.stat().st_size // 1024} KB): {len(seed.sectors)} setores, {len(seed.skills)} habilidades, "
        f"{len(seed.roles)} cargos, {len(seed.transitions)} transições"
    )


if __name__ == "__main__":
    main()
