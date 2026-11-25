# Design tokens · relatórios HTML do kit `pbi`

Fonte única do visual dos dois relatórios (review e doc). Os tokens ficam no CSS dos templates `assets/review/relatorio.html` e `assets/doc/relatorio.html`; se um token mudar aqui, mudar nos dois templates.

## Princípios visuais · review

- **Vibe**: editorial premium (não neon). Tom "Bloomberg/FT", não "ferramenta de hacker"
- **Hierarquia**: tipografia condensada (Bebas Neue + Barlow Condensed) pra display, Outfit pra body
- **Cor primária**: blue glow (`--accent-glow: #7099FF`) pra elementos informativos
- **Cor de destaque**: gold/champagne (`--accent-gold-bright: #E8C9A0`) pra score, scores e CTAs
- **Severidade adaptada ao DS**:
  - Crítico → `--neon-magenta` (#C47FFF) — roxo violeta sutil (não vermelho agressivo)
  - Médio → `--accent-glow` (#7099FF) — blue glow
  - Leve → `--accent-gold-bright` (#E8C9A0) — gold sutil
- **Background**: orb gradient fixo (navy/indigo) com radial blue overlay
- **Brackets**: elemento característico do v4 — usar nos cards principais
- **Print**: vira light mode automático (preserva legibilidade no papel)

---

## Princípios visuais · doc

- **Vibe**: editorial premium · "manual técnico de luxo" tipo Linear docs / Stripe docs / Tailwind docs
- **Hierarquia**: tipografia condensada (Bebas Neue + Barlow Condensed) pra display, Outfit pra body, JetBrains Mono pra código
- **Cor primária**: blue glow (`--accent-glow: #7099FF`) pra elementos navegacionais e identificadores (paths, nomes de medidas)
- **Cor de destaque**: gold/champagne (`--accent-gold-bright: #E8C9A0`) pra valores numéricos e métricas-resumo
- **Tipo de tabela** (badge na sidebar e nos cards):
  - **Fato** → `--neon-magenta` (#C47FFF) — destaque, é o "núcleo" do modelo
  - **Dimensão** → `--accent-glow` (#7099FF) — informativo, descreve
  - **Tabela de medidas** → `--accent-gold-bright` (#E8C9A0) — especial, mora o cálculo
  - **Auxiliar** (parameter, aux, etc.) → `--text-muted` (#6B729A) — discreto, papel utilitário
- **Layout**: sidebar fixa esquerda (250px) + main scrollable. Diferente da `fluxo review` (single column scrollable).
- **Background**: orb gradient fixo (navy/indigo) com radial blue overlay
- **Print**: vira light mode automático (preserva legibilidade no papel)

---

## Cores

### Backgrounds
```css
--bg-deepest:  #0D0C0E;  /* preto profundo, body base */
--bg-dark:     #100F14;
--bg-navy:     #1A1346;  /* navy do orb */
--bg-indigo:   #1D164A;  /* indigo do orb */
--bg-card:     #14131A;
--bg-elevated: #1C1B28;  /* surface elevado, cards */
--bg-surface:  #211F30;
```

### Accent Blues (orb palette)
```css
--accent-deep:   #1A1346;
--accent-mid:    #3951A3;
--accent-blue:   #4668D4;
--accent-bright: #5A7FFF;
--accent-glow:   #7099FF;  /* PRIMÁRIO informativo desta skill */
```

### Accent Gold (champagne — score, label, CTAs nobres)
```css
--accent-gold-deep:   #B8955A;
--accent-gold:        #D4B896;
--accent-gold-bright: #E8C9A0;  /* PRIMÁRIO destaque desta skill */
--accent-gold-glow:   #F0DFC0;
```

### Neon secundários (severity)
```css
--neon-cyan:    #4FE3E8;
--neon-magenta: #C47FFF;  /* SEVERIDADE CRÍTICA desta skill */
--neon-violet:  #7B6FFF;
--neon-teal:    #3FD1B8;
```

### Texto
```css
--text-white:     #FFFFFF;
--text-primary:   #F0EFF8;  /* body principal */
--text-secondary: #9DA5C8;  /* legendas, labels */
--text-muted:     #6B729A;  /* meta, footer */
--text-faint:     #3E4468;
```

### Borders
```css
--border-faint:  rgba(255,255,255,0.06);
--border-mid:    rgba(255,255,255,0.12);
--border-accent: rgba(90,127,255,0.35);  /* blue */
--border-gold:   rgba(212,184,150,0.35); /* gold */
```

---

> Neon secundários: no **review** indicam severidade (magenta = crítico, azul = médio, gold = leve); na **doc** indicam o tipo de tabela (magenta = fato, azul = dimensão, gold = medidas, muted = auxiliar).

## Tipografia

```css
--font-display:   'Bebas Neue', sans-serif;          /* h1, scorenum (uppercase, condensada) */
--font-condensed: 'Barlow Condensed', sans-serif;    /* labels, eyebrows, severity titles */
--font-body:      'Outfit', sans-serif;              /* body, cards, descriptions */
--font-mono:      'JetBrains Mono', Consolas, monospace; /* paths, snippets de código */
```

### Carregamento (Google Fonts — única dependência externa; os templates têm fontes do sistema como alternativa (Impact/Arial Narrow, Segoe UI, Cascadia Mono/Consolas) para funcionar sem internet)
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@300;400;600;700;800&family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

### Escala (fluida, mas não tão agressiva quanto slide)
- `score-num`: `clamp(7rem, 14vw, 12rem)`
- `hero-headline`: `clamp(40px, 6vw, 72px)`
- `section-title`: `clamp(36px, 5vw, 56px)`
- `sev-num`: `72px` fixo
- body padrão: `16px`
- labels uppercase: `11–13px`

---

## Spacing & layout

```css
--container-max: 1200px;
--gap-sm: 12px;
--gap-md: 24px;
--gap-lg: 48px;
--gap-xl: 80px;
--card-padding: 32px;
```

Padding lateral container: `40px` (desktop) → `24px` (mobile).
Margin entre seções: `96px`.

---

### Layout da doc

```css
--container-max: 1400px;        /* maior que fluxo review por causa da sidebar */
--sidebar-width: 260px;
--gap-sm: 12px;
--gap-md: 24px;
--gap-lg: 40px;
--gap-xl: 80px;
--card-padding: 28px;
```

Padding lateral main content: `48px` (desktop) → `20px` (mobile).
Margin entre seções: `80px`.

### Layout fundamental

```
┌────────────────────────────────────────────────────────┐
│ TOPBAR (full-width, fixed)                             │
├──────────┬─────────────────────────────────────────────┤
│          │                                             │
│ SIDEBAR  │ MAIN CONTENT                                │
│ (fixed)  │ (scrollable)                                │
│ 260px    │                                             │
│          │ - Overview section                          │
│          │ - Tabelas section (cards)                   │
│          │ - Medidas section (grouped by displayFolder)│
│          │ - Relacionamentos section (matrix + list)   │
│          │ - Dependências section (tree + reverse)     │
│          │                                             │
│          │ FOOTER                                      │
│          │                                             │
└──────────┴─────────────────────────────────────────────┘
```

Em mobile (<780px): sidebar vira topbar dropdown ou hamburger.

---

## Radii

```css
--radius-sm:   6px;   /* badges */
--radius-md:   12px;  /* mini-cards */
--radius-lg:   20px;  /* hero scorecard */
--radius-pill: 999px; /* buttons, badges */
```

---

## Shadows

```css
--shadow-card:      0 4px 24px rgba(0,0,0,0.5);
--shadow-elevated:  0 8px 48px rgba(0,0,0,0.7);
--shadow-glow-sm:   0 0 20px rgba(90,127,255,0.3);   /* hover blue */
--shadow-glow-md:   0 0 60px rgba(90,127,255,0.45);
--shadow-glow-gold: 0 0 24px rgba(232,201,160,0.25); /* score destaque */
```

---

## Gradients

```css
--gradient-orb: radial-gradient(ellipse at 38% 52%,
  #1F2E75 0%, #16205A 12%, #0F143E 28%, #0A0C24 48%, #0D0C0E 70%
);

--gradient-text: linear-gradient(135deg, #FFFFFF 0%, #A0B8FF 60%, #5A7FFF 100%);

--gradient-gold: linear-gradient(135deg, #F0DFC0 0%, #D4B896 55%, #B8955A 100%);

--gradient-surface: linear-gradient(135deg, #1C1B28 0%, #14131A 100%);
```

### Gradients por categoria do distribution-bar (cor por categoria)

| Categoria | Gradient |
|---|---|
| Performance | `linear-gradient(135deg, #5A7FFF, #4668D4)` |
| Relacionamentos | `linear-gradient(135deg, #7B6FFF, #4668D4)` |
| Modelagem | `linear-gradient(135deg, #C47FFF, #7B6FFF)` |
| Naming | `linear-gradient(135deg, #E8C9A0, #B8955A)` |
| DAX | `linear-gradient(135deg, #4FE3E8, #3FD1B8)` |
| Documentação | `linear-gradient(135deg, #6B729A, #3E4468)` |

---

## Componentes · review

Componentes novos criados pra essa skill (não existem no DS v4 base — extensões respeitando os tokens). Marcados com prefixo `pbi-` quando faria sentido modularizar; aqui usei nomes mais diretos pra simplicidade.

#### `.scorecard`
Card hero do score. Background `--gradient-surface`, border `--border-faint`, radius `20px`, padding `64px`. Tem `::before` com gradient gold sutil no topo.

#### `.score-num`
Texto gigante do score (0-100). Font condensed weight 300, color via `background-clip: text` com `--gradient-gold`, drop-shadow glow gold.

#### `.score-label`
Pill com label ("Bom" / "Precisa Atenção" / "Crítico"). Sempre gold (semântica neutra elegante).

#### `.sev-card`
Card de severidade (3 colunas). Variants `.critical`, `.medium`, `.light` mudam cor da `::before` line, do `.sev-num` e do `.sev-icon`.

#### `.dist-bar`
Barra empilhada horizontal (flex). Cada `<div>` tem `flex` proporcional ao count e gradient da categoria.

#### `.issue-card`
`<details>/<summary>` com header expansível. Variants `.critical` (border magenta) e `.medium` (border blue). Toggle visual de `+` rotaciona pra `×` quando aberto.

#### `.issue-body pre`
Snippet de código com syntax highlight via spans:
- `.k` → keyword (magenta)
- `.f` → function/identifier (blue glow)
- `.s` → string (gold)
- `.c` → comment (muted)

---

## Componentes · doc

#### `.topbar`
Fixed top, full-width. Brand esquerda + nome do projeto centro + busca direita.

#### `.sidebar`
Fixed left, 260px. Background `--bg-elevated`, scrollable. 5 seções principais (Overview/Tabelas/Medidas/Relacionamentos/Dependências) + sub-listas de tabelas/medidas (clicáveis pra anchor scroll).

#### `.search-input`
Input no topbar. JS filtra cards por nome (busca client-side).

#### `.metric-row` (overview)
Linha horizontal com 4-5 mini-cards: N tabelas | N medidas | N relacionamentos | N colunas | tamanho.

#### `.table-card`
Card por tabela. Header com nome + badge tipo (fato/dim/aux). Body com descrição + granularidade + tabela de colunas tipadas. Source M colapsável.

#### `.col-table`
Tabela HTML simples com colunas: Coluna, Tipo, Papel, Notas. Linha hover discreta.

#### `.measure-group`
Container por displayFolder. Header com nome do folder + N medidas dentro.

#### `.measure-card`
Card por medida. Nome em destaque, formatString abaixo. Pre com DAX colorizado. Box com explicação PT colapsável (`<details>`).

#### `.dax-block` (substitui `.issue-body pre`)
Mesmo padrão de syntax highlight via classes:
- `.k` → keyword (magenta)
- `.f` → function/identifier/measure (blue glow)
- `.s` → string/number (gold)
- `.c` → comment (muted)

#### `.rel-matrix`
Matriz visual ASCII art entre tabelas. Background dark, mono font, indica direção (↔, →) e cardinalidade.

#### `.dep-tree`
Árvore de dependências indentada. Cada nível com bullet + linha vertical conectora.

#### `.badge.tipo-fato` / `.tipo-dim` / `.tipo-medidas` / `.tipo-aux`
Badges pequenos pra indicar tipo de tabela. Cor segue mapeamento acima.

---

## Print stylesheet · review

```css
@media print {
  body { background: white; color: #1A1A1A; }
  body::before, body::after { display: none; }
  .scorecard, .sev-card, .issue-card, .dist-bar-container {
    box-shadow: none;
    background: white !important;
    border: 1px solid #ddd !important;
  }
  .score-num, .sev-num {
    color: #1A1A1A !important;
    -webkit-text-fill-color: #1A1A1A !important;
    filter: none !important;
  }
  .section-title, .issue-title { color: #1A1A1A !important; }
  .filters { display: none; }
}
```

Garante que ao imprimir/exportar PDF, o relatório vira light mode legível. Crítico pra circular em empresa.

---

## Print stylesheet · doc

```css
@media print {
  body { background: white; color: #1A1A1A; }
  body::before, body::after { display: none; }
  .topbar, .sidebar { display: none; }
  .main { margin-left: 0; padding: 24px; }
  .table-card, .measure-card { box-shadow: none; background: white !important; border: 1px solid #ddd !important; break-inside: avoid; }
  .dax-block { background: #f5f5f5 !important; color: #1A1A1A !important; }
  .section-title, .card-title { color: #1A1A1A !important; }
  .search-input { display: none; }
}
```

---

## Regras invioláveis ao gerar HTML

1. **CSS sempre inline** no `<head>` — sem arquivos externos
2. **JS mínimo (vanilla)** — usar `<details>/<summary>` HTML nativo pra collapse de issues. Único JS necessário é o filtro de issues (~20 linhas vanilla, IIFE, no fim do `<body>`). Sem framework, sem build, sem dependência externa.
3. **Fontes via Google Fonts CDN** — única exceção de external CDN permitida
4. **Mobile-friendly** — testar em 375px (iPhone padrão) sem quebrar layout
5. **Print stylesheet sempre presente** — se faltar, relatório é inútil em ambiente corporativo
6. **Nunca inventar cores fora dos tokens** — se precisar de tom novo, derivar via `rgba()` dos tokens existentes
7. **Footer simples** — crédito ao Claude

Diferenças na **doc**: o JS mínimo inclui busca client-side, scroll spy e collapse de DAX longo; a sidebar vira menu (hamburger) abaixo de 780px.
