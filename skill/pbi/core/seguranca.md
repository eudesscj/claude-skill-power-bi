# Segurança e limites · núcleo do kit `pbi`

Regras que valem para **todos** os fluxos, em qualquer projeto. Não dependem de CLAUDE.md externo.

## Leitura por padrão

- Ler `.SemanticModel/` e `.Report/` é livre
- Escrever só em `_pbi/` (inclui `historico/` e `mudancas/`), `_docs/`, `_review/`, `_testes/` e `CHANGELOG.md` (saídas do kit)
- **Editar `.tmdl` ou qualquer arquivo do modelo/relatório só com aprovação explícita** naquela conversa ("pode aplicar", "sim"). Mostrar antes o que vai mudar, em qual arquivo

## Arquivos do projeto × Power BI Desktop aberto

O Power BI Desktop lê os arquivos do projeto só ao abrir. Com o projeto aberto, edição externa no `.tmdl`/`.Report` não aparece no modelo, e **salvar no Desktop sobrescreve os arquivos, apagando a edição externa**.

- Antes de editar qualquer arquivo de `.SemanticModel/` ou `.Report/`, confirmar que o projeto **não** está aberto no Desktop:
  - com as ferramentas do Power BI Modeling MCP disponíveis: `connection_operations` → `ListLocalInstances` e procurar o nome do projeto em `parentWindowTitle`
  - sem elas: perguntar ao usuário ("o projeto está fechado no Power BI Desktop?")
- Projeto aberto → aplicar pelo MCP (`core/validacao.md` §4) ou pedir para fechar; **nunca** editar o arquivo com o projeto aberto
- Depois de editar os arquivos: orientar a abrir o projeto no Desktop (não existe "recarregar")
- Nunca editar arquivos das tabelas automáticas de data (`LocalDateTable_*`, `DateTableTemplate_*`)

## Versionamento das saídas

`_pbi/` (inventário com DAX e consultas M, histórico, mudanças) e `_testes/` (resultados de consultas, totais dos dados) são de trabalho e não devem ir para o git. `_docs/`, `_review/` e `CHANGELOG.md` podem ser versionados. O `inventario.py` avisa quando o projeto está num repositório git e o `.gitignore` não exclui essas pastas; nesse caso, oferecer **uma vez** adicionar ao `.gitignore`:

```
_pbi/
_testes/
```

Editar o `.gitignore` só com aprovação.

## Git

- Nunca fazer `commit`, `push`, `reset` ou `checkout` que descarte trabalho
- Fluxo **mudança**: sugerir um branch por pedido (`mudanca/<slug-curto>`) e criar só se o usuário aprovar
- Depois de editar, lembrar que dá para revisar com `git diff` e desfazer descartando o arquivo

## Power BI Modeling MCP

- Usar apenas contra **Power BI Desktop local** ou **pasta PBIP**
- **Nunca** conectar ou escrever em workspace do Fabric/Service sem o usuário pedir explicitamente com o nome do workspace
- Queries DAX de validação: só `EVALUATE` de leitura, com `TOPN` ou agregação para não trazer milhões de linhas
- Alteração via MCP segue a mesma regra de aprovação da edição de `.tmdl`

## Dados

- Não copiar dados de clientes (valores, nomes, documentos) para arquivos de saída além do necessário para provar um teste (ex: totais agregados no baseline)
- Baseline de regressão guarda só agregados por dimensão, nunca linhas da fato

## Rede

- Nenhum fluxo faz chamada de rede, exceto o MCP local quando conectado

## Projeto fora do formato PBIP

Se só existir `.pbix`, parar e orientar: *Arquivo → Salvar como → Projeto do Power BI (.pbip)*. Para mapear visuais, o relatório precisa estar no formato PBIR (Opções → Recursos de visualização prévia → "Armazenar relatórios usando o formato PBIR"); no formato legado (`report.json`) o mapeamento funciona, mas com menos garantia.
