# protocolo de colaboração — claude code × antigravity

dois agentes, um repositório. quem escreve é o **R** do RACI (roadmap); o outro revisa. nenhum gate de sprint passa sem uma revisão cruzada com veredito `APROVADO`.

| quem | responsável (R) por | revisa |
|---|---|---|
| claude code | backend Python, engines, schema, testes, prompts | frontend, UX e integrações do antigravity |
| antigravity (gemini) | frontend React, design system, infra/deploy, Resend, curadoria do seed | backend, algoritmos, schema |
| gregory (BHO) | decisões de produto (A) e desempate | — |

## ponte técnica

| direção | como |
|---|---|
| claude → antigravity | MCP `antigravity` (`tools/collab/antigravity_mcp.py`, registrado em `.mcp.json`) → `agentapi new-conversation / send-message` |
| antigravity → claude | MCP `claude-code` (`tools/collab/claude_mcp.py`, registrado no `mcp_config.json` do antigravity) → `claude -p` somente leitura |
| assíncrono (sempre funciona) | arquivos em `.collab/tasks/` e `.collab/reviews/` |

### handshake (antigravity, uma vez por sessão)

a CLI `agentapi` só funciona com as variáveis do language server do antigravity aberto (endereço + token CSRF). ao iniciar uma sessão no antigravity, o agente roda no terminal integrado, na raiz do repo:

```powershell
Get-ChildItem env:ANTIGRAVITY_* | ForEach-Object -Begin { $h = @{} } -Process { $h[$_.Name] = $_.Value } -End { $h | ConvertTo-Json | Out-File -Encoding utf8 .collab/antigravity_env.json }
```

(o arquivo é ignorado pelo git e só vale enquanto aquela sessão do antigravity estiver aberta; refaça ao reabrir.)

## o loop

```
autor implementa ──► .collab/tasks/NNN-slug.md  (handoff)
        ▲                     │
        │                     ▼
  autor corrige ◄── revisor grava .collab/reviews/NNN-slug-<revisor>-rK.md
        │
        └── até veredito APROVADO, ou 3 rodadas → escala para gregory
```

1. **handoff** (`.collab/tasks/NNN-slug.md`) — o autor descreve: objetivo, arquivos alterados, decisões de trade-off, como testar, o que quer que o revisor olhe com mais cuidado.
2. **revisão** (`.collab/reviews/NNN-slug-<claude|gemini>-rK.md`) — achados ordenados por severidade:
   - `bloqueante` — bug, quebra de regra de negócio (RN-01..RN-10), falha de segurança/LGPD
   - `importante` — risco real, mas não impede o merge
   - `sugestão` — qualidade, legibilidade
   
   cada achado com `arquivo:linha`, cenário de falha e correção sugerida. terminar com `veredito: APROVADO | MUDANÇAS NECESSÁRIAS`.
3. **resposta** — o autor corrige, anexa ao handoff uma seção `## rodada K` dizendo o que mudou e o que recusou (com motivo), e pede a rodada K+1.
4. **teto** — 3 rodadas sem consenso → registrar o impasse no handoff e escalar para gregory.

## regras

- revisor não edita o código do autor; propõe.
- achado sem cenário de falha concreto é `sugestão`, nunca `bloqueante`.
- não inventar achados para parecer útil; "nada a apontar" é uma revisão válida.
- tudo em pt-BR.
