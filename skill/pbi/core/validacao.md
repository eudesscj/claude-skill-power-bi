# Validação com dados (Power BI Modeling MCP) · núcleo do kit `pbi`

Como testar medidas e mudanças contra os dados reais. Usado pelos fluxos **medida**, **mudanca** e **review**. Sem o MCP conectado, tudo aqui é pulado e o fluxo diz "não validado com dados".

## 1. Conectar

1. `connection_operations` → `ListLocalInstances`. Escolher a instância cujo `parentWindowTitle` é o nome do projeto. Nenhuma instância → pedir para abrir o projeto no Power BI Desktop (ou seguir sem validação).
2. `connection_operations` → `Connect` com o `connectionString` devolvido.
3. Só Power BI Desktop local (`core/seguranca.md`). Nunca Fabric/Service sem pedido explícito.

**Atenção à sincronia:** o Desktop mostra o modelo que **ele** carregou. Edição feita no `.tmdl` com o Desktop aberto só aparece depois de fechar e reabrir o projeto; mudança feita pelo MCP só vai para o `.tmdl` quando o usuário salva no Desktop (Ctrl+S). E não atualizar os dados (refresh) entre a foto "antes" e a conferência.

## 2. Regra de ouro: testar sem alterar o modelo

Toda consulta é `dax_query_operations` → `Execute` com `resultMode: "Inline"`. `DEFINE MEASURE` cria a medida **só durante a consulta** — o modelo não muda. Medidas de teste sempre com prefixo `__`.

As consultas são geradas pelo `scripts/regressao.py` (não escrever à mão):

| Para | Comando | Devolve |
|---|---|---|
| Testar medida proposta | `regressao.py validar <projeto> --tabela <T> --expressao <arquivo ou texto> --por "T[C]" [--comparar-com "[M]"]` | 1 linha: total, linhas, soma das linhas, linhas iguais ao total, infinitos, mínimo, máximo (e diferença para uma medida existente) |
| Foto das medidas-chave | `regressao.py baseline <projeto> [--casos "..."]` | 1 linha por caso: linhas, total, soma, checksum |
| Comparar duas fotos | `regressao.py comparar <antes.json> <depois.json> --esperadas "[M1];[M2]"` | casos iguais / mudaram como esperado / **mudaram sem estar no plano** |
| Ver linha a linha o que mudou numa medida | `regressao.py diff <projeto> --antes <inventario-antes.json> --medida "[M]" --por "T[C]"` | só as linhas com diferença (antes, depois, dif), maiores primeiro |

Casos de regressão vêm de "Medidas-chave" do `pbi.projeto.md` (formato `[Medida] por T[Col] e T2[Col2]`). Sem essa seção, o script escolhe as medidas mais usadas no relatório.

Para salvar o resultado de uma consulta: gravar o objeto `data` do Execute **como veio** em `_testes/...json`. São poucas linhas (uma por caso) — não resumir nem arredondar.

## 3. Como ler a validação de uma medida proposta

| Sinal | Significa | Ação |
|---|---|---|
| `linhas_iguais_ao_total` = `linhas` (e linhas > 1) | A coluna do `--por` **não filtra** a medida (relacionamento ausente/inativo, filtro removido por ALL) | Parar e avisar. Conferir relacionamento e `REMOVEFILTERS`/`ALL` |
| `infinitos` > 0 | Divisão por zero com `/` | Trocar por `DIVIDE` |
| Medida aditiva e `soma_das_linhas` ≠ `total` | Lógica não soma nas linhas (ou dimensão com M:M) | Revisar a lógica; para não aditiva (%, média, distinct) a diferença é esperada |
| `total` em branco | Filtro elimina tudo, coluna errada ou tipo incompatível | Revisar |
| `linhas_diferentes_da_atual` > 0 ao reescrever uma medida | O resultado muda em relação à atual | Esperado? Mostrar com `diff` antes de aplicar |
| Erro de sintaxe/semântica no Execute | DAX inválido | Corrigir antes de mostrar ao usuário |

Escolher para o `--por` a dimensão mais usada com a medida (eixo dos visuais em `impacto_visuais`) e o ano/mês do calendário quando houver.

## 4. Aplicar pelo MCP (quando o usuário aprovar)

Com o Desktop conectado, aplicar no modelo aberto é mais seguro que editar `.tmdl`, porque dá para conferir e desfazer antes de salvar:

1. `transaction_operations` → `Begin`
2. `measure_operations` → `Create` / `Update` (nome, tabela, expressão no formato de `core/convencoes.md` §2, `description`, `formatString`, `displayFolder`)
3. Rodar a conferência (baseline/diff)
4. Tudo certo → `Commit`; algo inesperado → `Rollback` e mostrar o motivo
5. Pedir ao usuário para **salvar no Power BI Desktop (Ctrl+S)** — é isso que grava no `.tmdl`

Se a transação não for suportada, aplicar direto e, para desfazer, `Update` com a expressão antiga (está no inventário "antes").

## 5. Limites

- `diff` só reconstrói o "antes" de **medidas** (pela expressão antiga do inventário). Mudança em coluna, relacionamento, RLS ou dados aparece no `baseline` como caso que mudou, sem detalhe por linha
- Visual que usa medida renomeada/removida não é testado pelo DAX: continua valendo `referencias_quebradas` do `comparar.py`
- Consultas de leitura apenas; nada de `ClearCache`, refresh ou escrita fora do passo 4
