# caminh.ia

assistente de IA do **CarrerMatch** (BHO) que combina experiências profissionais **e pessoais** para revelar caminhos de carreira inesperados — e conecta a pessoa a mentores que já percorreram esses caminhos.

> habilidades aparentemente desconectadas são o ativo mais diferenciado de uma pessoa. o caminh.ia trata isso como dado de entrada, não como exceção.

**status:** MVP v2 em desenvolvimento — reescrita pós-beta Lovable (`caminho.lovable.app`). sprint 0 (fundação) concluído.

---

## como funciona

```
3–5 experiências (texto livre)
        │
        ├──► ItemBasedRecommender   cosine entre vetores TF-IDF de habilidades
        ├──► KnowledgeGraphEngine   transições de carreira (career_transitions)
        └──► HybridPipeline         combina, pondera, seleciona 6–21 caminhos
                    │
                    ▼
        Claude API — descreve cada caminho em pt-BR (não seleciona)
                    │
                    ▼
        mapa de ilhas + cards → mentor matching (user-based CF)
```

os algoritmos próprios escolhem e rankeiam; o Claude só escreve as descrições contextualizadas (ADR-02). todo evento é registrado em `behavioral_events` para treinar o modelo próprio da fase 2.

## stack

| camada | tecnologia |
|---|---|
| backend | FastAPI · Python 3.12 · asyncpg · Pydantic v2 |
| banco | PostgreSQL 16 (knowledge graph relacional, sem Neo4j no MVP) |
| IA | Claude API (descrições) · TF-IDF + cosine (fase 2: embeddings) |
| frontend | React 18 · Vite 5 · TypeScript · Tailwind · shadcn/ui |
| auth / e-mail | Supabase Auth (Google + LinkedIn) · Resend |

## estrutura

```
backend/carrermatch/
├── main.py, config.py           FastAPI + pool asyncpg + GET /health
├── recommender/
│   ├── models/domain.py         entidades puras (RN-01..RN-09 validadas)
│   ├── repositories/            Protocol + Postgres + InMemory
│   ├── engines/                 item-based, knowledge graph, hybrid, mentor (sprints 1–3)
│   └── tests/
└── db/
    ├── migrations/001_initial_schema.sql
    └── seeds/data/*.json        17 setores · 77 habilidades · 84 cargos · 315 transições
frontend/                        sprint 3
tools/collab/                    ponte MCP claude code ↔ antigravity
research/                        PoCs (classificação supervisionada)
```

## rodando o backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.example .env          # preencher DATABASE_URL e ANTHROPIC_API_KEY
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m carrermatch.db.seeds.build_seed
psql "%DATABASE_URL%" -f carrermatch/db/migrations/001_initial_schema.sql
psql "%DATABASE_URL%" -f carrermatch/db/seeds/seed.sql
.venv\Scripts\python.exe -m uvicorn carrermatch.main:app --reload
```

## desenvolvimento colaborativo

o projeto é construído por dois agentes em loop de revisão cruzada — **claude code** (arquitetura, algoritmos, backend) e **antigravity / gemini** (produto, design, frontend, infra). quem escreve é o responsável no RACI; o outro revisa; até 3 rodadas antes de escalar. detalhes em [`.collab/PROTOCOL.md`](.collab/PROTOCOL.md).

## documentação

- [PoC de classificação supervisionada](research/poc-classificacao-supervisionada/README.md)
- PRD, TRD e roadmap são documentos internos da BHO e não são versionados neste repositório público.

## roadmap

| fase | quando | o quê |
|---|---|---|
| **1 — MVP** | 8 semanas | backend, engines, Claude API, frontend reescrito, mentores |
| 2 — modelo próprio | após 1.000 usuários | embeddings, Faiss, Markov → LSTM, HDBSCAN |
| 3 — LTP engine | após fase 2 | grafo de plasticidade, classificador + SHAP |
