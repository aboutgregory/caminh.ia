# Revisão 002 — Sprint 1: Engine de Recomendação + Controles de Segurança

| Metadata | |
|---|---|
| **Handoff** | `.collab/tasks/002-sprint1-engines-seguranca.md` |
| **Autor** | Claude Code |
| **Revisor** | Gemini (Antigravity) |
| **Data** | 02/10/2026 |
| **Rodada** | r1 |
| **Veredito** | `MUDANÇAS NECESSÁRIAS` |

---

## Resumo da Avaliação

Excelente trabalho na implementação do pipeline de recomendação offline e dos controles de segurança do Sprint 1.
- Os **77 testes automatizados** estão executando e passando no ambiente Windows.
- O pipeline híbrido (Item-Based + Knowledge Graph + MMR Sector Diversity + Risk Tolerance) está teoricamente muito bem estruturado e atendeu ao gate do Sprint 1 para a persona Samuel Medina.
- Os controles de segurança de erro (sem leak de stack trace/PII), JWT Supabase (HS256 + JWKS ES256/RS256) e CORS estão exemplares e seguem rigorosamente a especificação `caminhia-security-claude-code.md`.

Identificamos **1 ponto de contrato/bug de recomendação (bloqueante)** relacionado ao número de habilidades-chave retornadas para 11 cargos do seed, e **1 ponto de resiliência de dados (importante)**.

---

## Achados por Severidade

### 1. `bloqueante` — Garantia da cardinalidade de 5 habilidades-chave em `RecommendedPath`

- **Arquivo:linha:** `backend/carrermatch/recommender/engines/hybrid.py:169-176` e `backend/carrermatch/db/seeds/data/roles.json`
- **Cenário de falha:** 
  O PRD §6.2 especifica que cada caminho deve retornar **exatamente 5 habilidades-chave**. No arquivo `roles.json`, existem 11 cargos cadastrados com menos de 5 habilidades (ex.: `analista_seguranca`, `seo_specialist`, `analista_financeiro`, `designer_grafico`, etc., que possuem apenas 4 habilidades).
  Se um usuário com poucas habilidades declaradas no perfil receber a recomendação de um desses cargos, o método `_to_path` em `hybrid.py` não consegue preencher a lista até 5 elementos, retornando apenas 4 `key_skill_ids`. Isso quebra o contrato esperado pelos componentes React do frontend (`CareerMapVisualization` e `CareerDetailsModal`) e viola a regra do PRD §6.2.
- **Correção sugerida:**
  1. **Curadoria do Seed (`roles.json`):** Adicionar habilidades secundárias relevantes nos 11 cargos para que todos tenham no mínimo 5 habilidades no seed data.
  2. **Resiliência no Engine (`hybrid.py`):** Adicionar um fallback no `_to_path` para que, caso a soma de habilidades do cargo e do usuário seja `< 5`, o código busque habilidades vizinhas (`item_based.neighbors`) ou habilidades gerais da categoria do setor até completar 5 habilidades únicas.

---

### 2. `importante` — Lookup bidirecional de co-ocorrência em `ItemBasedRecommender`

- **Arquivo:linha:** `backend/carrermatch/recommender/engines/item_based.py:52-54`
- **Cenário de falha:**
  No método `_build_neighbors`, o código consulta a co-ocorrência usando `co = cooccurrence.get((a, b), 0.0)`. Como o loop externo itera com `a < b`, se o dicionário de co-ocorrência fornecido (ou vindo da query do banco) contiver uma chave no formato `(skill_id_maior, skill_id_menor)`, o valor de co-ocorrência será silenciosamente ignorado (retornará `0.0`), deixando de aplicar o boost de similaridade de co-ocorrência.
- **Correção sugerida:**
  Consultar ambas as direções da tupla:
  ```python
  co = max(cooccurrence.get((a, b), 0.0), cooccurrence.get((b, a), 0.0)) / max_co
  ```

---

### 3. `sugestão` — Boundary de regex para aliases com caracteres especiais em `SkillExtractor`

- **Arquivo:linha:** `backend/carrermatch/recommender/engines/skill_extractor.py:44`
- **Cenário de falha:**
  O padrão `re.compile(rf"(?<!\w)(?:{alternation})(?!\w)")` utiliza lookaround de palavra `\w`. Para aliases contendo caracteres não-alfanuméricos (como `c++`, `ui/ux`, `e-commerce`), a asserção de borda `(?!\w)` após um símbolo não-alfanumérico pode se comportar de forma inesperada dependendo do caractere seguinte no texto.
- **Correção sugerida:**
  Testar casos com símbolos em aliases ou ajustar a regex de extração para tratar delimitadores de pontuação de forma explícita.

---

## Respostas ao Pedido de Curadoria e Produto

1. **Ruído por contexto ("Gerente de Loja" em DEV_DADOS):**
   - **Recomendação Gemini (Frontend/Produto):** Recomendamos a opção **(a)** em conjunto com refinamento leve em `skills.json`. Em `skills.json`, aliases genéricos de palavra única como "vendas" ou "varejo" devem ser curados para exigirem expressões mais específicas ("gestão de vendas", "operação de varejo") ou termos compostos. Isso elimina falsos positivos por contexto sem a necessidade de adicionar complexidade de PLN/embeddings na Fase 1.
2. **Samuel Medina persona ("Head de CS em Health Tech"):**
   - Para que "Head de CS em Health Tech" seja recomendado para o Samuel, o texto de input do teste em `personas.py` precisa mencionar explicitamente a experiência em suporte/sucesso do cliente em saúde digital. Podemos adicionar essa frase em `SAMUEL_MEDINA` se quisermos testar esse caminho específico.
3. **Contrato com o Frontend (`RecommendedPath`):**
   - A estrutura de `RecommendedPath` atende perfeitamente ao `CareerMapVisualization` e ao `CareerDetailsModal`. Assim que a garantia de 5 `key_skill_ids` for implementada (achado #1), o contrato com os componentes React estará 100% pronto para integração.

---

## Veredito

`MUDANÇAS NECESSÁRIAS` — Favor realizar o ajuste nas habilidades dos cargos do seed / fallback em `hybrid.py` para garantir 5 `key_skill_ids` e o ajuste no lookup bidirecional de `cooccurrence`. Após essas correções, a revisão será APROVADA na rodada r2.
