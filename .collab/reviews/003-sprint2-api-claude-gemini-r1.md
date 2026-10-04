# Revisão 003 — Sprint 2: POST /recommendations + Claude API + Rate Limiting + Eventos

| Metadata | |
|---|---|
| **Handoff** | `.collab/tasks/003-sprint2-api-claude.md` |
| **Autor** | Claude Code |
| **Revisor** | Gemini (Antigravity) |
| **Data** | 02/10/2026 |
| **Rodada** | r1 |
| **Veredito** | `APROVADO` |

---

## Resumo da Avaliação

A implementação do Sprint 2 entregou o endpoint principal (`POST /recommendations`), a integração resiliente com a Claude API (`ClaudeDescriptionService`), a coleta de telemetria comportamental (`POST /events`), a redação de PII e a infraestrutura de rate limiting.

- **Testes automatizados:** Todos os **136 testes** executam e passam em ~6.7s.
- **Segurança & PII:** Redação rigorosa de PII (`email`, `url`, `cpf`, `cnpj`, `telefone`, `cep`) antes do envio à Anthropic; `clean_user_text` remove scripts/HTML; sanitização da saída da IA com remoção de tags; payloads de eventos filtrados para não conter texto livre (minimização LGPD).
- **Resiliência da UX:** Processamento em lotes paralelos com fallback local gracioso por lote (caso haja erro 429, 5xx, timeout ou falha de JSON do Claude, o usuário sempre recebe 200 com a `description_source="fallback"`).
- **Rate Limiting:** Sliding window por IP em memória (`10/min + 50/h` para recomendações, `120/min` para eventos) retornando 429 e header `Retry-After`.

---

## Análise de Produto, UX e Contrato Frontend

1. **Tom das Mensagens de Erro em pt-BR:**
   - `NO_SKILLS_MSG` e `TOO_FEW_MSG` estão empáticas, claras e instrutivas, orientando o usuário a detalhar melhor suas vivências (inclusive pessoais, em conformidade com RN-09).
   - As mensagens de 422 e 429 estão prontas para serem exibidas diretamente no frontend.

2. **Texto do Fallback Local:**
   - A descrição gerada localmente (`fallback_description`) é natural, coerente e provê uma experiência de uso contínua mesmo quando a API externa falhar.

3. **Contrato do Endpoint com o Frontend (`CareerPathOut`):**
   - O contrato HTTP do `POST /recommendations` encaixa perfeitamente com os componentes React `CareerMapVisualization` e `CareerDetailsModal`.
   - **Nota confirmada para o Sprint 3:** O Antigravity (frontend) enviará `consent_data: true` no payload quando o usuário aceitar o consentimento de dados durante o salvamento/login (RN-07).

---

## Veredito

`APROVADO` — Implementação pronta para integração com o frontend no Sprint 3.
