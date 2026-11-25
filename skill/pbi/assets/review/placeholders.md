## Placeholders do `assets/review/relatorio.html`

Substituir SOMENTE no HTML — nunca dentro de comentários `<!-- -->` (CSS, JS, comentários ficam intocados).

### Placeholders globais

| Placeholder | Conteúdo |
|---|---|
| `{{PROJECT_NAME}}` | Ex: `Comercial_2026.pbix` |
| `{{TIMESTAMP}}` | Ex: `26 abr 2026 · 14:32` |
| `{{GENERATION_TIME}}` | Data e hora da geração (mesmo valor de `{{TIMESTAMP}}`) |
| `{{TABLES_COUNT}}`, `{{MEASURES_COUNT}}`, `{{RELATIONSHIPS_COUNT}}`, `{{SIZE}}` | Métricas |
| `{{SCORE}}` | Inteiro 0-100 (ex: `67`) |
| `{{SCORE_LABEL}}` | `Bom` / `Precisa Atenção` / `Crítico` |
| `{{VERDICT_HTML}}` | Frase de veredicto (pode usar `<strong>`/`<em>`) |
| `{{TOTAL_ISSUES}}`, `{{CRITICAL_COUNT}}`, `{{TIME_TO_FIX}}` | Contadores |
| `{{SEV_CRITICAL_COUNT}}`, `{{SEV_MEDIUM_COUNT}}`, `{{SEV_LIGHT_COUNT}}` | Contagens por severidade |

### Blocos HTML

| Placeholder | Conteúdo |
|---|---|
| `{{DIST_BAR_HTML}}` | `<div class="d-{slug}">{N}</div>` por categoria com count > 0 |
| `{{DIST_LEGEND_HTML}}` | items `.leg-item` (uma por categoria com count > 0) |
| `{{FILTERS_HTML}}` | botões `.filter-btn` (Todos + Críticos + por categoria) |
| `{{ISSUES_HTML}}` | todos os `<details class="issue-card">` |

### Padrão de cada DIST_BAR cell

```html
<div class="d-{slug-categoria}" title="{Categoria}: {N}">{N}</div>
```

`{slug-categoria}` ∈ `performance | relacionamentos | modelagem | naming | dax | doc`.

### Padrão de cada DIST_LEGEND item

```html
<div class="leg-item">
  <span class="leg-dot" style="background:{gradient};"></span>
  {Categoria}<span class="leg-num">{N}</span>
</div>
```

### Padrão de cada FILTER button

```html
<button class="filter-btn active" data-filter="all">Todos<span class="count">{N}</span></button>
<button class="filter-btn" data-filter="critical">Críticos<span class="count">{N}</span></button>
<button class="filter-btn" data-filter="{Categoria}">{Categoria}<span class="count">{N}</span></button>
```

Valores válidos de `data-filter`:
- `"all"` → mostra tudo
- `"critical"` / `"medium"` / `"light"` → por severidade
- `"{Categoria}"` (texto exato do `issue-badge.cat`) → por categoria

### Padrão de cada ISSUE card

```html
<details class="issue-card {critical|medium|light}" {open se for o 1º crítico}>
  <summary class="issue-header">
    <span class="issue-badge {critical|medium|light}">{Crítico|Médio|Leve}</span>
    <span class="issue-badge cat">{Categoria}</span>
    <div class="issue-title-wrap">
      <div class="issue-title">{Título do issue}</div>
      <div class="issue-path">{path/do/arquivo.tmdl[:linha]}</div>
    </div>
    <span class="issue-toggle">+</span>
  </summary>
  <div class="issue-body">
    <div class="section-mini">
      <div class="label">Por que importa</div>
      <p class="text">{Explicação adaptada ao contexto real.}</p>
    </div>
    <div class="section-mini">
      <div class="label">Como corrigir</div>
      <p class="text">{Passo prático.}</p>
    </div>
    <div class="section-mini">
      <div class="label">Snippet sugerido</div>
      <pre><span class="c">// comentário</span>
<span class="k">keyword</span> <span class="f">funcao</span>(<span class="s">"string"</span>)</pre>
    </div>
  </div>
</details>
```

Severidade escolhe a cor automática via classe: `critical` (magenta), `medium` (blue glow), `light` (gold).
