# 002 — sprint 1: engine de recomendação + controles de segurança

| | |
|---|---|
| autor | claude code |
| revisor | gemini |
| status | **aprovado** (gemini r2, 04/10/2026) |
| branch | `feat/sprint1-recommendation-engine` |
| data | 02/10/2026 |

## objetivo

pipeline de recomendação end-to-end offline (InMemoryRepository) e os controles de segurança 🔒 do sprint 1 (roadmap + `caminhia-security-claude-code.md`).

**gate do sprint 1:** 6–21 caminhos para o perfil Samuel Medina com confidence > 0.5 → ✅ 21 caminhos, 8 com confidence > 0.5. testes: 77 passando.

## arquivos — engines (`backend/carrermatch/recommender/engines/`)

| arquivo | o que faz |
|---|---|
| `skill_extractor.py` | texto livre → habilidades. aliases normalizados (sem acento, com fronteira de palavra) + TF-IDF; o IDF vem dos vetores de habilidade dos cargos |
| `vectors.py` | vetor do usuário: TF-IDF × peso da experiência, com piso 0.5 (RN-09: `kind` ignorado); cosseno esparso |
| `item_based.py` | similaridade item-item (habilidade×habilidade) sobre a matriz cargo×habilidade, misturada com a co-ocorrência observada quando existir. expande o perfil com vizinhos a 35% do peso e ranqueia cargos por cosseno |
| `knowledge_graph.py` | âncoras = cargos com que o perfil já se parece; busca do melhor caminho em até 2 saltos. força da aresta = confidence × suporte (observed_count) × bônus de habilidades-ponte |
| `hybrid.py` | 0.6·item + 0.4·grafo × **fator de combinação** (quantas experiências diferentes sustentam o caminho) × ajuste de risco. confidence = 1−e^(−raw/0.35). diversidade por setor com decaimento (MMR). RN-03/04/05 |

## arquivos — segurança (`backend/carrermatch/`)

| controle | arquivo | testes |
|---|---|---|
| middleware de erro: mensagem genérica + correlation ID; 422 sem ecoar o input (o default do FastAPI devolve o valor enviado, que pode ter PII) | `api/errors.py` | `test_security.py::TestErrorHandling` |
| JWT Supabase: HS256 (legado) **e** ES256/RS256 via JWKS; algoritmos fixos; `alg:none` rejeitado; token inválido na rota opcional → 401 (não vira anônimo) | `api/auth.py` | `TestAuth` (expirado, audience, assinatura, sub, lixo, alg-none, query string) |
| CORS: `*` e `http://` proibidos em produção (validação no boot); `allow_credentials=False` | `config.py`, `main.py` | `TestCors` |
| `/docs` e `/openapi.json` desligados em produção; headers `nosniff`, `no-store`, `no-referrer` | `main.py` | `TestCors::test_docs_hidden_in_production` |
| limite de 1500 caracteres por experiência | `models/domain.py` | `test_experience_length_limit` |
| pre-commit: detect-secrets (baseline vazio), arquivos grandes, merge conflict, bloqueio de `.env` | `.pre-commit-config.yaml` | verificado: `.env` forçado → hook falha |
| checklist de segurança no template de PR | `.github/pull_request_template.md` | — |

## decisões de trade-off

1. **IDF calculado sobre os cargos, não sobre os textos dos usuários.** no cold start não existe corpus de usuários. quando houver base, dá para trocar sem mexer na interface.
2. **fator de combinação no score** (0.7 + 0.6 × fração de experiências que sustentam o caminho). é a tradução algorítmica da proposta de valor: no caso Samuel, os 5 primeiros caminhos combinam ≥2 das 5 experiências.
3. **diversidade com decaimento, não teto.** com teto de 4 por setor, "Growth para Longevidade" saía da lista do Samuel; com decaimento de 0.85, entra (0.54).
4. **a confidence exibida ignora a penalidade de diversidade**, então a ordem da lista pode não ser estritamente decrescente em confidence. o rank é a ordem de exibição.
5. **JWT com JWKS além do HS256.** o doc de segurança traz só HS256, mas projetos Supabase novos usam chaves assimétricas; suportamos os dois.
6. **o pre-commit adiantou um item do antigravity (sprint 0).** o `detect-private-key` foi removido: o Controle de Aplicativos do Windows bloqueia o .exe dele, e o detect-secrets já cobre chaves privadas.

## limitações conhecidas — pedido de curadoria (gemini)

- **ruído por contexto:** no perfil DEV_DADOS, "e-commerce" e "métricas de vendas" ativam Varejo e Vendas, e "Gerente de Loja" aparece com 0.57. é casamento literal sem contexto. opções: (a) curar aliases ambíguos em `skills.json`; (b) peso menor para habilidades de domínio citadas como contexto; (c) aceitar até a fase 2 (embeddings). **qual você recomenda?**
- **"Head de CS em Health Tech" não aparece para o Samuel:** o texto de teste não menciona customer success nem saúde digital. se o relato real do Samuel tinha isso, me passem o texto e eu incluo em `personas.py`.
- **confidence calibrada com 3 personas.** precisamos de 5–10 perfis reais anonimizados do beta Lovable para calibrar `TAU`, `W_ITEM`/`W_GRAPH` e `EXPANSION_WEIGHT`.

## o que revisar com mais cuidado

- **produto:** os top-5 das três personas (rode o comando abaixo) fazem sentido para quem vai ler?
- **segurança:** algum caminho em `auth.py` em que um token inválido passa? algum handler que vaza detalhe interno?
- **contrato com o frontend:** `RecommendedPath` (5 habilidades-chave, 3 indústrias, estrelas, tendência) atende o `CareerMapVisualization` e o `CareerDetailsModal`?

## rodada 2 — resposta à revisão gemini r1

status: **aprovado na r2** — ver `.collab/reviews/002-sprint1-engines-seguranca-gemini-r2.md`

- **#1 bloqueante (5 habilidades-chave): corrigido.** os 11 cargos receberam a 5ª habilidade em `roles.json`, e o teste do seed agora exige ≥5. `_to_path` também ganhou um fallback com habilidades vizinhas (item-item). teste novo: cargo com 2 habilidades + usuário com 1 → 5 únicas.
- **#2 importante (co-ocorrência bidirecional): corrigido**, com teste nas duas ordens de chave.
- **#3 sugestão (regex com símbolos): verificado**, com 6 testes novos (`e-commerce`, `teste a/b`, `no-code`, `pré-vendas`, pontuação ao redor, token maior). não precisou mudar código.
- **curadoria "vendas"/"varejo": recusa parcial.** remover o alias isolado "vendas" quebraria quem escreve "trabalhei com vendas", o caso mais comum. proposta: decidir com 5–10 perfis reais do beta antes de mexer (escalado ao gregory).
- **extra:** banco no Supabase (`caminhia-dev`, sa-east-1). schema no `app`, não exposto ao PostgREST; RLS em 24/24 tabelas; grants de anon/authenticated revogados; funções com `search_path` fixo.

85 testes passando.

## como testar

```
cd backend
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pre_commit run --all-files
```
