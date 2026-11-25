# Fluxo · medida

Cria uma medida DAX a partir de uma descrição em PT, usando só objetos que existem no modelo e seguindo as convenções do projeto.

**Ler antes:** `core/convencoes.md`, `core/dax-padroes.md`; com o Power BI Modeling MCP disponível, `core/validacao.md`. Exemplos de referência: `assets/medida/exemplos.md`. Formato da resposta: `assets/medida/output-medida.md`.

**Entrada:** descrição do cálculo (obrigatória); tabela host (opcional — padrão: `convencoes_detectadas.tabela_de_medidas` ou a definida no `pbi.projeto.md`).

---

## 1. Entender o pedido

Do inventário (`_pbi/inventario.json`), identificar:
- **Tipo de cálculo:** agregação, razão/%, time intelligence, ranking, condicional
- **Objetos necessários:** colunas em `tabelas[].colunas`, medidas em `medidas[]`. Reaproveitar medida base existente em vez de repetir expressão (ex: `[Faturamento LY]` usa `[Faturamento]`)
- **Termo de negócio:** se o `pbi.projeto.md` tem glossário, usar a definição de lá ("vencido" = regra do glossário, não suposição)

**Parar e perguntar (uma pergunta, com opções a/b/c)** quando:
- o pedido admite mais de uma leitura ("vendas totais" = bruto? líquido? quantidade?)
- a coluna citada não existe → listar as 2–3 colunas reais mais próximas
- time intelligence pedido e `convencoes_detectadas.tabelas_calendario` vazio → avisar que o resultado pode sair errado e perguntar se segue

## 2. Checar duplicidade

Procurar em `medidas[]` nome parecido **ou** expressão equivalente. Achou → mostrar a existente e perguntar: usar a existente, criar variação ou substituir (variante em `assets/medida/output-medida.md`).

## 3. Escrever a medida

- Padrões de `core/dax-padroes.md` (DIVIDE, SUM vs SUMX, CALCULATE com predicado de coluna, KEEPFILTERS, VAR, sem IFERROR, sem BLANK→0 gratuito)
- Formatação de `core/convencoes.md` §2: **nome sozinho na 1ª linha**, fórmula a partir da 2ª
- **3 nomes** no padrão de `convencoes_detectadas.medidas` (ou do `pbi.projeto.md`)
- Metadados obrigatórios (`core/convencoes.md` §3): descrição, `formatString` no formato já usado no modelo (`convencoes_detectadas.format_strings`), `displayFolder` existente se o modelo usa pastas
- Pedido que leva a anti-pattern → avisar antes e oferecer a versão recomendada (variante em `output-medida.md`)

## 4. Autoverificação antes de responder

- [ ] Toda coluna/medida referenciada existe no inventário (nome exato, tabela certa)
- [ ] Nenhum check da família DAX de `core/checks.md` dispararia na medida nova
- [ ] Medida aditiva? Então o total tem que ser a soma das linhas — a lógica garante isso?
- [ ] Nome, pasta e formato seguem o projeto

## 4b. Validar com dados (se o MCP estiver disponível)

Seguir `core/validacao.md` §1–3: conectar no Desktop, gerar a consulta com `scripts/regressao.py validar` (expressão proposta, `--por` com a dimensão principal; `--comparar-com` quando a nova medida substitui ou deriva de uma existente) e executar. Interpretar pela tabela do §3 e **corrigir antes de responder** se aparecer dimensão que não filtra, infinito ou erro. Na resposta, uma linha com o resultado ("validada com dados: total X, N linhas por Ano, soma bate com o total").

Sem MCP: dizer "não validada com dados" numa linha.

## 5. Responder

Formato de `assets/medida/output-medida.md`: nomes, o que faz (negócio), DAX, como funciona (curto, nível de quem sabe DAX), onde vai (tabela, pasta, formato), pergunta se aplica.

## 6. Aplicar (só com "sim" explícito)

**Com MCP conectado:** aplicar no modelo aberto seguindo `core/validacao.md` §4 (transação, conferir, commit) e pedir para salvar no Desktop.

**Sem MCP:**
- Confirmar que o projeto está fechado no Power BI Desktop (`core/seguranca.md`, "Arquivos do projeto × Power BI Desktop aberto")
- Inserir no `.tmdl` da tabela host (caminho em `medidas[].arquivo` de uma medida da mesma tabela), dentro da pasta certa, em ordem alfabética na pasta
- Sintaxe TMDL de `core/convencoes.md` §2: descrição como `///` acima, expressão dois níveis abaixo, propriedades um nível abaixo, sem `lineageTag`
- Mostrar o trecho inserido e o arquivo/linha
- Não commitar. Lembrar: abrir o projeto no Power BI Desktop e revisar com `git diff`
- Rodar o `inventario.py` de novo se o usuário for pedir outra medida em seguida

## Casos de borda

| Cenário | Ação |
|---|---|
| Modelo sem tabela de medidas | Listar tabelas e perguntar onde colocar (ou sugerir criar `_Medidas`) |
| Mesmo nome já existe | Perguntar: substituir ou outro nome |
| Modelo com >500 medidas | Usar `inventario.json` (nome, pasta, dependências) e abrir a expressão completa só das medidas relevantes |
