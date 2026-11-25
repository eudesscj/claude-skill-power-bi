# Kit Power BI para o Claude (`pbi`)

> 🇺🇸 *A Claude skill for Power BI projects (PBIP): creates DAX measures that follow the model's conventions, runs impact analysis for change requests, audits model quality with a score, tests RLS and generates documentation and changelogs. Docs in Portuguese.*

Uma **skill do Claude** para quem trabalha com Power BI no formato **PBIP**. Em vez de pedir DAX "solto" para uma IA, a skill primeiro **lê o seu modelo** (tabelas, relacionamentos, medidas, convenções de nomes e uso em visuais) e só então cria, altera, audita ou documenta, sempre respeitando o padrão do projeto.

## O problema

IA genérica escreve DAX que até funciona, mas ignora o modelo: inventa nomes de colunas, não segue a convenção de nomes, esquece o `formatString`, não sabe quais visuais usam a medida que você vai alterar e não avisa quando um relacionamento bidirecional ou uma divisão sem `DIVIDE` vai dar problema.

## O que a skill faz

| Pedido (exemplo) | Fluxo | O que entrega |
|---|---|---|
| "Cria uma medida de margem %" | **medida** | DAX no padrão do modelo, com pasta, formato e descrição; validado com dados quando há conexão |
| "O que quebra se eu renomear essa coluna?" | **mudança** | Análise de impacto: medidas dependentes (diretas e transitivas) e visuais afetados |
| "Audita esse modelo" | **review** | Score de qualidade e relatório HTML com anti-patterns por família (modelagem, DAX, performance, segurança, naming) |
| "Documenta esse projeto" | **doc** | Documentação do modelo (tabelas, medidas, relacionamentos e dependências) em Markdown e HTML |
| "O que mudou desde a última versão?" | **changelog** | Comparação entre dois momentos do modelo, por histórico ou por git |
| "Testa o RLS" | **rls** | Checks estáticos de segurança e teste do que cada role enxerga |

## Como funciona

1. **Inventário determinístico.** O script `scripts/inventario.py` (só biblioteca padrão do Python) lê o modelo semântico (TMDL ou `model.bim`) e o relatório, e gera um mapa completo do projeto: papel de cada tabela, dependências entre medidas, uso em visuais e mais de 40 checks automáticos.
2. **Núcleo único de regras** (`core/`): convenções, boas práticas de DAX, catálogo de checks (comparado com as 71 regras do Best Practice Analyzer da Microsoft) e regras de segurança, como nunca editar sem aprovação e nunca fazer commit.
3. **Validação com dados (opcional).** Com o Power BI Modeling MCP e o projeto aberto no Power BI Desktop, as medidas são testadas com dados antes de serem aplicadas.

## Exemplo

Na pasta [`examples/`](examples/) há um **projeto PBIP fictício** (vendas de uma loja inventada) com alguns problemas colocados de propósito, e o [resumo gerado pelo inventário](examples/saida/inventario-resumo.md). Trecho:

```
- Crítico · Relacionamento bidirecional — f_Vendas[LojaKey] → d_Loja[LojaKey]
- Médio  · Divisão com operador / em vez de DIVIDE — [Margem %]
- Médio  · Fonte de dados com caminho pessoal/local — partição de f_Vendas
- Médio  · Coluna com tipo de ponto flutuante (double) — use decimal fixo para valores monetários
- Leve   · Medidas com sigla/nome curto e sem descrição — [TKM]
```

Para rodar você mesmo:

```bash
python skill/pbi/scripts/inventario.py examples/projeto-vendas-exemplo
```

## Instalação

**Claude Code:** copie a pasta `skill/pbi` para `~/.claude/skills/pbi` (no Windows, `C:\Users\<usuario>\.claude\skills\pbi`).

**claude.ai:** compacte a pasta `skill/pbi` em um `.zip` e envie na área de Skills das configurações.

Requisitos: Python 3.9+ e projeto salvo como **PBIP** (Arquivo → Salvar como → Projeto do Power BI). Arquivos `.pbix` não são lidos diretamente.

## Estrutura

```
skill/pbi/
├── SKILL.md        roteador: escolhe o fluxo e faz a preparação comum
├── fluxos/         medida, mudanca, review, doc, changelog, rls
├── core/           convenções, padrões DAX, checks, segurança, validação
├── scripts/        inventario.py, comparar.py, regressao.py
└── assets/         modelos dos relatórios (HTML/Markdown) e design tokens
examples/
├── projeto-vendas-exemplo/   projeto PBIP fictício
└── saida/                    resultado do inventário
```

## Segurança

A skill trabalha em **modo leitura** por padrão. Edição no modelo só com aprovação explícita, nunca com o arquivo aberto no Power BI Desktop, e ela nunca faz commit. Os arquivos gerados ficam em `_pbi/` dentro do projeto; adicione essa pasta ao `.gitignore`.

## Licença

[MIT](LICENSE) · Feito por [Eudes Junior](https://www.linkedin.com/in/eudescj), Analista de Dados.
