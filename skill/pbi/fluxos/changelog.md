# Fluxo · changelog

Transforma o que mudou no modelo em registro legível — para o `CHANGELOG.md` do projeto e para avisar quem usa o relatório.

**Entrada (opcional):** desde quando.
- Projeto em git: uma referência (`HEAD` = mudanças ainda não commitadas — padrão; `HEAD~3`, um commit, uma tag, `main`)
- Sem git: o inventário anterior guardado em `_pbi/historico/` (padrão) ou um `antes.json` de `_pbi/mudancas/`

---

## 1. Comparar

Rodar a partir da pasta da skill:

| Situação | Comando |
|---|---|
| Git, desde uma referência | `python scripts/comparar.py "<projeto>" --git <ref>` |
| Sem git, desde o último inventário | `python scripts/comparar.py "<projeto>" --historico` |
| Desde um arquivo específico | `python scripts/comparar.py "<projeto>" --antes <arquivo.json>` |

Ler `_pbi/comparacao.json`. `sem_mudancas: true` → dizer que não houve mudança no modelo e parar.

## 2. Traduzir para linguagem de negócio

Para cada mudança, escrever **o que muda para quem usa o relatório**, não o que mudou no código:

| Em vez de | Escrever |
|---|---|
| `[Saldo Aberto]`: expressao | **Saldo Aberto** passa a desconsiderar estornos |
| `f_X[Y]` removida | Campo **Y** retirado do modelo (não era usado em nenhum visual) |
| relacionamento direcao both→single | Filtro de **Empresa** deixa de filtrar **Metas** pelo cliente |

Fontes para entender a intenção: a expressão antes × depois (`mudancas.expressao`), o glossário do `pbi.projeto.md`, o `registro.md` da mudança em `_pbi/mudancas/` quando existir.

- Ignorar `so_formatacao` (reformatação sem mudança de lógica)
- Mudança cuja intenção não dá para deduzir → descrever objetivamente e marcar `(confirmar intenção)` — não inventar motivo
- Citar visuais afetados (`impacto.visuais`) quando a mudança altera números que alguém vê
- `referencias_quebradas` não vazio → destacar no topo como **atenção**

## 3. Formato da entrada

Mais recente no topo do `CHANGELOG.md` (raiz do projeto; criar se não existir):

```markdown
## 2026-11-22 · <título curto da entrega>
<!-- origem: git HEAD (a1b2c3d) → projeto atual -->

**Novo**
- Medida **Saldo Vencido**: saldo dos títulos com vencimento anterior à data de referência.

**Alterado**
- **Saldo Aberto** passa a desconsiderar estornos. Afeta: Visão Geral › Saldo por Empresa.

**Removido**
- Campo **Observação** (sem uso no relatório).

**Técnico**
- Relacionamento f_Metas → d_Cliente: bidirecional → direção única.
```

Seções vazias não aparecem. "Técnico" só para o que não muda nada visível (relacionamento, ocultação, descrição, formato).

## 4. Gravar e responder

- Inserir a entrada no topo do `CHANGELOG.md` (permitido por `core/seguranca.md`; mostrar a entrada no chat antes de gravar se o usuário pediu revisão)
- No chat: a entrada gerada + **mensagem curta para os usuários do relatório** (2–4 linhas, sem termos técnicos), pronta para colar
