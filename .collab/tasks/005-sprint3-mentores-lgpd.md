# 005 — sprint 3 (backend): matching de mentores + direitos LGPD

| | |
|---|---|
| autor | claude code |
| revisor | gemini |
| status | aguardando revisão |
| branch | `feat/sprint3-mentores-lgpd` |
| data | 08/10/2026 |

## objetivo

parte backend do sprint 3: `MentorMatcher` (user-based CF), `POST /mentor-matches` e a solicitação de mentoria, mais os itens 🔒 de LGPD bloqueantes para o go-live: exclusão definitiva, exportação e trilha de auditoria. o contrato HTTP está em `004-sprint3-frontend.md`.

## arquivos

| arquivo | o que faz |
|---|---|
| `recommender/engines/mentor_matcher.py` | score = 0,5·cos(mentorado, mentor) + 0,5·cos(mentor, cargo-alvo), no espaço TF-IDF dos cargos. mentor sem nenhuma habilidade do cargo é descartado. top-5, com as razões (habilidades do cargo que o mentor domina, priorizando as que o mentorado também tem) |
| `recommender/repositories/account_repo.py` | `AccountStore` (mentoria + conta): Postgres e memória. exclusão em transação, na ordem certa das FKs |
| `recommender/services/account_services.py` | `SupabaseAuthAdmin` (revoga o usuário via Admin API com a service role) e `MentorNotifier` (interface para o Resend) |
| `api/routes/mentors.py` | `POST /mentor-matches`, `POST /mentor-matches/{id}/requests` |
| `api/routes/users.py` | `GET /users/me/data`, `DELETE /users/me` |
| `db/migrations/002_audit_log_mentoria.sql` | `audit_log` (RLS, sem grants públicos) + índice único parcial: uma solicitação pendente por par mentorado→mentor |

## decisões de trade-off

1. **o score da mentoria tem dois termos.** um mentor parecido com o mentorado mas fora do cargo-alvo não ajuda na transição; um especialista sem ponte com a trajetória tende ao conselho genérico. pesos 50/50 até termos `mentor_matches.status` real para calibrar (meta PRD: match rate >20%).
2. **cálculo sob demanda, sem `user_similarities`.** com poucos mentores é instantâneo; o cache via batch diário (ADR-03) entra quando a base de mentores crescer.
3. **o score gravado é recalculado no servidor.** o cliente não envia pontuação (`extra="forbid"` rejeita o campo).
4. **hard delete, não anonimização parcial.** as tabelas com `ON DELETE SET NULL` (eventos, feedback) são apagadas explicitamente ANTES de `users`, senão sobreviveriam órfãs. a auditoria guarda só contagens de linhas, nunca ids.
5. **a revogação no Supabase Auth é feita depois do commit no banco.** se falhar, os dados já foram apagados e a pendência fica em `audit_log` (`auth_revocation_failed`) para reprocessar. o usuário recebe 204 de qualquer forma: do ponto de vista dele, a conta sumiu.
6. **`DELETE /users/me` é idempotente:** usuário sem dados também recebe 204.
7. **a exportação sem dados devolve uma estrutura vazia** com 200, e não 404. a resposta honesta é "não guardamos nada seu".
8. **o e-mail do mentor nunca sai da API.** o aviso é feito pela interface `MentorNotifier`. **gemini: a implementação Resend (`services/email_service.py`) é sua, segundo o RACI.**
9. **anti-spam:** 5 solicitações/hora e 20/dia por IP, mais o 409 para pedido duplicado pendente.

## o que revisar com mais cuidado

- **produto:** os pesos 50/50 e o critério "mentor sem habilidade do cargo = fora" fazem sentido para a experiência de busca?
- **LGPD:** alguma tabela com dado do usuário que a exclusão não cobre? (`_DELETE_STEPS` em `account_repo.py`)
- **UX:** as mensagens 404/409/422 em pt-BR.

## validação no banco (Supabase `caminhia-dev`, 08/10/2026)

migration 002 aplicada. o SQL de `PostgresAccountRepository` foi executado no banco real com as mesmas consultas do código, dentro de um bloco que termina em exceção (rollback total; conferido depois: 0 linhas de teste restantes):

| verificação | resultado |
|---|---|
| consulta de mentores disponíveis | ✅ 2 linhas (mentor × habilidades) |
| vetor de habilidades do mentorado | ✅ 2 habilidades |
| 2ª solicitação pendente para o mesmo mentor | ✅ bloqueada pelo índice único (`unique_violation` → 409) |
| consultas da exportação | ✅ experiências com nomes das habilidades em pt-BR, eventos, recomendações, mentorias |
| exclusão (`_DELETE_STEPS` na ordem do código) | ✅ eventos 1, feedback 1, matches 1, recomendações 1, experiências 1, users 1; **residual 0** (inclusive `experience_skills` por cascata); o mentor da outra ponta ficou intacto |
| `audit_log` | ✅ registro gravado só com contagens |
| advisor de segurança | só o INFO "RLS sem policy" (negar por padrão, intencional) |

## pendências

- `SUPABASE_SERVICE_ROLE_KEY` no `backend/.env` (produção: variável do Railway/Fly). sem ela, a revogação no Auth não acontece e vira pendência auditada.
- o plano gratuito do Supabase **pausa o projeto após ~7 dias sem uso** (aconteceu em 08/10; os dados voltaram intactos na reativação). antes do go-live: plano pago ou uptime ping, além do backup ≥7 dias do gate #6.

## como testar

```
cd backend
.venv\Scripts\python.exe -m pytest -q carrermatch/recommender/tests/test_mentors_lgpd.py
```
