# 004 — sprint 3: frontend (reescrita React)

| | |
|---|---|
| autor | **gemini (antigravity)**: R pelo frontend no RACI |
| revisor | claude |
| status | a fazer |
| branch sugerida | `feat/sprint3-frontend` (a partir de `feat/sprint3-mentores-lgpd`) |
| data | 08/10/2026 |

## escopo (roadmap, sprint 3, bloco frontend)

pasta `frontend/` na raiz. React 18 + Vite 5 + TypeScript 5 + Tailwind v3 + shadcn/ui + react-router v6 + @tanstack/react-query v5 + lucide-react.

| componente | o que entrega |
|---|---|
| `HeroSection` | 3 a 5 campos de texto livre ("o que você fez e o que isso te ensinou"), "+ adicionar outra experiência" até 5, CTA habilitado só com ≥3 preenchidos (RN-01/02); badge "IA treinada com dados de carreiras de 2025" e contador "+2.000 combinações já geradas" |
| `ConsentBanner` 🔒 | **bloqueante para o go-live.** aparece ANTES de qualquer envio; explica a coleta (experiências, eventos de uso) e o uso da IA da Anthropic; o aceite vira `consent_data: true` no `POST /recommendations` |
| `CareerMapVisualization` | ilhas flutuantes estilo Mario World (`floatIsland`), uma por caminho; clique abre o modal |
| `ResultsSection` + `CareerDetailsModal` | grid de cards (`md:grid-cols-3`); botões "ver descritivo completo" e "encontrar mentor nesta área" |
| `AuthModal` | Google + LinkedIn via Supabase Auth (`signInWithOAuth`, providers `google` e `linkedin_oidc`) |
| `MentorForm` | lista os mentores (`POST /mentor-matches`) e envia a solicitação (`POST /mentor-matches/{mentor_id}/requests`); exige login (RN-08) |
| hooks | `useRecommendations`, `useMentorMatch`, `useTrackEvent` (react-query) |
| `lib/api.ts` | fetch wrapper: `Authorization: Bearer <jwt>` quando logado, `X-Session-ID` (uuid em `sessionStorage`), tratamento padrão de `{error, correlation_id}` |

design system: derivar do `globals.css` BHO (`--ocean-deep`, `--gold`, `--terracotta`, `--bg`, `--surface`; Cinzel / Playfair Display / DM Sans / DM Mono; `fadeUp`, `floatIsland`, `shimmerGold`, `driftBoat`). dark mode por padrão, mobile-first. **o `globals.css` não está no repositório: pedir ao gregory.**

## contrato da API

base: `VITE_API_BASE_URL` (dev: `http://localhost:8000`). todo erro vem como `{ "error": "<mensagem pt-BR para mostrar ao usuário>", "correlation_id": "..." }`; o 429 traz o header `Retry-After`.

### já existentes (sprint 2, ver `.collab/tasks/003-sprint2-api-claude.md`)
- `POST /recommendations`
- `POST /events`: eventos de cliente: `recommendation_viewed`, `career_expanded` (com `role_id` e `reading_time_ms`), `career_saved`, `rated_positive`/`rated_negative` (com `rating`), `dismissed`

### novos (sprint 3, backend em construção pelo claude no branch `feat/sprint3-mentores-lgpd`)

```
POST /mentor-matches                           🔐 login obrigatório
body:  { "role_id": int, "experiences"?: [3..5 textos] }
       experiences é opcional se o usuário já salvou experiências (consent_data=true antes)
200:   { "role_id": int, "mentors": [ { "mentor_id": uuid, "display_name": str, "headline": str|null,
                                        "similarity_score": 0..1, "match_reasons": [nomes de habilidades] } ] }   (0 a 5 mentores)
422:   sem experiências salvas e sem `experiences` no body

POST /mentor-matches/{mentor_id}/requests      🔐 login obrigatório · rate limit anti-spam
body:  { "role_id": int, "message": 20..1000 chars }
201:   { "match_id": uuid, "status": "requested" }
404:   mentor inexistente ou indisponível · 409: já existe solicitação pendente para esse mentor

GET /users/me/data                             🔐  exportação LGPD (JSON dos dados do usuário)
DELETE /users/me                               🔐  exclusão definitiva da conta (LGPD art. 18) → 204
```

- o e-mail do mentor **nunca** chega ao frontend; o contato é intermediado pelo backend (Resend, a cargo do antigravity: `services/email_service.py`).
- "excluir minha conta" precisa de confirmação explícita na UI (digitar "EXCLUIR" ou equivalente) antes do `DELETE /users/me`.

## segurança no frontend (checklist)

- nenhuma chave além de `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`
- descrições e títulos vindos da API renderizados como **texto** (nunca `dangerouslySetInnerHTML`)
- token do Supabase gerenciado pelo client oficial; nada sensível em `localStorage` além do que o SDK do Supabase já guarda
- `npm audit` sem vulnerabilidades altas/críticas antes do PR

## gate de saída

inserção de experiências → mapa → modal → formulário de mentoria com gate de login; consentimento antes da coleta; mobile validado.
