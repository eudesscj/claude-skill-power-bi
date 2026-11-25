# Changelog · kit `pbi`

## 1.4.0 · 2026-11-22
- Catálogo de checks comparado com as 71 regras oficiais do Best Practice Analyzer da Microsoft (`BPARules.json`); 16 checks novos e seção "Referência BPA" com o motivo de cada regra não adotada
- Regra de segurança: nunca editar arquivo do projeto com ele aberto no Power BI Desktop (o Desktop sobrescreve ao salvar)
- `inventario.py` avisa quando `_pbi/` e `_testes/` não estão no `.gitignore` de um projeto em git
- Template da doc sem texto fixo de exemplo (novos placeholders); rodapés com data real
- Templates HTML com fontes do sistema como alternativa às do Google; CSS sem uso removido
- `design-tokens.md` único para review e doc

## 1.3.0 · 2026-11-22
- Fluxo **rls**: teste com dados de cada role (e usuário, em RLS dinâmica) via MCP; checks estáticos de RLS

## 1.2.0 · 2026-11-22
- Validação com dados pelo Power BI Modeling MCP (`core/validacao.md`, `scripts/regressao.py`): medida testada antes de criar, baseline e diff linha a linha, aplicação com transação
- Check de tabela calendário sem relacionamento

## 1.1.0 · 2026-11-22
- Fluxos **mudança** e **changelog**; `scripts/comparar.py`; histórico de inventários

## 1.0.0 · 2026-11-22
- Núcleo único de regras (`core/`), `scripts/inventario.py` e fluxos medida, review e doc
