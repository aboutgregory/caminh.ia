# caminh.ia — instruções para o agente do antigravity

você trabalha em par com o claude code neste repositório. leia `.collab/PROTOCOL.md` antes de qualquer tarefa.

## ao iniciar cada sessão

1. rode o handshake (terminal integrado, raiz do repo):
   ```powershell
   $env:ANTIGRAVITY_LS_ADDRESS | Out-File -Encoding utf8 -NoNewline .collab/antigravity_ls_address
   ```
2. leia `.collab/tasks/` — handoffs pendentes de revisão sua estão marcados `revisor: gemini` e `status: aguardando revisão`.

## seu papel (RACI do roadmap)

- **responsável:** frontend React (`frontend/`), design system derivado do `globals.css` BHO, infra/deploy, integração Resend, curadoria do seed (`backend/carrermatch/db/seeds/data/*.json`).
- **revisor:** todo código do claude code (backend, engines, schema). grave a revisão em `.collab/reviews/NNN-slug-gemini-rK.md` no formato do protocolo.
- **para pedir revisão ao claude:** use a ferramenta MCP `claude_review(paths, focus)` ou grave um handoff em `.collab/tasks/` com `revisor: claude`.

## especificações

`caminhia-PRD-v2.md`, `caminhia-TRD-v2.md`, `caminhia-roadmap-implementacao.md` (locais, fora do git: o repo é público; nunca os adicione ao commit). regras de negócio RN-01..RN-10 no PRD §9 são inegociáveis sem aprovação do gregory.

idioma: pt-BR em tudo.
