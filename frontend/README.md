# caminh.ia — frontend

React 18 + Vite + TypeScript + Tailwind. Autor (RACI): antigravity; revisão: claude.

## rodar

```
cp .env.example .env      # VITE_API_BASE_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
npm install
npm run dev               # http://localhost:5173 (backend em http://localhost:8000)
npm run build             # tsc + vite build
```

## design system

Derivado de **"bho: sistema visual · pré-proposta"** (09/10/2026): tokens em `src/index.css`
com os nomes do documento (`--brand-*`, `--dark-*`), expostos no Tailwind como `brand-*`, `dark-*`,
`ink`, `line`, `success`/`warning`/`danger`.

- uma família só: Montserrat variável, hospedada no build (latin + latin-ext)
- o caminh.ia consome a marca-mãe; cores da campanha terra fértil **não** entram na UI
- o degradê oficial entra como imagem quando os assets chegarem — nunca como gradiente CSS

## regras

- nenhuma chave além de `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`
- conteúdo vindo da API é renderizado como texto (sem `dangerouslySetInnerHTML`)
- nada é enviado à API antes da resposta ao banner de consentimento (LGPD)
