---
name: pbi
description: Kit de Power BI para projetos PBIP — cria medidas DAX respeitando o modelo, atende pedidos de mudança com análise de impacto, audita a qualidade (score e anti-patterns), testa RLS, documenta o projeto e gera changelog. Use quando o usuário pedir "cria medida pra X", "preciso de DAX que faça Y", "chegou um pedido de mudança", "altera a medida X", "o que quebra se eu mexer em Y", "audita esse modelo", "tá bem feito?", "documenta esse projeto", "preciso entregar handoff", "gera o changelog", "o que mudou no modelo", "testa o RLS", ou apontar uma pasta PBIP para qualquer trabalho de modelagem.
---

# /pbi — Kit de Power BI

Uma skill, vários fluxos. Todos usam o mesmo núcleo de regras (`core/`) e o mesmo mapa do modelo (`scripts/inventario.py`), então servem para qualquer projeto PBIP sem ajuste.

## 1. Escolher o fluxo

| Pedido | Fluxo | Arquivo |
|---|---|---|
| Criar uma medida DAX | **medida** | `fluxos/medida.md` |
| Pedido de alteração (vindo de alguém ou do próprio usuário), "o que quebra se eu mexer em X?" | **mudanca** | `fluxos/mudanca.md` |
| Auditar qualidade, "tá bem feito?", score | **review** | `fluxos/review.md` |
| Documentar, explicar o modelo, handoff | **doc** | `fluxos/doc.md` |
| Changelog, "o que mudou desde…", avisar usuários | **changelog** | `fluxos/changelog.md` |
| Testar RLS, "o que a role X vê?", conferir segurança | **rls** | `fluxos/rls.md` |

Ajustar uma medida existente é **mudanca** (tem dependentes e visuais); criar do zero é **medida**. Pedido ambíguo ("dá uma olhada nesse modelo"): perguntar uma vez se é auditoria (opinião) ou documentação (descrição). Ler **só** o arquivo do fluxo escolhido.

## 2. Preparação comum (todo fluxo começa aqui)

1. **Achar o projeto.** Pasta com `*.SemanticModel/`. Só `.pbix` → parar e orientar (ver `core/seguranca.md`, último bloco).
2. **Gerar o inventário.**
   - Com acesso à pasta (Claude Code / pasta conectada): `python <pasta-da-skill>/scripts/inventario.py "<pasta do projeto>"` → gera `_pbi/inventario.json` e `_pbi/inventario-resumo.md`. Mais de um modelo na pasta → repetir com `--modelo <nome>`.
   - Sem acesso à pasta (claude.ai web): pedir o ZIP da pasta do projeto (`.SemanticModel` + `.Report`), extrair no ambiente de execução e rodar o mesmo script. Sem ambiente de execução, pedir os `.tmdl` e trabalhar a partir deles.
   - Inventário de outra execução já existe e o projeto não mudou (mesma data dos `.tmdl`) → pode reaproveitar.
3. **Ler o contexto do projeto.** Se existir `pbi.projeto.md` na raiz do projeto, ler — ele tem precedência sobre o que foi detectado (`core/convencoes.md` §1). Não existe e o usuário vai trabalhar no projeto de novo → sugerir uma vez criar a partir de `core/projeto-template.md`.
4. **Ler as regras do núcleo** que o fluxo pedir. Nunca repetir regra do núcleo dentro de um fluxo — referenciar.

## 3. O que o inventário entrega (para não reler `.tmdl` à toa)

`_pbi/inventario.json`:
- `tabelas[]` — papel inferido (fato, dimensao, calendario, medidas, field_parameter, calc_group, auxiliar, desconectada), fontes M, colunas com tipo, uso e impacto
- `medidas[]` — expressão, pasta, formato, descrição, `depende_de`, `usada_por_medidas`, `impacto_medidas` (transitivo), `visuais`, `impacto_visuais`
- `relacionamentos[]`, `roles[]` (com colunas usadas no filtro), `expressoes[]`
- `relatorios[]` — páginas, visuais e campos usados
- `convencoes_detectadas` — padrão de nomes, tabela de medidas, prefixos, pastas, formatos, calendário
- `issues[]` — checks mecânicos do `core/checks.md` (os `script+revisar` precisam de confirmação)
- `avisos[]` — referências DAX não resolvidas, ausência de relatório etc.

Abrir um `.tmdl` só quando precisar do texto exato para editar ou citar linha.

Cada execução do `inventario.py` guarda o inventário anterior em `_pbi/historico/` (últimos 10).

**`scripts/comparar.py`** compara dois momentos (`--antes <json>`, `--git [ref]` ou `--historico`) e gera `_pbi/comparacao.json` / `.md`: medidas, colunas, tabelas, relacionamentos, RLS e parâmetros adicionados/alterados/removidos, mudanças só de formatação, referências quebradas, visuais para conferir e issues novos/resolvidos. Usado pelos fluxos mudança e changelog.

**`scripts/regressao.py`** gera as consultas DAX de validação (medida proposta), foto das medidas-chave (baseline), diferença linha a linha (diff) e teste de RLS (rls / rls-comparar), e compara fotos. Não conecta em nada — as consultas rodam pelo Power BI Modeling MCP (`core/validacao.md`).

**Power BI Modeling MCP:** se as ferramentas `powerbi-modeling-mcp` estiverem disponíveis e o projeto estiver aberto no Power BI Desktop, os fluxos medida, mudança, review e rls validam com dados. Sem ele, tudo funciona igual e o resultado diz "não validado com dados".

## 4. Núcleo

| Arquivo | Conteúdo |
|---|---|
| `core/convencoes.md` | Precedência, formatação DAX (nome na 1ª linha), metadados obrigatórios, nomenclatura, pastas |
| `core/dax-padroes.md` | Boas práticas DAX |
| `core/checks.md` | Catálogo de checks, severidade, quem detecta, fórmula do score |
| `core/seguranca.md` | O que pode ser escrito, aprovação, git, MCP, dados |
| `core/validacao.md` | Validação com dados pelo Power BI Modeling MCP: conectar, testar sem alterar o modelo, ler o resultado, aplicar com transação |
| `core/projeto-template.md` | Modelo do `pbi.projeto.md` |

## 5. Regras que valem sempre

- Seguir `core/seguranca.md`: leitura por padrão; editar modelo só com aprovação explícita; nunca commitar
- DAX sempre no formato de `core/convencoes.md` §2
- PT-BR com acentos, arquivos em UTF-8
- Tom: direto, nível de quem já domina DAX e modelagem; sem explicar o óbvio

## Versão

`1.4.0` — histórico em `CHANGELOG.md` (pasta da skill).
