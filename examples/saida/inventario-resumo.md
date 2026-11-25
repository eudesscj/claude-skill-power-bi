# Inventário · VendasExemplo.SemanticModel

Gerado em 25/11/2026 · formato tmdl · projeto fictício de exemplo

## Números

- 5 tabelas · 15 colunas (0 calculadas) · 5 medidas
- 3 relacionamentos (0 inativos) · 0 roles RLS
- 0 páginas · 0 visuais

## Papel das tabelas

- **fato**: f_Vendas
- **dimensao**: d_Loja, d_Produto
- **calendario**: d_Calendario
- **medidas**: _Medidas

## Convenções detectadas

- Nomes de medidas: Title Case (Title Case 4, PascalCase 1)
- Tabela de medidas: _Medidas
- Prefixos de tabela: d_, f_ (fato/dimensão com prefixo: 4/4)
- Pastas de medidas: Vendas, Rentabilidade
- Formatos mais usados: "R$ "#,0.00
- Auto Date/Time: desligado · Calendário: d_Calendario

## Checks mecânicos

- **Crítico** · Relacionamento bidirecional (`rel-bidirectional-unnecessary`) · *revisar* — f_Vendas[LojaKey] → d_Loja[LojaKey] (many:one, ativo).
- **Médio** · Divisão com operador / em vez de DIVIDE (`dax-divide-operator`) — [Margem %] usa '/' com denominador não constante.
- **Médio** · Divisão com operador / em vez de DIVIDE (`dax-divide-operator`) — [TKM] usa '/' com denominador não constante.
- **Médio** · Fonte de dados com caminho pessoal/local (`data-source-personal-path`) — Partição de f_Vendas contém: \users\, \downloads\.
- **Médio** · Coluna com tipo de ponto flutuante (double) (`perf-floating-point`) — 1 coluna(s) double. Para valores monetários use decimal fixo (Decimal Fixo/Moeda): evita erro de arredondamento e comprime melhor.
- **Leve** · Uso de IFERROR/ISERROR (`dax-iferror`) — [TKM] usa IFERROR/ISERROR.
- **Leve** · Medidas sem descrição (`doc-measures-no-description`) — 4 de 5 medidas sem descrição.
- **Leve** · Dimensões sem coluna-chave marcada (`doc-no-business-key-marked`) — 2 dimensão(ões) sem isKey.
- **Leve** · Tabelas sem descrição (`doc-tables-no-description`) — 5 de 5 tabelas sem descrição.
- **Leve** · Chave estrangeira visível na fato (`fmt-hide-foreign-keys`) — 1 chave(s) estrangeira(s) visíveis na fato; ocultar para o usuário filtrar pela dimensão.
- **Leve** · Coluna numérica visível com soma automática (`fmt-numeric-summarize`) — 3 coluna(s) numérica(s) visíveis com soma automática; prefira medidas explícitas e summarizeBy: none.
- **Leve** · Medidas sem formatString (`measure-no-format-string`) — 2 medida(s) sem formatString.
- **Leve** · Medidas sem uso (`measure-unused`) — 3 medida(s) sem uso em visual nem em outra expressão.
- **Leve** · Medidas com sigla/nome curto e sem descrição (`naming-acronym-no-context`) — 1 medida(s): [TKM]
- **Leve** · Colunas sem uso (`perf-unused-columns`) — 6 coluna(s) sem uso em medida, relacionamento, RLS, hierarquia, ordenação ou visual.
