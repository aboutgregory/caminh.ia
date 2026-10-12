## o que muda e por quê

<!-- objetivo, arquivos principais, decisões de trade-off -->

## como testar

```
cd backend
.venv\Scripts\python.exe -m pytest -q
```

## revisão cruzada (`.collab/PROTOCOL.md`)

- [ ] handoff em `.collab/tasks/` atualizado
- [ ] revisão do outro agente com veredito `APROVADO`

## checklist de segurança

### código
- [ ] nenhum segredo, API key ou token no diff (pre-commit `detect-secrets` passou)
- [ ] nenhuma variável de ambiente hardcoded
- [ ] inputs validados (Pydantic / domínio) antes de qualquer processamento

### banco de dados
- [ ] toda tabela nova tem `ENABLE ROW LEVEL SECURITY` + policies
- [ ] nenhuma query retorna dados de outros usuários

### integração Claude API
- [ ] payload sem PII (e-mail, CPF, telefone, user_id, nome, IP)
- [ ] resposta validada antes de persistir ou exibir

### erros e logs
- [ ] exceções não expõem stack trace ao cliente
- [ ] logs sem segredos nem dados pessoais completos

### LGPD
- [ ] nova coleta de dado pessoal tem base legal mapeada no documento de segurança
- [ ] eventos comportamentais com user_id protegidos por RLS
