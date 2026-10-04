"""Aplica `seeds/seed.sql` no banco de DATABASE_URL (backend/.env).

    python -m carrermatch.db.apply_seed

Idempotente: pode rodar após cada revisão da curadoria. Cada bloco `-- @chunk`
roda em transação própria. A URL do banco nunca é impressa.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import asyncpg

from carrermatch.config import get_settings

SEED = Path(__file__).resolve().parent / "seeds" / "seed.sql"


async def main() -> None:
    settings = get_settings()
    parts = re.split(r"^-- @chunk (.+)$", SEED.read_text(encoding="utf-8"), flags=re.MULTILINE)
    conn = await asyncpg.connect(settings.database_url, statement_cache_size=0)
    try:
        for name, sql in zip(parts[1::2], parts[2::2], strict=True):
            await conn.execute(sql)  # protocolo simples: múltiplos comandos, inclui BEGIN/COMMIT
            print(f"ok: {name.strip()}")
        counts = await conn.fetchrow(
            "SELECT (SELECT count(*) FROM app.skills) AS skills, (SELECT count(*) FROM app.roles) AS roles, "
            "(SELECT count(*) FROM app.career_transitions) AS transitions"
        )
        print(f"banco: {counts['skills']} habilidades, {counts['roles']} cargos, {counts['transitions']} transições")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
