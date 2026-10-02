"""Gera `seed.sql` a partir dos JSONs curados.

    python -m carrermatch.db.seeds.build_seed

O SQL é idempotente (ON CONFLICT DO UPDATE), então pode ser reaplicado depois
de cada revisão da curadoria.
"""

from __future__ import annotations

from pathlib import Path

from carrermatch.db.seeds.loader import load_seed

OUT = Path(__file__).resolve().parent / "seed.sql"


def q(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def arr_text(values) -> str:
    return "ARRAY[" + ", ".join(q(v) for v in values) + "]::text[]" if values else "'{}'::text[]"


def arr_int(values) -> str:
    return "ARRAY[" + ", ".join(str(v) for v in values) + "]::int[]" if values else "'{}'::int[]"


def build() -> str:
    seed = load_seed()
    out: list[str] = ["-- GERADO por build_seed.py — não editar à mão; edite data/*.json", "BEGIN;", ""]

    out.append("-- setores")
    for s in seed.raw_sectors:
        out.append(
            f"INSERT INTO sectors (id, slug) VALUES ({s['id']}, {q(s['slug'])}) "
            "ON CONFLICT (id) DO UPDATE SET slug = EXCLUDED.slug;"
        )
        for locale, key in (("pt-BR", "pt"), ("en", "en")):
            out.append(
                f"INSERT INTO sectors_i18n (sector_id, locale, name) VALUES ({s['id']}, '{locale}', {q(s[key])}) "
                "ON CONFLICT (sector_id, locale) DO UPDATE SET name = EXCLUDED.name;"
            )

    out += ["", "-- habilidades"]
    for s in seed.raw_skills:
        out.append(
            f"INSERT INTO skills (id, slug, category) VALUES ({s['id']}, {q(s['slug'])}, {q(s['cat'])}) "
            "ON CONFLICT (id) DO UPDATE SET slug = EXCLUDED.slug, category = EXCLUDED.category;"
        )
        out.append(
            f"INSERT INTO skills_i18n (skill_id, locale, name, aliases) VALUES "
            f"({s['id']}, 'pt-BR', {q(s['pt'])}, {arr_text(s['aliases'])}) "
            "ON CONFLICT (skill_id, locale) DO UPDATE SET name = EXCLUDED.name, aliases = EXCLUDED.aliases;"
        )
        out.append(
            f"INSERT INTO skills_i18n (skill_id, locale, name) VALUES ({s['id']}, 'en', {q(s['en'])}) "
            "ON CONFLICT (skill_id, locale) DO UPDATE SET name = EXCLUDED.name;"
        )

    raw_role_by_id = {r["id"]: r for r in seed.raw_roles}
    out += ["", "-- cargos"]
    for role in seed.roles:
        raw = raw_role_by_id[role.id]
        out.append(
            f"INSERT INTO roles (id, slug, sector_id, market_trend, is_hybrid) VALUES "
            f"({role.id}, {q(role.slug)}, {role.sector_id}, '{role.market_trend.value}', {str(role.is_hybrid).lower()}) "
            "ON CONFLICT (id) DO UPDATE SET slug = EXCLUDED.slug, sector_id = EXCLUDED.sector_id, "
            "market_trend = EXCLUDED.market_trend, is_hybrid = EXCLUDED.is_hybrid;"
        )
        for locale, key in (("pt-BR", "pt"), ("en", "en")):
            out.append(
                f"INSERT INTO roles_i18n (role_id, locale, title) VALUES ({role.id}, '{locale}', {q(raw[key])}) "
                "ON CONFLICT (role_id, locale) DO UPDATE SET title = EXCLUDED.title;"
            )
        out.append(f"DELETE FROM role_skills WHERE role_id = {role.id};")
        for rs in role.skills:
            out.append(
                f"INSERT INTO role_skills (role_id, skill_id, importance) VALUES ({role.id}, {rs.skill_id}, {rs.importance});"
            )
        out.append(f"DELETE FROM role_sectors WHERE role_id = {role.id};")
        for sector_id in role.related_sector_ids:
            out.append(f"INSERT INTO role_sectors (role_id, sector_id) VALUES ({role.id}, {sector_id});")

    out += ["", "-- knowledge graph (career_transitions)"]
    for t in seed.transitions:
        out.append(
            "INSERT INTO career_transitions (from_role_id, to_role_id, observed_count, confidence, avg_years, "
            f"bridge_skill_ids, source) VALUES ({t.from_role_id}, {t.to_role_id}, {t.observed_count}, {t.confidence}, "
            f"{t.avg_years}, {arr_int(t.bridge_skill_ids)}, 'curated') "
            "ON CONFLICT (from_role_id, to_role_id) DO UPDATE SET observed_count = EXCLUDED.observed_count, "
            "confidence = EXCLUDED.confidence, avg_years = EXCLUDED.avg_years, bridge_skill_ids = EXCLUDED.bridge_skill_ids;"
        )

    out += ["", "COMMIT;", ""]
    return "\n".join(out)


def main() -> None:
    seed = load_seed()
    OUT.write_text(build(), encoding="utf-8")
    print(
        f"seed.sql gerado: {len(seed.sectors)} setores, {len(seed.skills)} habilidades, "
        f"{len(seed.roles)} cargos, {len(seed.transitions)} transições"
    )


if __name__ == "__main__":
    main()
