# pbi.projeto.md — modelo

Copiar para a raiz do projeto PBIP como `pbi.projeto.md` e preencher. Tudo é opcional: o que não for preenchido vem do padrão detectado no modelo ou do padrão do kit. Mantenha curto — é lido em toda execução.

```markdown
# <Nome do projeto>

## Contexto
<1–3 frases: o que o modelo responde, quem usa, origem dos dados>

## Papel das tabelas
<!-- Só quando a inferência automática errar -->
- f_Lancamentos: fato — 1 linha = 1 lançamento contábil
- d_Empresa: dimensão
- aux_Parametros: auxiliar desconectada

## Convenções (sobrepõe o padrão detectado)
- Tabela de medidas: _Medidas
- Prefixos de tabela: f_ / d_ / aux_
- Formato moeda: R$ #,0.00;-R$ #,0.00;R$ 0.00

## Glossário de negócio
- Partida em aberto: título sem data de compensação
- Vencido: data de vencimento < data de referência

## Medidas-chave (base do teste de regressão)
- [Saldo Aberto] por d_Empresa[Empresa] e d_Calendario[Ano Mes]
- [# Títulos] por d_Empresa[Empresa]

## RLS
<!-- Uma linha por usuário de teste: "Role: e-mail (o que deve ver)". Role sem e-mail = estática. -->
- Regional: teste.sul@empresa.com (vê só a regional Sul)
- Regional: teste.norte@empresa.com (vê só a regional Norte)
- Admin: (vê tudo — intencional)

## Exceções aceitas
<!-- Checks do review que não se aplicam a este projeto, com motivo -->
- rel-bidirectional-unnecessary em f_X ↔ ponte_Y: ponte de M:M intencional
```
