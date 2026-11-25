# Padrões DAX · núcleo do kit `pbi`

Boas práticas que o fluxo **medida** aplica ao escrever DAX e que o fluxo **review** usa como referência. Formatação (nome na 1ª linha, indentação, VAR) está em `convencoes.md`.

Cada padrão tem o ID do check correspondente em `checks.md`, quando existe.

---

## Divisão: sempre `DIVIDE` · `dax-divide-operator`

```dax
% Margem =
DIVIDE( [Margem Bruta], [Faturamento] )
```

`/` devolve infinito ou NaN quando o denominador é 0. `DIVIDE` devolve BLANK (ou o 3º argumento). Exceção aceitável: denominador constante diferente de zero (`[Valor] / 1000`).

---

## Agregação: SUM vs SUMX

- `SUM( T[Col] )` — soma direta de uma coluna
- `SUMX( T, T[A] * T[B] )` — expressão linha a linha com mais de uma coluna

Não criar coluna calculada só para depois somar (`perf-calc-column-should-be-measure`): infla o modelo. Mesma lógica para `AVERAGEX`, `MAXX`, `MINX`, `COUNTX`.

---

## Contagem

- `COUNTROWS( T )` — linhas da fato no contexto (preferir a `COUNT( T[Col] )`)
- `DISTINCTCOUNT( T[Col] )` — valores únicos; preferir coluna inteira a texto em alta cardinalidade (`perf-distinctcount-high-cardinality`)

---

## Time intelligence

Sempre sobre a coluna de data da **tabela calendário marcada** (`dataCategory: Time`), nunca sobre a data da fato nem sobre a hierarquia automática (`model-no-date-table`, `perf-auto-date-time`).

```dax
Faturamento LY =
CALCULATE(
    [Faturamento],
    SAMEPERIODLASTYEAR( d_Calendario[Data] )
)
```

```dax
% Faturamento YoY =
VAR _Atual = [Faturamento]
VAR _LY = [Faturamento LY]
RETURN
    DIVIDE( _Atual - _LY, _LY )
```

Reaproveitar a medida base (`[Faturamento]`) em vez de repetir a expressão.

---

## CALCULATE

- Filtro por coluna com predicado explícito: `d_Geo[Pais] = "Brasil"`
- **Não filtrar a tabela inteira** com `FILTER( f_Vendas, ... )` como argumento de `CALCULATE` — filtrar só a(s) coluna(s) necessária(s) (`dax-filter-whole-table`):

```dax
Vendas Acima 1000 =
CALCULATE(
    [Faturamento],
    KEEPFILTERS( f_Vendas[Valor] > 1000 )
)
```

- Remover filtro: `REMOVEFILTERS( T )` / `REMOVEFILTERS( T[Col] )`
- Manter o filtro externo ao adicionar um novo: `KEEPFILTERS`
- Ativar relacionamento inativo: `USERELATIONSHIP( f[DataEntrega], d_Calendario[Data] )`
- Mudar direção de filtro só dentro da medida: `CROSSFILTER( ..., Both )` (em vez de relacionamento bidirecional permanente)

## CALCULATE aninhado · `dax-nested-calculate`

Extrair o cálculo interno para `VAR`. Exceção legítima: `CALCULATE` dentro de iterador para forçar transição de contexto (`FILTER( VALUES(...), CALCULATE(...) > 0 )`).

```dax
Faturamento VIP =
VAR _SegmentosVIP =
    CALCULATETABLE(
        VALUES( d_Cliente[Segmento] ),
        d_Cliente[Tipo] = "VIP"
    )
RETURN
    CALCULATE( [Faturamento], d_Cliente[Segmento] IN _SegmentosVIP )
```

---

## Variáveis · `dax-unused-variables`

Usar `VAR` quando houver 2+ passos ou expressão repetida. Toda VAR declarada precisa ser usada.

---

## Erros e BLANK

- **Não usar `IFERROR` / `ISERROR`** (`dax-iferror`): mascaram erro e impedem otimizações do motor. Tratar a causa (`DIVIDE`, `SELECTEDVALUE` com valor padrão, `ISBLANK`).
- **Não converter BLANK em 0 por padrão** (`+ 0`, `IF( ISBLANK(x), 0, x )`): força o motor a calcular todas as combinações e enche o visual de linhas zeradas. Só quando o negócio exige mostrar zero.
- Seleção única: `SELECTEDVALUE( T[Col], "valor padrão" )` em vez de `IF( HASONEVALUE(...), VALUES(...) )`

---

## IF / SWITCH

Mais de uma condição → `SWITCH( TRUE(), ... )` em vez de `IF` aninhado.

```dax
Faixa Cliente =
SWITCH(
    TRUE(),
    [Faturamento] > 1000000, "Premium",
    [Faturamento] > 100000, "Médio",
    [Faturamento] > 0, "Pequeno",
    "Inativo"
)
```

---

## Totais e granularidade

- Comportamento diferente no total: `ISINSCOPE( d_Produto[Produto] )` (preferir a `HASONEVALUE` para detectar nível de hierarquia)
- Medida não aditiva (média, %, distinct): conferir o total — ele **não** é a soma das linhas, e isso é esperado
- Medida aditiva: o total **tem** que ser a soma das linhas. Esse é um dos testes do fluxo de validação

---

## Iteradores em tabela grande · `dax-iterators-on-large-tables`

`SUMX` / `FILTER` / `RANKX` direto sobre fato de milhões de linhas: reduzir escopo antes (`CALCULATETABLE`, `VALUES` da coluna necessária) ou trocar por agregação simples quando possível. A contagem de linhas só é conhecida com o MCP conectado.
