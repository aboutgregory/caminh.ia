# 001 — sprint 0: fundação

| | |
|---|---|
| autor | claude code |
| revisor | gemini |
| status | aguardando revisão |
| data | 02/10/2026 |

## objetivo

estrutura do backend, schema PostgreSQL, domínio, repositório, `/health` e seed inicial do knowledge graph (gate do sprint 0: ≥200 transições).

## arquivos

- `backend/carrermatch/db/migrations/001_initial_schema.sql`: schema completo (15 domínios + `role_skills` e `role_sectors`)
- `backend/carrermatch/recommender/models/domain.py`: entidades puras
- `backend/carrermatch/recommender/repositories/recommender_repo.py`: Protocol + Postgres + InMemory
- `backend/carrermatch/main.py` e `config.py`: FastAPI, lifespan, pool asyncpg e `GET /health`
- `backend/carrermatch/db/seeds/data/*.json`: 17 setores, 77 habilidades, 84 cargos e 315 transições
- `backend/carrermatch/recommender/tests/test_foundation.py`: 23 testes, todos passando

## decisões de trade-off

1. **schema recriado.** o `carrermatch_schema.sql` original não estava no repo; reescrevi a partir do PRD/TRD/handoff.
2. **`role_skills` e `role_sectors` adicionadas.** o TRD não lista essas tabelas, mas sem `role_skills` não existe vetor de item para o item-based, e sem `role_sectors` não temos as "3 indústrias" do PRD.
3. **RLS via `app.user_id`** em vez de `auth.uid()`: o banco é PostgreSQL puro, não Supabase. o backend conecta como dono das tabelas (bypass); as policies protegem acesso direto.
4. **seed em JSON** (fonte única para os testes e para o SQL). bridge skills calculadas como interseção de `role_skills`.
5. **cargos híbridos** (`is_hybrid`) entram no vocabulário para sustentar combinações como as do caso Samuel.
6. **modelo claude:** `claude-sonnet-5-5` (o TRD cita sonnet-4-6 "ou latest").

## o que revisar com mais cuidado (gemini)

- **curadoria** de `roles.json` e `transitions.json`: as transições e confianças fazem sentido para o mercado brasileiro? que cargos ou transições óbvios estão faltando?
- **aliases** em `skills.json`: termos que um usuário real escreveria e não estão lá; aliases ambíguos demais (ex.: "projeto", "dados", "corpo").
- schema: alguma necessidade de produto/UX (PRD §6) que o schema não comporta?

## como testar

```
cd backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m carrermatch.db.seeds.build_seed
```
