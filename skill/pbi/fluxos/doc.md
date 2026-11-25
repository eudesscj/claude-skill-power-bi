# Fluxo · doc

Documenta o que **existe** no modelo — tabelas, colunas, medidas explicadas, relacionamentos, dependências e onde cada medida aparece no relatório. Não opina sobre qualidade (isso é o fluxo review).

**Ler antes:** `assets/doc/escopo.md` (conteúdo de cada arquivo e placeholders do HTML). Templates: `assets/doc/00-overview.md` a `04-dependencias.md`, `assets/doc/relatorio.html`; visual em `assets/design-tokens.md`.

**Entrada:** escopo (opcional): `tudo` (padrão) · `só medidas` · `só tabelas` · `só relacionamentos` · `tabela X, Y`. Não perguntar se o usuário não mencionar — usar `tudo`.

---

## 1. Partir do inventário

Tudo o que é estrutural vem de `_pbi/inventario.json`:
- tabelas, papel, fontes M (`fontes`, `usa_expressoes`), colunas tipadas
- medidas com expressão, pasta, formato, descrição
- relacionamentos com cardinalidade, direção, ativo
- dependências prontas: `depende_de`, `usada_por_medidas` (árvore e reversa do `04-dependencias.md`)
- **uso no relatório:** `medidas[].visuais` e `colunas[].visuais` — incluir "Aparece em: página › visual" em cada medida
- tabelas `auto_data` ficam fora da documentação

Abrir `.tmdl` só para trechos de M que precisem de resumo.

## 2. Texto de negócio

- Descrição existente (`///`) tem prioridade
- Sem descrição: inferir de nome + estrutura + uso, marcando "descrição inferida"
- Usar contexto e glossário do `pbi.projeto.md` quando existir — é o que faz a doc falar a língua de quem pediu o relatório
- Medidas: explicar em PT o que calcula (negócio) e como (técnico, curto). DAX longo (>30 linhas) explicado em blocos

## 3. Atualização incremental

Se `_docs/` já existe, comparar com o inventário atual e regerar só as seções de tabelas/medidas que mudaram (novas, removidas ou com expressão diferente). Informar no chat o que mudou. Pedido explícito de "refazer tudo" → regerar inteiro.

## 4. Gerar os arquivos

Em `_docs/` na raiz do projeto: `00-overview.md` … `04-dependencias.md` + `index.html`.

**Regra do HTML:** usar `assets/doc/relatorio.html` **literal**, substituindo **só** os placeholders `{{...}}` listados em `assets/doc/escopo.md`. Não tocar em `<style>`, `<script>` nem em comentários; não trocar cores, fontes ou ornamentos; UTF-8 puro.

Sem acesso a disco (web): HTML como artifact, markdowns como blocos ou ZIP.

## 5. Resumo no chat

Quantidades documentadas, o que mudou desde a última doc (se incremental), caminho do `index.html`.

## Segurança

Somente leitura no modelo; escreve só em `_docs/` (`core/seguranca.md`).
