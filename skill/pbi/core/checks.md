# Catálogo de checks · núcleo do kit `pbi`

Fonte única dos checks de qualidade. Alinhado às regras oficiais do Best Practice Analyzer publicadas pela Microsoft (`BestPracticeRules/BPARules.json`, repositório microsoft/Analysis-Services — conferido em 2026-11-22); a correspondência está na seção "Referência BPA" no fim. O fluxo **review** roda todos; o fluxo **mudança** roda os que tocam os objetos alterados; o fluxo **medida** valida a medida nova contra a família DAX.

## Quem detecta

| Detector | Significado |
|---|---|
| `script` | `inventario.py` detecta de forma determinística. A IA só adapta o texto. |
| `script+revisar` | O script aponta o candidato; a IA confirma ou descarta com base no contexto (papel da tabela, regra de negócio, `pbi.projeto.md`). |
| `ia` | Exige julgamento sobre a estrutura. A IA avalia a partir do inventário. |
| `mcp` | Precisa de dados reais (contagem de linhas, cardinalidade). Só roda com o Power BI Modeling MCP conectado; sem ele, registrar como "não verificado". |

## Severidade e nota

`score = max(0, 100 − críticos × 4 − médios × 1,5 − leves × 0,4)` · ≥ 85 BOM · 65–84 PRECISA ATENÇÃO · < 65 CRÍTICO

Issues agregados (ex: "23 medidas sem descrição") contam **uma vez**, não uma por objeto.

---

## Modelagem

| ID | Sev. | Detector | O que é · como corrigir |
|---|---|---|---|
| `model-no-date-table` | crítico | script | Nenhuma tabela marcada como tabela de datas (`dataCategory: Time`). Time intelligence fica sujeita a erro silencioso. → Criar/marcar `d_Calendario` com coluna Data contínua. |
| `model-date-table-disconnected` | crítico | script | Calendário marcado sem nenhum relacionamento ativo: segmentação por data e time intelligence não filtram as fatos. → Criar o relacionamento (data da fato → `d_Calendario[Data]`) ou confirmar que é intencional. |
| `model-calendar-using-auto-hierarchy` | crítico | script | Calendário próprio cuja coluna ainda aponta (`variation`) para `LocalDateTable_*`. → Marcar como tabela de datas, remover a variation, desligar Auto Date/Time. |
| `model-circular-reference` | crítico | script | Dois caminhos de filtro ativos distintos entre o mesmo par de tabelas (ambiguidade), geralmente causado por bidirecional. → Inativar o relacionamento extra e usar `USERELATIONSHIP` onde precisar. |
| `model-flat-detected` | crítico | ia | Várias tabelas-fato sem dimensões compartilhadas (modelo plano). → Extrair dimensões conformadas (começar pelo calendário) e refatorar para star schema. |
| `model-table-without-relationship` | leve | script | Tabela sem relacionamento que não é de medidas, parâmetro nem calc group. → Relacionar ou remover. |
| `model-fact-as-dim` | médio | ia | Tabela com cara de fato no lado "1" de relacionamento. → Revisar cardinalidade; fato é sempre o lado N. |

## Relacionamentos

| ID | Sev. | Detector | O que é · como corrigir |
|---|---|---|---|
| `rel-bidirectional-unnecessary` | crítico | script+revisar | `crossFilteringBehavior: bothDirections`. Legítimo em ponte de M:M; em fato→dimensão N:1 gera ambiguidade e custo. → Single direction + `CROSSFILTER` na medida que precisar. |
| `rel-many-to-many-without-bridge` | crítico | script+revisar | Cardinalidade muitos-para-muitos direta. → Tabela ponte com as chaves únicas e dois N:1. |
| `rel-one-to-one-suspicious` | médio | script | Relacionamento 1:1 quase sempre indica tabelas que deveriam ser uma. → Avaliar merge. |
| `rel-snowflake-suspicious` | médio | script+revisar | Dimensão que filtra outra dimensão (cadeia dim → dim → fato). → Denormalizar atributos na dimensão principal. |
| `rel-columns-different-types` | crítico | script | Colunas de tipos diferentes nas duas pontas do relacionamento (ex.: texto × inteiro). → Igualar o tipo na origem. |
| `rel-inactive-orphan` | leve | script | Relacionamento inativo que nenhuma expressão ativa com `USERELATIONSHIP`. → Remover ou documentar o motivo. |

## Performance

| ID | Sev. | Detector | O que é · como corrigir |
|---|---|---|---|
| `perf-auto-date-time` | médio | script | Auto Date/Time ligado (anotação `__PBI_TimeIntelligenceEnabled = 1` ou tabelas `LocalDateTable_*`). Cria um calendário oculto por coluna de data. → Desligar em Opções → Carregamento de dados. |
| `perf-calc-column-should-be-measure` | médio | script+revisar | Coluna calculada numérica em fato, só com operações da própria linha, sem uso como eixo/segmentação. Materializa em memória sem ganho. → Trocar por medida com `SUMX`. |
| `perf-string-as-key` | médio | script+revisar | Relacionamento por coluna texto. Join por hash de string é mais lento. → Chave inteira substituta. Confirmar cardinalidade (alta = problema) com MCP. |
| `perf-unused-columns` | leve | script | Coluna não usada em medida, relacionamento, RLS, hierarquia, ordenação nem visual. → Remover da origem (ideal) ou ocultar. Só considera relatórios dentro da pasta do projeto. |
| `perf-floating-point` | médio | script | Coluna `double` (ponto flutuante). Em valor monetário gera erro de arredondamento e comprime pior. → Decimal fixo. |
| `perf-calc-column-related` | leve | script | Coluna calculada com `RELATED`. → Trazer o atributo na origem (Power Query/SQL). |
| `perf-directquery-time-intelligence` | médio | script | Medidas de time intelligence em modelo com tabela DirectQuery: SQL pesado na origem. → Agregações, import ou lógica na origem. |
| `perf-distinctcount-high-cardinality` | crítico | mcp | `DISTINCTCOUNT` em coluna texto de alta cardinalidade. → Contar sobre chave inteira. |

## Nomenclatura

| ID | Sev. | Detector | O que é · como corrigir |
|---|---|---|---|
| `naming-mixed-conventions` | médio | script | Nenhum padrão de nome de medida chega a 70%. → Padronizar conforme `convencoes.md` §4. |
| `naming-no-table-prefix` | leve | script | Menos da metade das tabelas fato/dimensão usa prefixo de papel. → Padronizar conforme `convencoes.md` §5. |
| `naming-leading-trailing-space` | leve | script | Nome de tabela, coluna ou medida com espaço no início ou no fim. → Remover. |
| `naming-acronym-no-context` | leve | script | Medida com nome de até 4 caracteres ou sigla, sem descrição. → Expandir ou descrever. |

## DAX

| ID | Sev. | Detector | O que é · como corrigir |
|---|---|---|---|
| `dax-divide-operator` | médio | script | Operador `/` com denominador não constante. → `DIVIDE`. |
| `dax-nested-calculate` | médio | script+revisar | `CALCULATE` dentro de `CALCULATE`. → Extrair para `VAR` (exceto transição de contexto em iterador). |
| `dax-filter-whole-table` | médio | script | `FILTER( <tabela do modelo>, ... )` como filtro de `CALCULATE`/`CALCULATETABLE`. → Filtrar só a coluna (`KEEPFILTERS( T[Col] > x )`). |
| `dax-iferror` | leve | script | `IFERROR` / `ISERROR`. Mascara erro e degrada performance. → Tratar a causa. |
| `dax-duplicate-measures` | médio | script | Duas ou mais medidas com a mesma expressão. → Manter uma; a outra referencia ou sai. |
| `dax-measure-is-reference` | leve | script | Medida cuja expressão é só `[Outra Medida]`. → Remover ou justificar (ex.: renomear para o usuário). |
| `dax-qualified-measure-ref` | leve | script | Medida referenciada com tabela (`T[Medida]`). → `[Medida]` (`core/convencoes.md` §2). |
| `dax-unqualified-column-ref` | leve | script | Coluna referenciada sem tabela (`[Coluna]`) em medida. → `T[Coluna]`. |
| `dax-intersect` | leve | script | `INTERSECT` como relacionamento virtual. → `TREATAS`. |
| `dax-evaluateandlog` | leve | script | `EVALUATEANDLOG` em medida (só para depuração). → Remover antes de publicar. |
| `dax-unused-variables` | leve | script | `VAR` declarada e não usada. → Remover. |
| `dax-iterators-on-large-tables` | médio | mcp | Iterador direto sobre fato com milhões de linhas. → Reduzir escopo antes de iterar. |

## Segurança (RLS)

| ID | Sev. | Detector | O que é · como corrigir |
|---|---|---|---|
| `rls-filter-not-propagating` | crítico | script | A tabela filtrada pela role não alcança nenhuma fato pelos relacionamentos ativos (o filtro de segurança só desce do lado 1 para o N, ou nos dois sentidos com `securityFilteringBehavior: bothDirections`). A role não restringe os números. → Filtrar a dimensão certa ou criar o relacionamento. |
| `rls-on-fact-table` | médio | script | Filtro de segurança direto na fato. Mais pesado e frágil. → Filtrar a dimensão. |
| `rls-and-userelationship-same-table` | crítico | script | Tabela filtrada por RLS também usada em `USERELATIONSHIP`: a consulta falha para quem está na role. → Remover um dos dois ou mudar o desenho. |
| `rls-role-without-filter` | leve | script | Role sem nenhum filtro (vê tudo). Pode ser intencional (admin) — confirmar. |

O teste com dados (o que cada role realmente vê) é o fluxo **rls** (`fluxos/rls.md`).

## Documentação e metadados

| ID | Sev. | Detector | O que é · como corrigir |
|---|---|---|---|
| `doc-measures-no-description` | leve | script | Medidas sem descrição (`///`). → Descrever conforme `convencoes.md` §3. |
| `doc-tables-no-description` | leve | script | Tabelas sem descrição. → Origem + granularidade em uma frase. |
| `measure-no-format-string` | leve | script | Medida sem `formatString`. → Definir conforme formatos do modelo. |
| `measure-unused` | leve | script | Medida não usada em visual nem em outra medida. → Remover ou mover para pasta de auxiliares. Só considera relatórios dentro da pasta do projeto. |
| `fmt-hide-foreign-keys` | leve | script | Chave estrangeira visível na fato. → Ocultar; o usuário filtra pela dimensão. |
| `fmt-numeric-summarize` | leve | script | Coluna numérica visível com soma automática (`summarizeBy` diferente de `none`). → Medida explícita e `summarizeBy: none`. |
| `fmt-month-not-sorted` | leve | script | Coluna de mês em texto sem "Classificar por coluna" (fica em ordem alfabética). → `sortByColumn` com o número do mês. |
| `doc-no-business-key-marked` | leve | script | Dimensão sem coluna `isKey`. Baixa prioridade: o Desktop só expõe isso ao marcar tabela de datas. |
| `data-source-personal-path` | médio | script | Fonte M com caminho pessoal/local (`C:\Users\`, OneDrive, Google Drive). Refresh quebra em outra máquina. Se o caminho já está num parâmetro, cai para leve (só trocar o valor ao entregar). → Parâmetro, SharePoint/Dataflow ou modelo publicado. |

---

## Como a IA usa este catálogo

1. Ler `_pbi/inventario.json` → `issues` (já traz os checks `script` e `script+revisar`)
2. Confirmar ou descartar os `script+revisar` (registrar o motivo do descarte)
3. Avaliar os checks `ia` a partir de `tabelas[].papel_inferido` e `relacionamentos`
4. Rodar os checks `mcp` se o MCP estiver conectado; senão listar como "não verificados"
5. Adaptar o texto ao projeto real: nomes reais de tabelas/medidas, números reais, termo de negócio do glossário

---

## Referência BPA (Microsoft `BPARules.json`)

**Cobertas:** AVOID_FLOATING_POINT_DATA_TYPES → `perf-floating-point` · SNOWFLAKE_SCHEMA_ARCHITECTURE → `rel-snowflake-suspicious` · MODEL_SHOULD_HAVE_A_DATE_TABLE e DATE/CALENDAR_TABLES_SHOULD_BE_MARKED_AS_A_DATE_TABLE → `model-no-date-table` · REMOVE_AUTO-DATE_TABLE → `perf-auto-date-time` · AVOID_EXCESSIVE_BI-DIRECTIONAL_OR_MANY-TO-MANY_RELATIONSHIPS, CHECK_IF_BI-DIRECTIONAL_AND_MANY-TO-MANY_RELATIONSHIPS_ARE_VALID e MANY-TO-MANY_RELATIONSHIPS_SHOULD_BE_SINGLE-DIRECTION → `rel-bidirectional-unnecessary` / `rel-many-to-many-without-bridge` · REDUCE_USAGE_OF_CALCULATED_COLUMNS_THAT_USE_THE_RELATED_FUNCTION → `perf-calc-column-related` · MEASURES_USING_TIME_INTELLIGENCE_AND_MODEL_IS_USING_DIRECT_QUERY → `perf-directquery-time-intelligence` · DAX_COLUMNS_FULLY_QUALIFIED → `dax-unqualified-column-ref` · DAX_MEASURES_UNQUALIFIED → `dax-qualified-measure-ref` · AVOID_DUPLICATE_MEASURES → `dax-duplicate-measures` · USE_THE_TREATAS_FUNCTION_INSTEAD_OF_INTERSECT → `dax-intersect` · USE_THE_DIVIDE_FUNCTION_FOR_DIVISION → `dax-divide-operator` · AVOID_USING_THE_IFERROR_FUNCTION → `dax-iferror` · MEASURES_SHOULD_NOT_BE_DIRECT_REFERENCES_OF_OTHER_MEASURES → `dax-measure-is-reference` · FILTER_MEASURE_VALUES_BY_COLUMNS e FILTER_COLUMN_VALUES → `dax-filter-whole-table` · INACTIVE_RELATIONSHIPS_THAT_ARE_NEVER_ACTIVATED → `rel-inactive-orphan` · EVALUATEANDLOG_SHOULD_NOT_BE_USED_IN_PRODUCTION_MODELS → `dax-evaluateandlog` · AVOID_THE_USERELATIONSHIP_FUNCTION_AND_RLS_AGAINST_THE_SAME_TABLE → `rls-and-userelationship-same-table` · RELATIONSHIP_COLUMNS_SAME_DATA_TYPE → `rel-columns-different-types` · UNNECESSARY_COLUMNS → `perf-unused-columns` · UNNECESSARY_MEASURES → `measure-unused` · ENSURE_TABLES_HAVE_RELATIONSHIPS → `model-table-without-relationship` · OBJECTS_WITH_NO_DESCRIPTION → `doc-measures-no-description` / `doc-tables-no-description` · TRIM_OBJECT_NAMES e OBJECTS_SHOULD_NOT_START_OR_END_WITH_A_SPACE → `naming-leading-trailing-space` · PROVIDE_FORMAT_STRING_FOR_MEASURES → `measure-no-format-string` · NUMERIC_COLUMN_SUMMARIZE_BY → `fmt-numeric-summarize` · RELATIONSHIP_COLUMNS_SHOULD_BE_OF_INTEGER_DATA_TYPE → `perf-string-as-key` · HIDE_FOREIGN_KEYS → `fmt-hide-foreign-keys` · MARK_PRIMARY_KEYS → `doc-no-business-key-marked` · MONTH_(AS_A_STRING)_MUST_BE_SORTED → `fmt-month-not-sorted` · AVOID_BI-DIRECTIONAL_RELATIONSHIPS_AGAINST_HIGH-CARDINALITY_COLUMNS → `rel-bidirectional-unnecessary` (cardinalidade via MCP)

**Não adotadas, e por quê:**
- ISAVAILABLEINMDX_FALSE_NONATTRIBUTE_COLUMNS, SET_ISAVAILABLEINMDX_TO_TRUE_ON_NECESSARY_COLUMNS, AVOID_STRUCTURED_DATA_SOURCES_WITH_PROVIDER_PARTITIONS, REMOVE_DATA_SOURCES_NOT_REFERENCED_BY_ANY_PARTITIONS, PERSPECTIVES_WITH_NO_OBJECTS, PARTITION_NAME_SHOULD_MATCH_TABLE_NAME_FOR_SINGLE_PARTITION_TABLES: específicas de Analysis Services/Tabular Editor ou sem efeito em modelo do Power BI Desktop
- FIRST_LETTER_OF_OBJECTS_MUST_BE_CAPITALIZED e SPECIAL_CHARS_IN_OBJECT_NAMES: conflitam com prefixos `f_`/`d_` e nomes em PT com acento; nomenclatura segue `core/convencoes.md`
- PERCENTAGE_FORMATTING, INTEGER_FORMATTING, DATECOLUMN_FORMATSTRING, MONTHCOLUMN_FORMATSTRING, FORMAT_FLAG_COLUMNS_AS_YES/NO_VALUE_STRINGS, ADD_DATA_CATEGORY_FOR_COLUMNS, HIDE_FACT_TABLE_COLUMNS: preferência de formato; o kit segue o padrão detectado no projeto
- REDUCE_USAGE_OF_LONG-LENGTH_COLUMNS_WITH_HIGH_CARDINALITY, SPLIT_DATE_AND_TIME, LARGE_TABLES_SHOULD_BE_PARTITIONED, FIX_REFERENTIAL_INTEGRITY_VIOLATIONS: precisam de dados/estatísticas; candidatas a checks `mcp` futuros
- LIMIT_ROW_LEVEL_SECURITY_(RLS)_LOGIC, CHECK_IF_DYNAMIC_ROW_LEVEL_SECURITY_(RLS)_IS_NECESSARY, AVOID_USING_MANY-TO-MANY_RELATIONSHIPS_ON_TABLES_USED_FOR_DYNAMIC_ROW_LEVEL_SECURITY, REMOVE_ROLES_WITH_NO_MEMBERS: avaliadas no fluxo **rls** (membros de role só existem no Service)
- MINIMIZE_POWER_QUERY_TRANSFORMATIONS, UNPIVOT_PIVOTED_(MONTH)_DATA, REDUCE_USAGE_OF_CALCULATED_TABLES, REDUCE_NUMBER_OF_CALCULATED_COLUMNS, REMOVE_REDUNDANT_COLUMNS_IN_RELATED_TABLES, MODEL_USING_DIRECT_QUERY_AND_NO_AGGREGATIONS, AVOID_USING_'1-(X/Y)'_SYNTAX, DATA_COLUMNS_MUST_HAVE_A_SOURCE_COLUMN, EXPRESSION_RELIANT_OBJECTS_MUST_HAVE_AN_EXPRESSION, AVOID_INVALID_NAME_CHARACTERS, AVOID_INVALID_DESCRIPTION_CHARACTERS, CALCULATION_GROUPS_WITH_NO_CALCULATION_ITEMS: julgamento caso a caso no fluxo **review** (detector `ia`) ou erros que o próprio Desktop já impede
