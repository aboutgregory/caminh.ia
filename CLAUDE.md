# caminh.ia — instruções para o claude code

produto: assistente que combina experiências (pessoais e profissionais) em 6–21 caminhos de carreira. specs: `caminhia-PRD-v2.md`, `caminhia-TRD-v2.md`, `caminhia-roadmap-implementacao.md` (locais, fora do git: o repo é público). colaboração com o antigravity: `.collab/PROTOCOL.md`.

## layout

- `backend/` — FastAPI + asyncpg, pacote `carrermatch`. venv em `backend/.venv`.
- `backend/carrermatch/db/migrations/001_initial_schema.sql` — schema (recriado na v2; o original não foi recuperado).
- `backend/carrermatch/db/seeds/data/*.json` — vocabulário e knowledge graph curados; `build_seed.py` gera `seed.sql`. edite os JSONs, nunca o SQL.
- `frontend/` — React + Vite (sprint 3, antigravity é R).
- `tools/collab/` — servidores MCP da ponte claude ↔ antigravity.

## comandos (rodar em `backend/`)

```
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check carrermatch
.venv\Scripts\python.exe -m carrermatch.db.seeds.build_seed
.venv\Scripts\python.exe -m uvicorn carrermatch.main:app --reload
.venv\Scripts\python.exe -m pre_commit run --all-files   # na raiz; use "python -m", os .exe do venv são bloqueados pelo Controle de Aplicativos do Windows
```

## segurança

checklist obrigatório em `.github/pull_request_template.md`; itens por sprint e gate de go-live no roadmap (local). docs locais: `caminhia-seguranca-v2.md`, `caminhia-security-claude-code.md`.

## invariantes

- engines nunca falam com o banco: só via `RecommenderRepository`.
- RN-09: `Experience.kind` nunca entra na ponderação.
- scores internos em [0, 1]; estrelas 1–5 só na borda da API.
- claude API só descreve caminhos já selecionados pelos algoritmos (ADR-02).
- nenhuma chave no frontend; `backend/.env` fora do git.
- respostas de erro nunca ecoam input nem stack trace (`api/errors.py`); token inválido é 401, nunca anônimo.
- payload da Claude API: só experiências passadas por `redact_pii` + vocabulário; sem `temperature`/`tool_choice` forçado (400 no `claude-sonnet-5-5`); falha do Claude cai no fallback local, nunca no usuário.
- eventos comportamentais: só números e ids no payload, nunca texto livre; persistência exige login **e** `consent_data`.
