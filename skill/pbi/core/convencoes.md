# Convenções · núcleo do kit `pbi`

Fonte única das regras de nomenclatura, formatação e metadados. Todos os fluxos (medida, mudança, review, doc, changelog) leem este arquivo — nenhum fluxo repete estas regras.

---

## 1. Precedência das regras

Quando duas regras conflitam, vale a de cima:

1. **`pbi.projeto.md`** na raiz do projeto (regras e glossário daquele projeto)
2. **Padrão detectado no modelo** (`_pbi/inventario.json` → `convencoes_detectadas`)
3. **Padrão do kit** (este arquivo)

Regra de ouro: **seguir o que o projeto já faz**, mesmo que o padrão do kit seja diferente. O padrão do kit só entra em projeto novo, ou quando o modelo não tem padrão dominante (nesse caso, avisar antes de aplicar).

---

## 2. Formatação de DAX (vale para medida, coluna calculada e tabela calculada)

**Primeira linha só com o nome e o `=`. Fórmula começa na linha de baixo.** Sem exceção, inclusive para fórmula de uma linha.

```dax
Faturamento =
SUMX(
    f_Vendas,
    f_Vendas[QtdItens] * f_Vendas[PrecoUnitario]
)
```

```dax
% Margem Bruta =
DIVIDE( [Margem Bruta], [Faturamento] )
```

Demais regras:
- Indentação de 4 espaços; um argumento por linha quando a chamada não cabe em ~80 colunas
- `VAR` / `RETURN` em maiúsculas, `RETURN` sozinho na linha
- Nomes de VAR com prefixo `_` (`_Atual`, `_AnoAnterior`) para não colidir com medidas/colunas
- Funções em MAIÚSCULAS (`CALCULATE`, `DIVIDE`)
- Coluna **sempre** com tabela (`f_Vendas[Valor]`); medida **nunca** com tabela (`[Faturamento]`)

### Como isso fica no `.tmdl`

No TMDL a expressão multi-linha vai **dois níveis** de indentação abaixo do objeto; as propriedades, **um nível**:

```tmdl
	/// Receita total das vendas (Quantidade × Preço Unitário). Em R$, sem descontos.
	measure Faturamento =
			SUMX(
			    f_Vendas,
			    f_Vendas[QtdItens] * f_Vendas[PrecoUnitario]
			)
		formatString: #,0.00
		displayFolder: 0. Medidas Padrão
```

- Descrição em TMDL é o comentário `///` **acima** do objeto (não existe propriedade `description:` em TMDL)
- Não inventar `lineageTag` em objeto novo — o Power BI Desktop gera ao abrir
- Nome com espaço, acento ou caractere especial vai entre aspas simples: `measure '% Margem Bruta' =`

---

## 3. Metadados obrigatórios em medida nova

| Metadado | Regra |
|---|---|
| Descrição (`///`) | 1–2 frases: o que calcula + unidade + exclusões relevantes ("sem impostos", "só clientes ativos"). Não repetir o nome. Usar o termo de negócio do glossário do `pbi.projeto.md`. |
| `formatString` | Sempre. Seguir os formatos já usados no modelo (`convencoes_detectadas.format_strings`). |
| `displayFolder` | Se o modelo usa pastas, encaixar numa existente. Se não usa, **não inventar** — só sugerir. |
| Tabela host | A tabela de medidas do projeto (ex: `_Medidas`). Sem tabela de medidas, perguntar. |

Formatos de referência (quando o modelo não tem padrão):
- Moeda BR: `R$ #,0.00;-R$ #,0.00;R$ 0.00`
- Percentual 1 casa: `0.0%;-0.0%;0.0%`
- Inteiro com separador: `#,0`
- Decimal 2 casas: `#,0.00`

---

## 4. Nomenclatura de medidas

### Detecção do padrão dominante

O `inventario.py` classifica os nomes de medidas e grava a distribuição em `convencoes_detectadas.medidas`. O padrão com **≥ 70%** é o dominante e deve ser seguido. Sem dominante, avisar ("modelo tem naming inconsistente") e usar o padrão do kit.

| Padrão | Exemplo |
|---|---|
| **Title Case PT** (padrão do kit) | `Total Vendas`, `Notas Emitidas` |
| camelCase / PascalCase | `totalVendas`, `TotalVendas` |
| snake_case | `total_vendas` |
| MAIÚSCULAS | `TOTAL VENDAS` |

### Prefixos e sufixos de tipo (padrão SQLBI)

| Prefixo | Uso | | Sufixo | Uso |
|---|---|---|---|---|
| `%` | percentual | | `LY` | ano anterior |
| `#` | contagem | | `YoY` / `MoM` | variação ano/mês |
| `Δ` | variação absoluta | | `YTD` / `MTD` | acumulado ano/mês |
| | | | `LTM` | últimos 12 meses |

Exemplos: `% Margem Bruta YoY`, `# Pedidos`, `Faturamento YTD`, `Δ Vendas vs LY`.

### Sugestão de nomes

Medida nova sempre com **3 nomes**: (1) recomendado, seguindo 100% o padrão dominante; (2) mais explícito; (3) mais enxuto.

---

## 5. Nomenclatura de tabelas

- Detectar o prefixo usado (`convencoes_detectadas.tabelas`) e seguir
- Padrão do kit, quando não há: `f_` para fato, `d_` para dimensão, `_Medidas` para a tabela de medidas, `aux_` para tabelas auxiliares/desconectadas (parâmetros, field parameters)
- Tabela calendário: `d_Calendario`, marcada como tabela de datas (`dataCategory: Time`)

---

## 6. displayFolder

Se o modelo já organiza por pastas, reutilizar. Estrutura de referência para projeto novo:

- `0. Medidas Padrão` — base (Faturamento, Custos, Margem)
- `1. Medidas Temporais` — LY, YoY, YTD, MoM
- `2. Medidas por Categoria` — Top N, rankings, slicing por dimensão
- `3. Medidas Dinâmicas` — field parameter, SWITCH por seleção
- `4. Medidas Auxiliares` — títulos, formatação, medidas internas (ocultas)

---

## 7. Idioma e texto

- PT-BR com todos os acentos em descrições, documentação e relatórios
- Arquivos gerados sempre em UTF-8 puro (sem entities, sem mojibake)
- Termos de negócio vêm do glossário do `pbi.projeto.md`; na ausência, do próprio nome das tabelas/colunas
