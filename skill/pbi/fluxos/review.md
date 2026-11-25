# Fluxo · review

Audita o modelo e entrega relatório priorizado: score 0–100, issues por severidade e categoria, cada um com o que é, onde está, por que importa e como corrigir.

**Ler antes:** `core/checks.md` (catálogo, detectores, fórmula do score). Templates: `assets/review/relatorio.md`, `assets/review/relatorio.html`, placeholders em `assets/review/placeholders.md`, visual em `assets/design-tokens.md`.

**Entrada:** severidade mínima (opcional): `tudo` (padrão) · `crítico+médio` · `só crítico`. Não perguntar se o usuário não mencionar — usar `tudo`.

---

## 1. Partir do inventário

`_pbi/inventario.json` → `issues[]` já traz todos os checks `script` e `script+revisar`. Não refazer esses checks lendo `.tmdl`.

## 2. Completar a análise

Seguir "Como a IA usa este catálogo" no fim de `core/checks.md`:

1. **Confirmar ou descartar os `script+revisar`** com base no papel das tabelas e no contexto. Ex.: bidirecional entre fato e ponte de M:M → descartar com motivo; CALCULATE aninhado dentro de iterador → descartar
2. **Avaliar os checks `ia`** (`model-flat-detected`, `model-fact-as-dim`) a partir de `tabelas[].papel_inferido` e `relacionamentos[]`
3. **Checks `mcp`** (`perf-distinctcount-high-cardinality`, `dax-iterators-on-large-tables`, confirmação de `perf-string-as-key`): com o Power BI Modeling MCP conectado (`core/validacao.md` §1), consultar contagem de linhas/cardinalidade com `EVALUATE` de leitura (`COUNTROWS( T )`, `DISTINCTCOUNT( T[C] )`); senão listar como "não verificados". Com MCP, rodar também `regressao.py validar` com `[medida principal]` por cada dimensão ligada à fato e pelo ano do calendário: dimensão que **não filtra** (todas as linhas iguais ao total) vira issue crítico com a evidência
4. **Exceções do projeto:** issue listado em "Exceções aceitas" do `pbi.projeto.md` sai do score e aparece numa seção "Aceitos pelo projeto"

## 3. Score

Fórmula de `core/checks.md`. Issue agregado conta uma vez. Descartados e aceitos não contam.

## 4. Comparar com a review anterior

Se `_review/relatorio.md` já existe, ler antes de sobrescrever e incluir no relatório: score anterior → atual, issues resolvidos, issues novos.

## 5. Escrever os textos

Para cada issue: título, objeto(s) e caminho (`arquivo`/`linha` do inventário), **por que importa** e **como corrigir** — adaptados ao projeto real: nomes reais, números reais, termo de negócio. Snippet DAX no formato de `core/convencoes.md` §2; snippet TMDL com `///` para descrição.

Ordem: críticos → médios → leves; dentro do nível, categoria com mais issues primeiro. Modelo com >50 críticos: listar os 30 primeiros e uma linha "+N não listados".

## 6. Gerar os arquivos

Em `_review/` na raiz do projeto (sobrescreve):
- `relatorio.md` a partir de `assets/review/relatorio.md`
- `index.html` a partir de `assets/review/relatorio.html`

**Regra do HTML:** usar o template **literal**, substituindo **só** os placeholders `{{...}}` listados em `assets/review/placeholders.md`. Não tocar em `<style>`, `<script>` nem em comentários; não trocar cores, fontes ou ornamentos; UTF-8 puro (acentos e símbolos como caracteres reais — mojibake tipo `Ã£` quebra o parser).

Sem acesso a disco (web): HTML como artifact e markdown como bloco.

## 7. Resumo no chat

Score + rótulo, variação desde a última review (se houver), 3 principais críticos (só títulos), caminho dos arquivos. Nada além disso.

## Segurança

Somente leitura no modelo; escreve só em `_review/` (`core/seguranca.md`).
