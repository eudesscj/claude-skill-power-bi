# Fluxo · rls

Testa o que cada role de segurança realmente vê, com dados, simulando a role (e o usuário, em RLS dinâmica) no Power BI Desktop. Também roda dentro do fluxo **mudança** quando a mudança mexe em role, em tabela filtrada por role ou em relacionamento no caminho do filtro.

**Ler antes:** `core/validacao.md` (conexão e regras de consulta).

**Precisa do Power BI Modeling MCP** com o projeto aberto no Desktop. Sem ele: fazer só a parte estática (§1) e dizer que o teste com dados não foi feito.

---

## 1. Parte estática (sempre)

Do inventário:
- `roles[]`: filtros de cada role, se é dinâmica (`dinamica`), tabelas que o filtro alcança (`permissoes[].alcanca`)
- issues da família Segurança (`rls-filter-not-propagating`, `rls-on-fact-table`, `rls-role-without-filter`)

Filtro que não chega em fato é problema mesmo sem testar dados — reportar primeiro.

## 2. Montar o teste

```
python <pasta-da-skill>/scripts/regressao.py rls "<projeto>"
```

Devolve o DAX (o mesmo do baseline das medidas-chave), as roles, se são dinâmicas e os usuários de teste da seção "RLS" do `pbi.projeto.md`.

- **Role dinâmica sem usuário de teste** → pedir ao usuário 1–2 e-mails reais para simular (e sugerir registrar no `pbi.projeto.md`). Sem e-mail, a role dinâmica não é testada — dizer isso
- Sem "Medidas-chave" no `pbi.projeto.md`, o script usa as medidas mais vistas no relatório

## 3. Executar

`dax_query_operations` → `Execute`, `resultMode: "Inline"`, com o DAX do passo 2:

1. **Sem role** (sem `impersonation`) → salvar `data` em `_testes/rls/sem_role.json`
2. **Cada role estática** → `impersonation: { "roles": ["<Role>"] }` → `_testes/rls/<Role>.json`
3. **Cada role dinâmica × usuário de teste** → `impersonation: { "roles": ["<Role>"], "userPrincipalName": "<email>" }` → `_testes/rls/<Role>__<usuario>.json`

Erro de impersonação (ex.: o Desktop não aceitar `userPrincipalName`) → registrar e seguir com as demais; sugerir conferir aquele caso pelo "Exibir como" do Desktop.

## 4. Comparar

```
python <pasta-da-skill>/scripts/regressao.py rls-comparar --base _testes/rls/sem_role.json --role "Regional (sul)=_testes/rls/Regional__sul.json" --role "Admin=_testes/rls/Admin.json" --saida _testes/rls
```

Veredito por role:

| Veredito | Leitura |
|---|---|
| **restringe** | vê parte dos dados — conferir a proporção contra o que o `pbi.projeto.md` diz que ela deve ver |
| **⚠ vê tudo** | igual a sem role. Problema, a menos que o projeto diga que é intencional (admin) |
| **⚠ não vê nada** | totais em branco. Em RLS dinâmica, o e-mail não casa com o valor da tabela (maiúsculas, domínio, espaço); em estática, filtro com valor que não existe |

"Soma das roles × total": quando as roles repartem os dados (uma por regional), a soma tem que bater com o total. Não bater = sobreposição ou buraco entre as roles.

## 5. Responder

- Uma linha por role com o veredito e a proporção vista; problemas primeiro
- Para cada problema: causa provável (do §1 e do veredito) e correção sugerida
- Roles/usuários que não puderam ser testados, e por quê
- Arquivos em `_testes/rls/`. Nada é alterado no modelo
