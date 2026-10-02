# 003 — sprint 2: POST /recommendations + Claude API + rate limiting + eventos

| | |
|---|---|
| autor | claude code |
| revisor | gemini |
| status | aguardando revisão |
| branch | `feat/sprint2-api-claude` (sobre `feat/sprint1-recommendation-engine`) |
| data | 02/10/2026 |

## objetivo

endpoint principal funcional: experiências → pipeline híbrido → descrições do Claude → resposta. junto, os controles 🔒 do sprint 2.

**gate do sprint 2:** `POST /recommendations` com 3–5 experiências retorna 6–21 caminhos com descrição em <15 s; erros com mensagem amigável; nenhum PII no payload; o request acima do limite por minuto recebe 429. ✅ todos cobertos por teste (136 passando). falta a validação com a API real (ver pendências).

## arquivos

| arquivo | o que faz |
|---|---|
| `recommender/services/claude_service.py` | `ClaudeDescriptionService`: lotes de 3 caminhos em paralelo, saída JSON por `output_config.format`, validação (ids, 60–220 palavras, HTML removido) e fallback local por lote |
| `recommender/services/pii.py` | `clean_user_text` (HTML/script/caracteres de controle) e `redact_pii` (e-mail, URL, CPF, CNPJ, telefone, CEP) |
| `recommender/services/behavioral_service.py` | `BehavioralEventCollector` (RN-10): pesos do TRD §9; payload só com números/ids; falha de telemetria nunca derruba a requisição |
| `recommender/repositories/write_repo.py` | eventos e recomendações persistidas (Postgres + InMemory) |
| `api/routes/recommendations.py` | `POST /recommendations` |
| `api/routes/events.py` | `POST /events` (só eventos de cliente; os de servidor são rejeitados) |
| `api/rate_limit.py` | janela deslizante por IP: 10/min + 50/h (recomendações), 120/min (eventos) |
| `api/schemas/recommendation_schema.py` | contratos HTTP (`extra="forbid"`) |
| `main.py` | montagem dos serviços no lifespan; Postgres → seed em memória em dev; sem chave Anthropic → fallback local |

## decisões de trade-off

1. **`temperature` 0.7 do TRD removida.** o `claude-sonnet-5-5` devolve 400 para temperature diferente do padrão. `tool_choice` forçado também é 400; por isso, `output_config.format`.
2. **lotes paralelos.** 21 descrições de ~150 palavras numa única chamada levam mais de 60 s. em lotes de 3 com até 7 em paralelo, o tempo de parede cai para o de um lote (~8–12 s, a medir). custo extra: as experiências se repetem em cada lote (poucos tokens).
3. **effort `low` + thinking `between_tools`.** é redação curta, sem raciocínio estendido. se a qualidade não bastar, subir para `medium` é uma linha.
4. **o fallback local nunca falha a resposta.** 429/5xx/timeout/recusa/JSON inválido afetam só o lote. `description_source` em cada caminho permite ao frontend sinalizar, e ao analytics medir.
5. **persistência só com login E consentimento** (`consent_data: true`), gravando `users.consent_data_at`. o PRD pede salvar com login (RN-07); o doc de segurança exige consentimento antes da coleta. **gemini: o banner do sprint 3 precisa enviar esse campo.**
6. **rate limit próprio, não slowapi.** sem dependência e sem decorator. limitação: estado por processo. com mais de uma réplica, migrar para Redis/Postgres. IP vem do uvicorn com `--proxy-headers` (não lemos o X-Forwarded-For na mão).
7. **`DATABASE_URL` vazio = sem banco** (testes rodam em 6 s em vez de 90 s).

## contrato para o frontend (gemini)

```
POST /recommendations
headers: X-Session-ID: <uuid gerado no navegador e mantido na sessão>  (opcional, recomendado)
         Authorization: Bearer <jwt supabase>                          (opcional)
body:    { "experiences": [3..5 textos de 10..1500 chars], "risk_tolerance": 0..1, "consent_data": bool }
200:     { request_id, model_version, generated_in_ms, saved,
           paths: [{ id, role_slug, title, description, description_source, key_skills[5],
                     relevance(1-5), confidence_score, market_trend("Em Alta"|"Estável"|"Emergente"),
                     industries[3], is_hybrid, source }] }
422:     { error: "<mensagem amigável pt-BR>", correlation_id }   ← mostrar `error` direto ao usuário
429:     { error, correlation_id } + header Retry-After
POST /events   X-Session-ID obrigatório
body:    { event_type: recommendation_viewed|career_expanded|career_saved|rated_positive|rated_negative|dismissed,
           request_id?, role_id?, rating?(1-5), reading_time_ms? }  → 202
```

## o que revisar com mais cuidado

- **produto/UX:** as mensagens de erro em pt-BR (`NO_SKILLS_MSG`, `TOO_FEW_MSG`, 429) estão no tom certo?
- **o texto do fallback local** (`fallback_description`) é aceitável para o usuário ver quando o Claude falhar?
- **segurança:** algum caminho em que texto livre do usuário vai parar no payload de evento ou num log?
- **contrato:** algo faltando para o `CareerMapVisualization`/`CareerDetailsModal`?

## pendências (não bloqueiam a revisão)

- **teste com a API real:** precisa de `ANTHROPIC_API_KEY` no `backend/.env`. falta medir latência real (gate <15 s) e a qualidade das descrições nas 3 personas.
- **Supabase:** o seed ainda não foi carregado, porque falta a connection string no `.env` (`python -m carrermatch.db.apply_seed`). os repositórios Postgres de escrita foram testados só com dublês.

## como testar

```
cd backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m uvicorn carrermatch.main:app --reload   # http://localhost:8000/docs
```
