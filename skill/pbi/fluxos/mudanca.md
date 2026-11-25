# Fluxo · mudança

Atende um pedido de alteração no modelo do começo ao fim: entende o pedido, mede o impacto, propõe o plano, implementa só com aprovação, confere o que realmente mudou e registra.

**Ler antes:** `core/convencoes.md`, `core/dax-padroes.md`, `core/seguranca.md`; com o Power BI Modeling MCP disponível, `core/validacao.md`. Para criar medida dentro da mudança, seguir também `fluxos/medida.md` §3–4.

**Também serve para** "o que acontece se eu mexer em X?" — nesse caso rodar só as etapas 1–3 e parar.

**Entrada:** o pedido como chegou (e-mail, mensagem, chamado), colado pelo usuário.

---

## 1. Entender o pedido

Traduzir o texto em **requisitos técnicos numerados** — cada um verificável:

> Pedido: "o saldo tem que desconsiderar os estornos a partir de outubro"
> R1. `[Saldo Aberto]` passa a excluir lançamentos com tipo de documento de estorno
> R2. A regra vale a partir de 01/10/2026 (por data de lançamento? de documento?)

- Cruzar com o glossário e as regras do `pbi.projeto.md`
- Ambiguidade que muda o resultado (qual data, qual campo, vale para histórico?) → **uma** pergunta com opções, antes de seguir
- Coluna/campo citado que não existe no modelo → dizer e listar os mais próximos (pode exigir mudança na origem/ETL — sinalizar como fora do modelo)

## 2. Fotografar o estado atual

- Rodar `scripts/inventario.py` (preparação comum do `SKILL.md`)
- Copiar `_pbi/inventario.json` para `_pbi/mudancas/<AAAA-MM-DD>-<slug>/antes.json` — é a base da conferência da etapa 6
- **Com MCP:** tirar a foto das medidas-chave (`core/validacao.md` §2, `regressao.py baseline`) e salvar em `_pbi/mudancas/<pasta>/baseline-antes.json`
- Se o projeto está em git: sugerir um branch `mudanca/<slug>` e criar só se o usuário aprovar (`core/seguranca.md`)

## 3. Análise de impacto

Para cada objeto que será alterado ou removido, tirar do inventário:
- `impacto_medidas` (cascata) e `impacto_visuais` (página › visual)
- uso em RLS (`roles[].permissoes[].depende_de`), relacionamentos, hierarquias, ordenação (`colunas[].usada_em`)
- issues abertos em `issues[]` que tocam esses objetos
- **RLS:** mudança em role, em tabela filtrada por role (`roles[].permissoes`) ou em relacionamento no caminho do filtro (`permissoes[].alcanca`) → incluir o teste do `fluxos/rls.md` antes e depois

Classificar o risco:
- **Baixo:** medida nova ou alteração sem dependentes
- **Médio:** alteração com dependentes ou visuais afetados
- **Alto:** remoção/renomeação com dependentes, mudança de relacionamento, chave ou RLS

Pergunta do tipo "e se eu mexer em X?" termina aqui: devolver a análise e parar.

## 4. Plano (esperar aprovação)

Apresentar curto:
1. Requisitos (da etapa 1)
2. Mudanças, uma por linha: objeto · arquivo · o que muda. DAX completo no formato de `core/convencoes.md` §2
3. Impacto e risco (da etapa 3), com os visuais que mudam de valor **de propósito**
4. Fora do escopo (o que o pedido pode sugerir mas não será feito)
5. Como vai ser conferido (etapa 6)

**Com MCP, testar o plano antes de mostrar:** cada expressão nova ou alterada passa por `regressao.py validar` (com `--comparar-com` a medida atual, quando é alteração). No plano, informar quantas linhas mudam e confirmar que a dimensão filtra. Erro aqui → corrigir o plano, não mostrar DAX que não roda.

**Não editar nada antes de um "sim" explícito.** Ajuste pedido → refazer o plano.

## 5. Implementar

**Com MCP conectado (preferível):** aplicar no modelo aberto dentro de uma transação, seguindo `core/validacao.md` §4. A conferência da etapa 6 acontece **antes do Commit**; no fim, pedir para salvar no Desktop.

**Sem MCP:**
- Confirmar que o projeto está fechado no Power BI Desktop (`core/seguranca.md`, "Arquivos do projeto × Power BI Desktop aberto")
- Editar só os `.tmdl` do plano, na sintaxe de `core/convencoes.md` §2 (descrição `///`, indentação, sem `lineageTag` novo)
- Renomear medida/coluna → atualizar todas as referências DAX listadas no impacto. Visual que usa o nome antigo **quebra** no relatório: listar para o usuário reapontar (ou editar o `visual.json` do PBIR, se ele aprovar)
- Nada fora do plano. Achou outro problema no caminho → anotar e sugerir no fim, não corrigir

## 6. Conferir

```
python <pasta-da-skill>/scripts/comparar.py "<projeto>" --antes "_pbi/mudancas/<pasta>/antes.json"
```

Ler `_pbi/comparacao.json` e checar:
- [ ] Toda mudança listada corresponde a um item do plano — **diferença inesperada = parar e mostrar**
- [ ] `referencias_quebradas` vazio (ou só os visuais já avisados no plano)
- [ ] `avisos_novos` sem referência DAX não resolvida
- [ ] `issues.novos` vazio, ou explicado
- [ ] `medidas.so_formatacao` não conta como mudança de lógica

**Com dados (MCP):**
1. Nova foto: `regressao.py baseline` → `_pbi/mudancas/<pasta>/baseline-depois.json`
2. `regressao.py comparar baseline-antes.json baseline-depois.json --esperadas "<medidas do impacto do plano>"` → salvar em `_pbi/mudancas/<pasta>/`
3. Caso em **"mudaram sem estar no plano"** → `regressao.py diff` na medida para ver as linhas, parar e mostrar (com MCP em transação: `Rollback` até o usuário decidir)
4. Para cada medida alterada de propósito, `regressao.py diff` mostra as maiores diferenças — conferir se batem com o pedido (ex.: só as linhas de estorno mudaram)

**Sem MCP:** listar para o usuário os visuais de `impacto.visuais` para abrir no Power BI Desktop e o que esperar em cada um.

## 7. Registrar

Em `_pbi/mudancas/<pasta>/registro.md`:
- pedido original (texto), requisitos, plano aprovado
- o que mudou (resumo do `comparacao.md`), resultado da conferência estrutural e da regressão com dados (ou "não validado com dados")
- pendências (visuais para reapontar, validação manual, sugestões anotadas)

Adicionar a entrada no `CHANGELOG.md` do projeto no formato de `fluxos/changelog.md` §3 (sem rodar o fluxo inteiro).

## 8. Responder

No chat, curto:
- o que foi feito e o resultado da conferência
- pendências para o usuário
- **texto pronto para responder a quem pediu** (2–4 linhas, linguagem de negócio, sem DAX)

Lembrar: revisar com `git diff` e abrir o projeto no Power BI Desktop (com MCP: salvar no Desktop). Não commitar.
