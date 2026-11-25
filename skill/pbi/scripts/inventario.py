#!/usr/bin/env python3
"""
inventario.py — mapa determinístico de um projeto Power BI (PBIP).

Lê o modelo semântico (TMDL ou model.bim) e o(s) relatório(s) (PBIR ou report.json legado)
e gera, na pasta de saída (padrão: <raiz>/_pbi/):

  inventario.json         tabelas, colunas, medidas, relacionamentos, RLS, dependências,
                          uso em visuais, impacto transitivo, convenções detectadas e
                          checks mecânicos (catálogo: core/checks.md)
  inventario-resumo.md    resumo curto para leitura humana

Uso:
  python inventario.py <pasta do projeto PBIP | pasta .SemanticModel> [--saida DIR] [--modelo NOME]

Só biblioteca padrão. Somente leitura no projeto: escreve apenas na pasta de saída.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path

VERSAO = "1.0"

AUTO_DATE_RE = re.compile(r"^(LocalDateTable_|DateTableTemplate_)", re.I)
NUMERICOS = {"int64", "double", "decimal", "currency"}

# ID -> (família, severidade, detector, título)   — espelha core/checks.md
CATALOGO = {
    "model-no-date-table": ("Modelagem", "critical", "script", "Nenhuma tabela marcada como tabela de datas"),
    "model-date-table-disconnected": ("Modelagem", "critical", "script", "Tabela calendário sem relacionamento ativo"),
    "rls-filter-not-propagating": ("Segurança", "critical", "script", "Filtro de RLS que não chega em nenhuma fato"),
    "rls-on-fact-table": ("Segurança", "medium", "script", "Filtro de RLS direto na tabela fato"),
    "rls-role-without-filter": ("Segurança", "light", "script", "Role sem filtro de tabela"),
    "model-calendar-using-auto-hierarchy": ("Modelagem", "critical", "script", "Calendário próprio usando hierarquia automática (LocalDateTable)"),
    "model-circular-reference": ("Modelagem", "critical", "script", "Caminhos de filtro ambíguos entre tabelas"),
    "rel-bidirectional-unnecessary": ("Relacionamentos", "critical", "script+revisar", "Relacionamento bidirecional"),
    "rel-many-to-many-without-bridge": ("Relacionamentos", "critical", "script+revisar", "Relacionamento muitos-para-muitos direto"),
    "rel-one-to-one-suspicious": ("Relacionamentos", "medium", "script", "Relacionamento 1:1"),
    "rel-snowflake-suspicious": ("Relacionamentos", "medium", "script+revisar", "Dimensão filtrando dimensão (snowflake)"),
    "rel-inactive-orphan": ("Relacionamentos", "light", "script", "Relacionamento inativo sem USERELATIONSHIP"),
    "perf-auto-date-time": ("Performance", "medium", "script", "Auto Date/Time ligado"),
    "perf-calc-column-should-be-measure": ("Performance", "medium", "script+revisar", "Coluna calculada numérica que poderia ser medida"),
    "perf-string-as-key": ("Performance", "medium", "script+revisar", "Relacionamento por coluna texto"),
    "perf-unused-columns": ("Performance", "light", "script", "Colunas sem uso"),
    "naming-mixed-conventions": ("Naming", "medium", "script", "Nomes de medidas sem padrão dominante"),
    "naming-no-table-prefix": ("Naming", "light", "script", "Tabelas fato/dimensão sem prefixo de papel"),
    "naming-acronym-no-context": ("Naming", "light", "script", "Medidas com sigla/nome curto e sem descrição"),
    "dax-divide-operator": ("DAX", "medium", "script", "Divisão com operador / em vez de DIVIDE"),
    "dax-nested-calculate": ("DAX", "medium", "script+revisar", "CALCULATE aninhado"),
    "dax-filter-whole-table": ("DAX", "medium", "script", "FILTER sobre tabela inteira como filtro de CALCULATE"),
    "dax-iferror": ("DAX", "light", "script", "Uso de IFERROR/ISERROR"),
    "dax-unused-variables": ("DAX", "light", "script", "Variável declarada e não usada"),
    "rel-columns-different-types": ("Relacionamentos", "critical", "script", "Relacionamento entre colunas de tipos diferentes"),
    "rls-and-userelationship-same-table": ("Segurança", "critical", "script", "USERELATIONSHIP em tabela filtrada por RLS"),
    "perf-floating-point": ("Performance", "medium", "script", "Coluna com tipo de ponto flutuante (double)"),
    "perf-directquery-time-intelligence": ("Performance", "medium", "script", "Time intelligence em modelo DirectQuery"),
    "perf-calc-column-related": ("Performance", "light", "script", "Coluna calculada usando RELATED"),
    "dax-duplicate-measures": ("DAX", "medium", "script", "Medidas com a mesma expressão"),
    "dax-measure-is-reference": ("DAX", "light", "script", "Medida que é só referência a outra medida"),
    "dax-qualified-measure-ref": ("DAX", "light", "script", "Medida referenciada com nome de tabela"),
    "dax-unqualified-column-ref": ("DAX", "light", "script", "Coluna referenciada sem nome de tabela"),
    "dax-intersect": ("DAX", "light", "script", "INTERSECT usado como relacionamento virtual (usar TREATAS)"),
    "dax-evaluateandlog": ("DAX", "light", "script", "EVALUATEANDLOG em medida"),
    "fmt-hide-foreign-keys": ("Documentação", "light", "script", "Chave estrangeira visível na fato"),
    "fmt-numeric-summarize": ("Documentação", "light", "script", "Coluna numérica visível com soma automática"),
    "fmt-month-not-sorted": ("Documentação", "light", "script", "Coluna de mês em texto sem ordenação"),
    "naming-leading-trailing-space": ("Naming", "light", "script", "Nome com espaço no início ou no fim"),
    "model-table-without-relationship": ("Modelagem", "light", "script", "Tabela sem relacionamento"),
    "doc-measures-no-description": ("Documentação", "light", "script", "Medidas sem descrição"),
    "doc-tables-no-description": ("Documentação", "light", "script", "Tabelas sem descrição"),
    "measure-no-format-string": ("Documentação", "light", "script", "Medidas sem formatString"),
    "measure-unused": ("Documentação", "light", "script", "Medidas sem uso"),
    "doc-no-business-key-marked": ("Documentação", "light", "script", "Dimensões sem coluna-chave marcada"),
    "data-source-personal-path": ("Documentação", "medium", "script", "Fonte de dados com caminho pessoal/local"),
}
ORDEM_SEV = {"critical": 0, "medium": 1, "light": 2}

PATH_PESSOAL = ["\\users\\", "/users/", "onedrive", "google drive", "googledrive", "drives compartilhados",
                "meu drive", "my drive", "\\desktop\\", "\\downloads\\", "\\documents\\", "\\documentos\\"]

ITERADORES = ["FILTER", "SUMX", "AVERAGEX", "MAXX", "MINX", "COUNTX", "COUNTAX", "RANKX", "ADDCOLUMNS",
              "GENERATE", "SELECTCOLUMNS", "CONCATENATEX", "PRODUCTX", "MEDIANX"]
FUNCS_AGREGACAO = re.compile(
    r"\b(CALCULATE|CALCULATETABLE|SUM|SUMX|AVERAGE|AVERAGEX|MIN|MINX|MAX|MAXX|COUNT\w*|DISTINCTCOUNT\w*|"
    r"EARLIER|EARLIEST|RANKX|RELATEDTABLE|LOOKUPVALUE|FILTER|ALL\w*|VALUES|SUMMARIZE\w*|TOPN|PATH\w*)\s*\(",
    re.I)


# =============================================================================
# Utilitários
# =============================================================================

def ler_texto(p):
    return Path(p).read_text(encoding="utf-8-sig")


def nivel_indent(linha):
    n = 0
    for ch in linha:
        if ch == "\t":
            n += 4
        elif ch == " ":
            n += 1
        else:
            break
    return n // 4


def parse_nome(s):
    """Lê um nome TMDL (entre aspas simples ou token) e devolve (nome, resto)."""
    s = s.lstrip()
    if s.startswith("'"):
        i, out = 1, []
        while i < len(s):
            if s[i] == "'":
                if i + 1 < len(s) and s[i + 1] == "'":
                    out.append("'")
                    i += 2
                    continue
                return "".join(out), s[i + 1:]
            out.append(s[i])
            i += 1
        return "".join(out), ""
    m = re.match(r"([^\s=:]+)", s)
    if not m:
        return None, s
    return m.group(1), s[m.end():]


def split_ref_coluna(s):
    """'Tabela'.'Coluna' | Tabela.Coluna -> (tabela, coluna)."""
    s = (s or "").strip()
    if s.startswith("'"):
        t, resto = parse_nome(s)
        resto = resto.lstrip(".")
    else:
        if "." not in s:
            return None, s
        t, resto = s.split(".", 1)
    if resto.startswith("'"):
        c, _ = parse_nome(resto)
    else:
        c = resto.strip()
    return t, c


def dedent(linhas):
    nao_vazias = [l for l in linhas if l.strip()]
    if not nao_vazias:
        return ""
    def larg(l):
        return len(l) - len(l.lstrip(" \t"))
    m = min(larg(l) for l in nao_vazias)
    return "\n".join(l[m:] if l.strip() else "" for l in linhas).strip("\n")


def bool_prop(v, padrao=False):
    if v is None:
        return padrao
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() not in ("false", "0", "no")


def unq(v):
    """Remove aspas simples de nome TMDL em valor de propriedade ('Mês Num' -> Mês Num)."""
    if isinstance(v, str) and v.strip().startswith("'"):
        return parse_nome(v)[0]
    return v


def chave(*partes):
    return tuple((p or "").lower() for p in partes)


# =============================================================================
# Parser TMDL (genérico, por indentação)
# =============================================================================

PALAVRAS_OBJ = {
    "model", "table", "column", "measure", "partition", "hierarchy", "level", "annotation",
    "extendedProperty", "calculationGroup", "calculationItem", "variation", "relationship", "role",
    "tablePermission", "columnPermission", "member", "expression", "ref", "perspective",
    "perspectiveTable", "perspectiveColumn", "perspectiveMeasure", "perspectiveHierarchy", "culture",
    "dataSource", "queryGroup", "function", "calendar", "linguisticMetadata", "translation",
    "changedProperty", "database",
}


def ler_expressao(linhas, i, ind, depois):
    """Lê a expressão iniciada após '=' na linha i. Devolve (texto, próximo índice)."""
    depois = depois.strip()
    if depois.startswith("```"):
        corpo, j = [], i + 1
        while j < len(linhas) and linhas[j].strip() != "```":
            corpo.append(linhas[j])
            j += 1
        return dedent(corpo), j + 1
    corpo, j = [], i + 1
    while j < len(linhas):
        l = linhas[j]
        if l.strip() and nivel_indent(l) <= ind + 1:
            break
        corpo.append(l)
        j += 1
    while corpo and not corpo[-1].strip():
        corpo.pop()
    cont = dedent(corpo)
    if depois and cont:
        return depois + "\n" + cont, j
    return (depois or cont), j


def parse_tmdl(texto, arquivo):
    linhas = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    raiz = {"kind": "_raiz", "children": [], "props": {}}
    pilha = [(-1, raiz)]
    desc = []
    i = 0
    while i < len(linhas):
        bruta = linhas[i]
        st = bruta.strip()
        if not st:
            i += 1
            continue
        ind = nivel_indent(bruta)
        if st.startswith("///"):
            desc.append(st[3:].strip())
            i += 1
            continue
        if st.startswith("//"):
            i += 1
            continue
        while pilha and pilha[-1][0] >= ind:
            pilha.pop()
        pai = pilha[-1][1]
        m = re.match(r"^([A-Za-z_]+)(.*)$", st)
        if not m:
            desc = []
            i += 1
            continue
        tok, resto = m.group(1), m.group(2)
        if resto.startswith(":"):
            v = resto[1:].strip()
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                v = v[1:-1]
            pai["props"][tok] = v
            desc = []
            i += 1
            continue
        if tok in PALAVRAS_OBJ and (resto == "" or resto[0] in " \t="):
            nome, rem = (None, resto)
            if resto.strip() and not resto.strip().startswith("="):
                nome, rem = parse_nome(resto)
            expr = None
            prox = i + 1
            if rem.strip().startswith("="):
                expr, prox = ler_expressao(linhas, i, ind, rem.strip()[1:])
            no = {"kind": tok, "name": nome, "expr": expr, "props": {}, "children": [],
                  "desc": "\n".join(desc) if desc else None, "line": i + 1, "file": arquivo}
            pai["children"].append(no)
            pilha.append((ind, no))
            desc = []
            i = prox
            continue
        if re.match(r"^\s*=", resto):
            expr, prox = ler_expressao(linhas, i, ind, resto.split("=", 1)[1])
            pai["props"][tok] = expr
            desc = []
            i = prox
            continue
        if resto.strip() == "":
            pai["props"][tok] = True
        desc = []
        i += 1
    return raiz


# =============================================================================
# Normalização do modelo (TMDL e model.bim -> mesma estrutura)
# =============================================================================

def novo_modelo():
    return {"tabelas": {}, "relacionamentos": [], "roles": [], "expressoes": [], "anotacoes": {},
            "funcoes": [], "formato": None}


def carregar_tmdl(def_dir, raiz_proj):
    modelo = novo_modelo()
    modelo["formato"] = "tmdl"
    for arq in sorted(def_dir.rglob("*.tmdl")):
        rel = arq.relative_to(raiz_proj).as_posix()
        try:
            arvore = parse_tmdl(ler_texto(arq), rel)
        except Exception as e:  # noqa
            modelo.setdefault("erros", []).append(f"{rel}: {e}")
            continue
        for no in arvore["children"]:
            k = no["kind"]
            if k == "table":
                modelo["tabelas"][no["name"]] = tabela_de_tmdl(no)
            elif k == "relationship":
                p = no["props"]
                dt, dc = split_ref_coluna(p.get("fromColumn"))
                pt, pc = split_ref_coluna(p.get("toColumn"))
                modelo["relacionamentos"].append({
                    "id": no["name"], "de_tabela": dt, "de_coluna": dc, "para_tabela": pt, "para_coluna": pc,
                    "card_de": p.get("fromCardinality", "many"), "card_para": p.get("toCardinality", "one"),
                    "direcao": "both" if p.get("crossFilteringBehavior") == "bothDirections" else "single",
                    "seguranca_both": p.get("securityFilteringBehavior") == "bothDirections",
                    "ativo": bool_prop(p.get("isActive"), True), "arquivo": rel, "linha": no["line"]})
            elif k == "role":
                perms = [{"tabela": c["name"], "expressao": c["expr"] or ""}
                         for c in no["children"] if c["kind"] == "tablePermission"]
                modelo["roles"].append({"nome": no["name"], "permissoes": perms,
                                        "permissao_modelo": no["props"].get("modelPermission"),
                                        "arquivo": rel, "linha": no["line"]})
            elif k == "expression":
                modelo["expressoes"].append({"nome": no["name"], "expressao": no["expr"] or "",
                                             "arquivo": rel, "linha": no["line"]})
            elif k == "model":
                for c in no["children"]:
                    if c["kind"] == "annotation":
                        modelo["anotacoes"][c["name"]] = (c["expr"] or "").strip()
            elif k == "function":
                modelo["funcoes"].append({"nome": no["name"], "expressao": no["expr"] or "",
                                          "arquivo": rel, "linha": no["line"]})
    return modelo


def tabela_de_tmdl(no):
    p = no["props"]
    t = {"nome": no["name"], "arquivo": no["file"], "linha": no["line"], "descricao": no["desc"],
         "oculta": bool_prop(p.get("isHidden")), "data_category": p.get("dataCategory"),
         "colunas": {}, "medidas": {}, "particoes": [], "hierarquias": [], "calc_items": [],
         "calc_group": False}
    for c in no["children"]:
        k = c["kind"]
        cp = c["props"]
        if k == "column":
            variacao = None
            for v in c["children"]:
                if v["kind"] == "variation":
                    variacao = v["props"].get("defaultHierarchy")
            t["colunas"][c["name"]] = {
                "nome": c["name"], "tipo": cp.get("dataType"), "oculta": bool_prop(cp.get("isHidden")),
                "chave": bool_prop(cp.get("isKey")), "calculada": c["expr"] is not None,
                "expressao": c["expr"], "sort_by": unq(cp.get("sortByColumn")), "formato": cp.get("formatString"),
                "data_category": cp.get("dataCategory"), "variacao": variacao, "descricao": c["desc"],
                "summarize_by": cp.get("summarizeBy"),
                "linha": c["line"], "tipo_coluna": cp.get("type")}
        elif k == "measure":
            t["medidas"][c["name"]] = {
                "nome": c["name"], "tabela": no["name"], "expressao": c["expr"] or "",
                "formato": cp.get("formatString"), "formato_dinamico": "formatStringDefinition" in cp,
                "pasta": cp.get("displayFolder"), "descricao": c["desc"], "oculta": bool_prop(cp.get("isHidden")),
                "arquivo": no["file"], "linha": c["line"]}
        elif k == "partition":
            t["particoes"].append({"nome": c["name"], "tipo": (c["expr"] or "").strip(),
                                   "modo": cp.get("mode"), "fonte": cp.get("source") if isinstance(cp.get("source"), str) else "",
                                   "linha": c["line"]})
        elif k == "hierarchy":
            niveis = [{"nome": lv["name"], "coluna": unq(lv["props"].get("column"))}
                      for lv in c["children"] if lv["kind"] == "level"]
            t["hierarquias"].append({"nome": c["name"], "niveis": niveis})
        elif k == "calculationGroup":
            t["calc_group"] = True
            for it in c["children"]:
                if it["kind"] == "calculationItem":
                    t["calc_items"].append({"nome": it["name"], "expressao": it["expr"] or "", "linha": it["line"]})
    return t


def _expr_bim(v):
    if isinstance(v, list):
        return "\n".join(v)
    return v or ""


def carregar_bim(bim, raiz_proj):
    modelo = novo_modelo()
    modelo["formato"] = "bim"
    rel = bim.relative_to(raiz_proj).as_posix()
    dados = json.loads(ler_texto(bim))
    m = dados.get("model", dados)
    for a in m.get("annotations", []) or []:
        modelo["anotacoes"][a.get("name")] = str(_expr_bim(a.get("value"))).strip()
    for tb in m.get("tables", []) or []:
        t = {"nome": tb["name"], "arquivo": rel, "linha": None, "descricao": tb.get("description"),
             "oculta": bool(tb.get("isHidden")), "data_category": tb.get("dataCategory"),
             "colunas": {}, "medidas": {}, "particoes": [], "hierarquias": [], "calc_items": [],
             "calc_group": "calculationGroup" in tb}
        for c in tb.get("columns", []) or []:
            if c.get("type") == "rowNumber":
                continue
            var = None
            for v in c.get("variations", []) or []:
                dh = v.get("defaultHierarchy") or {}
                var = f"{dh.get('table')}.{dh.get('hierarchy')}"
            calc = c.get("type") == "calculated"
            t["colunas"][c["name"]] = {
                "nome": c["name"], "tipo": c.get("dataType"), "oculta": bool(c.get("isHidden")),
                "chave": bool(c.get("isKey")), "calculada": calc,
                "expressao": _expr_bim(c.get("expression")) if calc else None,
                "sort_by": c.get("sortByColumn"), "formato": c.get("formatString"),
                "data_category": c.get("dataCategory"), "variacao": var, "descricao": c.get("description"),
                "summarize_by": c.get("summarizeBy"),
                "linha": None, "tipo_coluna": c.get("type")}
        for me in tb.get("measures", []) or []:
            t["medidas"][me["name"]] = {
                "nome": me["name"], "tabela": tb["name"], "expressao": _expr_bim(me.get("expression")),
                "formato": me.get("formatString"), "formato_dinamico": "formatStringDefinition" in me,
                "pasta": me.get("displayFolder"), "descricao": me.get("description"),
                "oculta": bool(me.get("isHidden")), "arquivo": rel, "linha": None}
        for pa in tb.get("partitions", []) or []:
            src = pa.get("source", {}) or {}
            t["particoes"].append({"nome": pa.get("name"), "tipo": src.get("type", ""), "modo": pa.get("mode"),
                                   "fonte": _expr_bim(src.get("expression")), "linha": None})
        for h in tb.get("hierarchies", []) or []:
            t["hierarquias"].append({"nome": h.get("name"), "niveis": [{"nome": lv.get("name"), "coluna": lv.get("column")} for lv in h.get("levels", [])]})
        for it in (tb.get("calculationGroup") or {}).get("calculationItems", []) or []:
            t["calc_items"].append({"nome": it.get("name"), "expressao": _expr_bim(it.get("expression")), "linha": None})
        modelo["tabelas"][tb["name"]] = t
    for r in m.get("relationships", []) or []:
        modelo["relacionamentos"].append({
            "id": r.get("name"), "de_tabela": r.get("fromTable"), "de_coluna": r.get("fromColumn"),
            "para_tabela": r.get("toTable"), "para_coluna": r.get("toColumn"),
            "card_de": r.get("fromCardinality", "many"), "card_para": r.get("toCardinality", "one"),
            "direcao": "both" if r.get("crossFilteringBehavior") == "bothDirections" else "single",
            "seguranca_both": r.get("securityFilteringBehavior") == "bothDirections",
            "ativo": r.get("isActive", True), "arquivo": rel, "linha": None})
    for ro in m.get("roles", []) or []:
        perms = [{"tabela": tp.get("name"), "expressao": _expr_bim(tp.get("filterExpression"))}
                 for tp in ro.get("tablePermissions", []) or []]
        modelo["roles"].append({"nome": ro.get("name"), "permissoes": perms,
                                "permissao_modelo": ro.get("modelPermission"), "arquivo": rel, "linha": None})
    for ex in m.get("expressions", []) or []:
        modelo["expressoes"].append({"nome": ex.get("name"), "expressao": _expr_bim(ex.get("expression")),
                                     "arquivo": rel, "linha": None})
    return modelo


# =============================================================================
# DAX: limpeza, máscara, referências
# =============================================================================

def _pular_delim(s, i, fecha):
    j = i + 1
    while j < len(s):
        if s[j] == fecha:
            if j + 1 < len(s) and s[j + 1] == fecha:
                j += 2
                continue
            return j
        j += 1
    return len(s) - 1


def limpar_dax(expr):
    """Remove comentários e conteúdo de strings; preserva [nomes] e 'tabelas'."""
    out, i, n = [], 0, len(expr or "")
    s = expr or ""
    while i < n:
        c = s[i]
        if c == '"':
            j = _pular_delim(s, i, '"')
            out.append('""')
            i = j + 1
        elif s.startswith("//", i) or s.startswith("--", i):
            j = s.find("\n", i)
            i = n if j < 0 else j
        elif s.startswith("/*", i):
            j = s.find("*/", i + 2)
            out.append(" ")
            i = n if j < 0 else j + 2
        elif c in "'[":
            j = _pular_delim(s, i, "'" if c == "'" else "]")
            out.append(s[i:j + 1])
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def mascarar(limpo):
    """Troca o conteúdo de [..] e '..' por '~' mantendo posições (para varreduras estruturais)."""
    out, i, n = list(limpo), 0, len(limpo)
    while i < n:
        c = limpo[i]
        if c in "'[":
            j = _pular_delim(limpo, i, "'" if c == "'" else "]")
            for k in range(i + 1, j):
                out[k] = "~"
            i = j + 1
        else:
            i += 1
    return "".join(out)


REF_RE = re.compile(r"(?<![\w'\]~])(?:'((?:[^']|'')+)'|([^\W\d]\w*))?\[((?:[^\]]|\]\])+)\]", re.U)


def chamadas(masc, fname):
    """Spans (inicio, abre, fecha) de chamadas fname( ... ) no texto mascarado."""
    res = []
    for m in re.finditer(r"\b" + fname + r"\s*\(", masc, re.I):
        abre = m.end() - 1
        prof, j = 0, abre
        while j < len(masc):
            if masc[j] == "(":
                prof += 1
            elif masc[j] == ")":
                prof -= 1
                if prof == 0:
                    break
            j += 1
        res.append((m.start(), abre, j))
    return res


def args_topo(masc, abre, fecha):
    """Spans dos argumentos de primeiro nível de uma chamada."""
    spans, prof, ini = [], 0, abre + 1
    for j in range(abre + 1, fecha):
        ch = masc[j]
        if ch == "(":
            prof += 1
        elif ch == ")":
            prof -= 1
        elif ch == "," and prof == 0:
            spans.append((ini, j))
            ini = j + 1
    spans.append((ini, fecha))
    return spans


class Indice:
    def __init__(self, modelo):
        self.modelo = modelo
        self.medidas = {}       # lower -> (tabela, nome)
        self.colunas = {}       # (tlower, clower) -> (tabela, nome)
        self.tabelas = {}       # lower -> nome
        self.col_por_nome = defaultdict(list)
        for tn, t in modelo["tabelas"].items():
            self.tabelas[tn.lower()] = tn
            for mn in t["medidas"]:
                self.medidas[mn.lower()] = (tn, mn)
            for cn in t["colunas"]:
                self.colunas[chave(tn, cn)] = (tn, cn)
                self.col_por_nome[cn.lower()].append((tn, cn))

    def deps(self, expr, tabela_casa=None):
        limpo = limpar_dax(expr)
        medidas, colunas, soltas = set(), set(), set()
        for m in REF_RE.finditer(limpo):
            tq, tu, nome = m.group(1), m.group(2), m.group(3).replace("]]", "]")
            tab = (tq.replace("''", "'") if tq else tu)
            if tab:
                tc = self.colunas.get(chave(tab, nome))
                if tc:
                    colunas.add(tc)
                elif nome.lower() in self.medidas:
                    medidas.add(self.medidas[nome.lower()][1])
                elif tab.lower() in self.tabelas:
                    soltas.add(f"{tab}[{nome}]")
            else:
                if nome.lower() in self.medidas:
                    medidas.add(self.medidas[nome.lower()][1])
                elif tabela_casa and chave(tabela_casa, nome) in self.colunas:
                    colunas.add(self.colunas[chave(tabela_casa, nome)])
                elif len(self.col_por_nome.get(nome.lower(), [])) == 1:
                    colunas.add(self.col_por_nome[nome.lower()][0])
                else:
                    soltas.add(f"[{nome}]")
        return medidas, colunas, soltas

    def userelationships(self, expr):
        limpo = limpar_dax(expr)
        masc = mascarar(limpo)
        pares = []
        for ini, abre, fecha in chamadas(masc, "USERELATIONSHIP"):
            refs = []
            for a, b in args_topo(masc, abre, fecha):
                m = REF_RE.search(limpo[a:b])
                if m:
                    tab = (m.group(1) or "").replace("''", "'") or m.group(2)
                    refs.append(chave(tab, m.group(3)))
            if len(refs) == 2:
                pares.append(frozenset(refs))
        return pares


# =============================================================================
# Relatórios (PBIR e legado)
# =============================================================================

def campos_em(obj):
    """Varre JSON de visual/filtro e devolve [(tipo, entidade, propriedade, agregado)]."""
    aliases = {}

    def coletar(o):
        if isinstance(o, dict):
            fr = o.get("From")
            if isinstance(fr, list):
                for f in fr:
                    if isinstance(f, dict) and "Name" in f and "Entity" in f:
                        aliases[f["Name"]] = f["Entity"]
            for v in o.values():
                coletar(v)
        elif isinstance(o, list):
            for v in o:
                coletar(v)

    coletar(obj)
    out = []

    def entidade(e):
        if not isinstance(e, dict):
            return None
        sr = e.get("SourceRef")
        if isinstance(sr, dict):
            return sr.get("Entity") or aliases.get(sr.get("Source"))
        return None

    def andar(o, agg=False):
        if isinstance(o, dict):
            for k, tipo in (("Measure", "medida"), ("Column", "coluna"), ("PropertyVariationSource", "coluna")):
                v = o.get(k)
                if isinstance(v, dict) and "Property" in v:
                    ent = entidade(v.get("Expression"))
                    if ent:
                        out.append((tipo, ent, v["Property"], agg))
            hl = o.get("HierarchyLevel")
            if isinstance(hl, dict):
                h = (hl.get("Expression") or {}).get("Hierarchy") or {}
                ent = entidade(h.get("Expression"))
                if ent and h.get("Hierarchy"):
                    out.append(("nivel", ent, f"{h.get('Hierarchy')}|{hl.get('Level')}", agg))
            for k, v in o.items():
                andar(v, agg or k == "Aggregation")
        elif isinstance(o, list):
            for v in o:
                andar(v, agg)

    andar(obj)
    return out


def _json_ou_none(p):
    try:
        return json.loads(ler_texto(p))
    except Exception:
        return None


def _titulo_pbir(v):
    try:
        t = v["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"]["expr"]["Literal"]["Value"]
        return t.strip("'")
    except Exception:
        return None


def carregar_relatorio(rdir, raiz_proj):
    rel = {"dir": rdir.relative_to(raiz_proj).as_posix(), "formato": None, "modelo_ref": None, "paginas": []}
    pbir = _json_ou_none(rdir / "definition.pbir")
    if pbir:
        rel["modelo_ref"] = ((pbir.get("datasetReference") or {}).get("byPath") or {}).get("path")
    pages_dir = rdir / "definition" / "pages"
    if pages_dir.is_dir():
        rel["formato"] = "pbir"
        rj = _json_ou_none(rdir / "definition" / "report.json")
        if rj and rj.get("filterConfig"):
            rel["paginas"].append({"nome": "(filtros do relatório)", "visuais": [
                {"id": "filtros", "tipo": "filtro", "titulo": None, "campos": campos_em(rj.get("filterConfig"))}]})
        for pdir in sorted(p for p in pages_dir.iterdir() if p.is_dir()):
            pj = _json_ou_none(pdir / "page.json") or {}
            pag = {"nome": pj.get("displayName") or pdir.name, "visuais": []}
            if pj.get("filterConfig"):
                pag["visuais"].append({"id": "filtros-pagina", "tipo": "filtro", "titulo": None,
                                       "campos": campos_em(pj["filterConfig"])})
            vdir = pdir / "visuals"
            if vdir.is_dir():
                for vj_path in sorted(vdir.glob("*/visual.json")):
                    vj = _json_ou_none(vj_path) or {}
                    tipo = (vj.get("visual") or {}).get("visualType") or ("grupo" if "visualGroup" in vj else None)
                    pag["visuais"].append({"id": vj.get("name") or vj_path.parent.name, "tipo": tipo,
                                           "titulo": _titulo_pbir(vj), "campos": campos_em(vj)})
            rel["paginas"].append(pag)
        return rel
    legado = rdir / "report.json"
    if legado.is_file():
        rel["formato"] = "legado"
        rj = _json_ou_none(legado) or {}

        def parse_str(x):
            if isinstance(x, str) and x.strip()[:1] in "{[":
                try:
                    return json.loads(x)
                except Exception:
                    return None
            return x if isinstance(x, (dict, list)) else None

        if parse_str(rj.get("filters")):
            rel["paginas"].append({"nome": "(filtros do relatório)", "visuais": [
                {"id": "filtros", "tipo": "filtro", "titulo": None, "campos": campos_em(parse_str(rj.get("filters")))}]})
        for sec in rj.get("sections", []) or []:
            pag = {"nome": sec.get("displayName") or sec.get("name"), "visuais": []}
            if parse_str(sec.get("filters")):
                pag["visuais"].append({"id": "filtros-pagina", "tipo": "filtro", "titulo": None,
                                       "campos": campos_em(parse_str(sec.get("filters")))})
            for vc in sec.get("visualContainers", []) or []:
                cfg = parse_str(vc.get("config")) or {}
                sv = cfg.get("singleVisual") or {}
                campos = campos_em(cfg) + campos_em(parse_str(vc.get("filters")) or [])
                pag["visuais"].append({"id": cfg.get("name"), "tipo": sv.get("visualType"), "titulo": None,
                                       "campos": campos})
            rel["paginas"].append(pag)
    return rel


# =============================================================================
# Análise
# =============================================================================

def classe_nome(n):
    letras = re.sub(r"[^A-Za-zÀ-ÿ]", "", n)
    if not letras:
        return None
    maius = letras.upper() == letras and len(letras) > 3
    if " " in n.strip():
        return "MAIÚSCULAS" if maius else "Title Case"
    if "_" in n:
        return "MAIÚSCULAS" if maius else "snake_case"
    if maius:
        return "MAIÚSCULAS"
    if n[:1].islower() and any(ch.isupper() for ch in n):
        return "camelCase"
    if n[:1].isupper() and any(ch.isupper() for ch in n[1:]):
        return "PascalCase"
    return None  # palavra única: compatível com vários padrões


PREFIXOS_PAPEL = {"f", "ft", "fat", "fato", "fact", "fct", "d", "dm", "dim", "dimensao", "dimensão"}


def prefixo_tabela(n):
    m = re.match(r"^([A-Za-zÀ-ÿ]{1,8})[_ ]", n)
    if m:
        return m.group(1).lower() + n[m.end() - 1]
    m = re.match(r"^([fd])[A-Z]", n)
    if m:
        return m.group(1)
    return None


def analisar(modelo, relatorios, raiz):
    idx = Indice(modelo)
    tabs = modelo["tabelas"]
    avisos = []
    issues = []

    def issue(cid, objetos, detalhe, arquivo=None, linha=None, severidade=None):
        fam, sev, det, tit = CATALOGO[cid]
        sev = severidade or sev
        issues.append({"id": cid, "familia": fam, "severidade": sev, "detector": det, "titulo": tit,
                       "objetos": objetos, "detalhe": detalhe, "arquivo": arquivo, "linha": linha})

    # ---------- dependências de todas as expressões ----------
    dep_medida = {}           # nome medida -> (set medidas, set colunas)
    usados_col = defaultdict(set)   # chave col -> set de "origens"
    soltas_total = Counter()
    pares_userel = []

    def registrar(expr, origem, casa=None, ignorar_nuas=False):
        ms, cs, soltas = idx.deps(expr, casa)
        for c in cs:
            usados_col[chave(*c)].add(origem)
        if ignorar_nuas:
            # tabela calculada: [Date] de CALENDAR, [Value] de GENERATESERIES, colunas de ADDCOLUMNS etc.
            soltas = {x for x in soltas if not x.startswith("[")}
        soltas_total.update(soltas)
        pares_userel.extend(idx.userelationships(expr))
        return ms, cs

    for tn, t in tabs.items():
        for mn, m in t["medidas"].items():
            dep_medida[mn] = registrar(m["expressao"], f"medida:{mn}", tn)
        for cn, c in t["colunas"].items():
            if c["calculada"]:
                c["_deps"] = registrar(c["expressao"] or "", f"coluna:{tn}[{cn}]", tn)
        for p in t["particoes"]:
            if p["tipo"].lower() == "calculated":
                t["_deps_calc"] = registrar(p["fonte"] or "", f"tabela_calculada:{tn}", ignorar_nuas=True)
        for it in t["calc_items"]:
            registrar(it["expressao"], f"calc_item:{tn}.{it['nome']}", tn)
    for ro in modelo["roles"]:
        for pe in ro["permissoes"]:
            ms, cs = registrar(pe["expressao"], f"rls:{ro['nome']}", pe["tabela"])
            pe["depende_de"] = {"medidas": sorted(ms), "colunas": sorted(f"{a}[{b}]" for a, b in cs)}
    for r in modelo["relacionamentos"]:
        for t_, c_ in ((r["de_tabela"], r["de_coluna"]), (r["para_tabela"], r["para_coluna"])):
            usados_col[chave(t_, c_)].add(f"relacionamento:{r['id']}")
    for tn, t in tabs.items():
        for cn, c in t["colunas"].items():
            if c.get("sort_by"):
                usados_col[chave(tn, c["sort_by"])].add(f"ordenacao:{tn}[{cn}]")
        for h in t["hierarquias"]:
            for lv in h["niveis"]:
                if lv.get("coluna"):
                    usados_col[chave(tn, lv["coluna"])].add(f"hierarquia:{tn}.{h['nome']}")

    # medidas usadas por outras expressões (inclui calc items, colunas, RLS)
    medida_usada_por = defaultdict(set)
    for mn, (ms, _) in dep_medida.items():
        for d in ms:
            medida_usada_por[d].add(mn)
    medida_usada_extra = defaultdict(set)
    for tn, t in tabs.items():
        for cn, c in t["colunas"].items():
            if c.get("_deps"):
                for d in c["_deps"][0]:
                    medida_usada_extra[d].add(f"coluna:{tn}[{cn}]")
        if t.get("_deps_calc"):
            for d in t["_deps_calc"][0]:
                medida_usada_extra[d].add(f"tabela_calculada:{tn}")
        for it in t["calc_items"]:
            for d in idx.deps(it["expressao"], tn)[0]:
                medida_usada_extra[d].add(f"calc_item:{tn}.{it['nome']}")

    def fechamento(inicio):
        vistos, fila = set(), deque(inicio)
        while fila:
            x = fila.popleft()
            for y in medida_usada_por.get(x, ()):
                if y not in vistos:
                    vistos.add(y)
                    fila.append(y)
        return vistos

    # ---------- uso em visuais ----------
    tem_relatorio = bool(relatorios)
    uso_vis = defaultdict(list)   # ("medida"|"coluna", tlower, nlower) -> [ {ref, agregado} ]
    hier_idx = {}
    for tn, t in tabs.items():
        for h in t["hierarquias"]:
            hier_idx[chave(tn, h["nome"])] = h
    total_vis = 0
    for rel in relatorios:
        for pag in rel["paginas"]:
            for v in pag["visuais"]:
                if v["tipo"] != "filtro":
                    total_vis += 1
                ref = f"{pag['nome']} › {v.get('titulo') or v['tipo'] or 'visual'} [{v['id']}]"
                vistos = set()
                for tipo, ent, prop, agg in v["campos"]:
                    if tipo == "nivel":
                        hn, lv = prop.split("|", 1)
                        h = hier_idx.get(chave(ent, hn))
                        col = next((n["coluna"] for n in (h or {}).get("niveis", [])
                                    if (n["nome"] or "").lower() == lv.lower()), None)
                        if not col:
                            continue
                        tipo, prop = "coluna", col
                    k = (tipo, (ent or "").lower(), prop.lower())
                    if tipo == "medida":
                        k = ("medida", "", prop.lower())
                    if k in vistos:
                        continue
                    vistos.add(k)
                    uso_vis[k].append({"ref": ref, "agregado": agg})
                    if tipo == "coluna":
                        usados_col[chave(ent, prop)].add("visual")

    # ---------- papel das tabelas ----------
    lado_um, lado_n = defaultdict(int), defaultdict(int)
    for r in modelo["relacionamentos"]:
        um_de = (r["card_de"] == "one")
        um_para = (r["card_para"] == "one")
        if um_para and not um_de:
            lado_um[r["para_tabela"]] += 1
            lado_n[r["de_tabela"]] += 1
        elif um_de and not um_para:
            lado_um[r["de_tabela"]] += 1
            lado_n[r["para_tabela"]] += 1
        elif um_de and um_para:
            lado_um[r["de_tabela"]] += 1
            lado_um[r["para_tabela"]] += 1
        else:
            lado_n[r["de_tabela"]] += 1
            lado_n[r["para_tabela"]] += 1

    for tn, t in tabs.items():
        visiveis = [c for c in t["colunas"].values() if not c["oculta"]]
        calc_src = " ".join(p["fonte"] or "" for p in t["particoes"] if p["tipo"].lower() == "calculated")
        if AUTO_DATE_RE.match(tn):
            papel = "auto_data"
        elif t["calc_group"]:
            papel = "calc_group"
        elif (t["data_category"] or "").lower() == "time":
            papel = "calendario"
        elif "NAMEOF" in calc_src.upper():
            papel = "field_parameter"
        elif t["medidas"] and not visiveis and not lado_um[tn] and not lado_n[tn]:
            papel = "medidas"
        elif lado_um[tn]:
            papel = "dimensao"
        elif lado_n[tn]:
            papel = "fato"
        elif calc_src:
            papel = "auxiliar"
        else:
            papel = "desconectada"
        t["papel_inferido"] = papel

    # ---------- fontes M ----------
    nomes_expr = {e["nome"] for e in modelo["expressoes"]}
    fonte_re = re.compile(r"\b((?:[A-Z][A-Za-z]*\.)+(?:Database|Databases|Workbook|Files|Contents|Document|"
                          r"Tables|Query|Feed|Dataflows|Lakehouse|Warehouse|Folder))\s*\(")
    for tn, t in tabs.items():
        fontes, refs = set(), set()
        for p in t["particoes"]:
            if p["tipo"].lower() == "m" or (p["fonte"] and "let" in (p["fonte"] or "").lower()):
                src = p["fonte"] or ""
                fontes.update(fonte_re.findall(src))
                for ne in nomes_expr:
                    if re.search(r'(?<![\w"])' + re.escape(ne) + r'(?![\w"])', src) or f'#"{ne}"' in src:
                        refs.add(ne)
        t["fontes"] = sorted(fontes)
        t["usa_expressoes"] = sorted(refs)
        t["modo"] = sorted({p["modo"] for p in t["particoes"] if p.get("modo")})

    # =========================== CHECKS ===========================
    reais = {tn: t for tn, t in tabs.items() if t["papel_inferido"] != "auto_data"}
    todas_medidas_pre = [m for t in reais.values() for m in t["medidas"].values()]

    # datas
    calendarios = [tn for tn, t in reais.items() if t["papel_inferido"] == "calendario"]
    autos = [tn for tn in tabs if AUTO_DATE_RE.match(tn)]
    if not calendarios:
        cand = [tn for tn, t in reais.items()
                if re.search(r"calend|^d_?data|date|tempo|time", tn, re.I)
                and any((c["tipo"] or "").lower() == "datetime" for c in t["colunas"].values())]
        issue("model-no-date-table", cand,
              "Nenhuma tabela com dataCategory: Time." + (f" Candidatas: {', '.join(cand)}." if cand else ""))
    ligadas_ativas = set()
    for r in modelo["relacionamentos"]:
        if r["ativo"] and not AUTO_DATE_RE.match(r["de_tabela"] or "") and not AUTO_DATE_RE.match(r["para_tabela"] or ""):
            ligadas_ativas.update((r["de_tabela"], r["para_tabela"]))
    for tn in calendarios:
        if tn not in ligadas_ativas:
            inativos = [r for r in modelo["relacionamentos"] if tn in (r["de_tabela"], r["para_tabela"])]
            issue("model-date-table-disconnected", [tn],
                  f"{tn} está marcada como calendário mas não tem relacionamento ativo"
                  + (f" ({len(inativos)} inativo(s))" if inativos else "") +
                  ": filtros e time intelligence por ela não afetam as fatos.", tabs[tn]["arquivo"], tabs[tn]["linha"])
    if modelo["anotacoes"].get("__PBI_TimeIntelligenceEnabled") == "1" or autos:
        issue("perf-auto-date-time", autos,
              f"Auto Date/Time ligado; {len(autos)} tabela(s) LocalDateTable/DateTableTemplate no modelo.")
    for tn in calendarios or [tn for tn in reais if re.search(r"calend", tn, re.I)]:
        for cn, c in tabs[tn]["colunas"].items():
            if c.get("variacao") and AUTO_DATE_RE.match(str(c["variacao"]).strip("'")):
                issue("model-calendar-using-auto-hierarchy", [f"{tn}[{cn}]"],
                      f"{tn}[{cn}] tem variation apontando para {c['variacao']}.",
                      tabs[tn]["arquivo"], c["linha"])

    # relacionamentos (ignora os internos do Auto Date/Time)
    rels = [r for r in modelo["relacionamentos"]
            if not AUTO_DATE_RE.match(r["de_tabela"] or "") and not AUTO_DATE_RE.match(r["para_tabela"] or "")]
    for r in rels:
        desc = f"{r['de_tabela']}[{r['de_coluna']}] → {r['para_tabela']}[{r['para_coluna']}]"
        if r["direcao"] == "both":
            issue("rel-bidirectional-unnecessary", [desc],
                  f"{desc} ({r['card_de']}:{r['card_para']}, {'ativo' if r['ativo'] else 'inativo'}).",
                  r["arquivo"], r["linha"])
        if r["card_de"] == "many" and r["card_para"] == "many":
            issue("rel-many-to-many-without-bridge", [desc], f"{desc} declarado muitos-para-muitos.",
                  r["arquivo"], r["linha"])
        if r["card_de"] == "one" and r["card_para"] == "one":
            issue("rel-one-to-one-suspicious", [desc], f"{desc} é 1:1.", r["arquivo"], r["linha"])
    usados_pares = set(pares_userel)
    for r in rels:
        if not r["ativo"]:
            par = frozenset({chave(r["de_tabela"], r["de_coluna"]), chave(r["para_tabela"], r["para_coluna"])})
            r["usado_por_userelationship"] = par in usados_pares
            if par not in usados_pares:
                desc = f"{r['de_tabela']}[{r['de_coluna']}] → {r['para_tabela']}[{r['para_coluna']}]"
                issue("rel-inactive-orphan", [desc], f"Inativo e nenhuma expressão usa USERELATIONSHIP nele: {desc}.",
                      r["arquivo"], r["linha"])

    # snowflake: dimensão no lado "1" de um relacionamento e no lado "N" de outro (ativos)
    filtra = defaultdict(set)   # quem -> filtra quem (direção natural 1 -> N)
    for r in rels:
        if not r["ativo"]:
            continue
        if r["card_para"] == "one" and r["card_de"] == "many":
            filtra[r["para_tabela"]].add(r["de_tabela"])
        elif r["card_de"] == "one" and r["card_para"] == "many":
            filtra[r["de_tabela"]].add(r["para_tabela"])
    for dim, filhos in filtra.items():
        for filho in filhos:
            if reais.get(filho, {}).get("papel_inferido") == "dimensao" and filtra.get(filho):
                cadeia = f"{dim} → {filho} → {', '.join(sorted(filtra[filho]))}"
                issue("rel-snowflake-suspicious", [dim, filho], f"Cadeia de filtro: {cadeia}.")

    # caminhos ambíguos (grafo de propagação de filtro, relacionamentos ativos)
    arestas = defaultdict(list)   # origem -> [(destino, rel_id)]
    for r in rels:
        if not r["ativo"]:
            continue
        a, b = r["para_tabela"], r["de_tabela"]   # padrão: lado "para" (1) filtra lado "de" (N)
        if r["card_de"] == "one" and r["card_para"] == "many":
            a, b = b, a
        arestas[a].append((b, r["id"]))
        if r["direcao"] == "both" or (r["card_de"] == "one" and r["card_para"] == "one"):
            arestas[b].append((a, r["id"]))
    ambiguos, orcamento = {}, [200000]

    def dfs(orig, atual, usados, visit, caminho):
        if orcamento[0] <= 0 or len(caminho) > 6:
            return
        for dest, rid in arestas.get(atual, ()):
            if rid in usados or dest in visit:
                continue
            orcamento[0] -= 1
            novo = caminho + [dest]
            ambiguos.setdefault((orig, dest), set()).add(" → ".join(novo))
            dfs(orig, dest, usados | {rid}, visit | {dest}, novo)

    for orig in list(arestas):
        dfs(orig, orig, frozenset(), {orig}, [orig])
    pares_amb = [(o, d, sorted(cs)) for (o, d), cs in sorted(ambiguos.items()) if len(cs) > 1]
    if pares_amb:
        bidi = sorted({f"{r['de_tabela']} ↔ {r['para_tabela']}" for r in rels if r["ativo"] and r["direcao"] == "both"})
        exemplos = [f"{o} → {d}: " + " | ".join(cs[:3]) for o, d, cs in pares_amb[:3]]
        issue("model-circular-reference", sorted({x for o, d, _ in pares_amb for x in (o, d)}),
              f"{len(pares_amb)} par(es) de tabelas com mais de um caminho de filtro ativo. "
              + (f"Bidirecionais envolvidos: {', '.join(bidi)}. " if bidi else "") + "Ex.: " + " ; ".join(exemplos))

    # RLS (propagação do filtro de segurança: lado 1 -> lado N; ambos os sentidos só com securityFilteringBehavior)
    arestas_seg = defaultdict(set)
    for r in rels:
        if not r["ativo"]:
            continue
        a, b = r["para_tabela"], r["de_tabela"]
        if r["card_de"] == "one" and r["card_para"] == "many":
            a, b = b, a
        arestas_seg[a].add(b)
        if r.get("seguranca_both") or (r["card_de"] == "one" and r["card_para"] == "one"):
            arestas_seg[b].add(a)
    fatos = {tn for tn, t in reais.items() if t["papel_inferido"] == "fato"}
    for ro in modelo["roles"]:
        if not ro["permissoes"]:
            if len(modelo["roles"]) > 1:
                issue("rls-role-without-filter", [ro["nome"]],
                      f"Role {ro['nome']} não filtra nenhuma tabela: quem estiver nela vê tudo.", ro["arquivo"], ro["linha"])
            continue
        for pe in ro["permissoes"]:
            tab = pe["tabela"]
            if not (pe["expressao"] or "").strip() or (pe["expressao"] or "").strip().upper() == "TRUE()":
                continue
            if tab in fatos:
                issue("rls-on-fact-table", [f"{ro['nome']} / {tab}"],
                      f"Role {ro['nome']} filtra a fato {tab} direto; filtrar a dimensão é mais leve e mais fácil de manter.",
                      ro["arquivo"], ro["linha"])
                continue
            alcance, fila = set(), [tab]
            while fila:
                x = fila.pop()
                for y in arestas_seg.get(x, ()):
                    if y not in alcance:
                        alcance.add(y)
                        fila.append(y)
            if fatos and not (alcance & fatos):
                issue("rls-filter-not-propagating", [f"{ro['nome']} / {tab}"],
                      f"Role {ro['nome']} filtra {tab}, mas esse filtro não chega em nenhuma fato "
                      f"({', '.join(sorted(fatos))}) pelos relacionamentos ativos: a role não restringe os números.",
                      ro["arquivo"], ro["linha"])
            pe["alcanca"] = sorted(alcance)
        ro["dinamica"] = any(re.search(r"\b(USERPRINCIPALNAME|USERNAME|CUSTOMDATA|USEROBJECTID)\s*\(", pe["expressao"] or "", re.I)
                             for pe in ro["permissoes"])

    # string como chave
    chaves_txt = []
    for r in rels:
        for t_, c_ in ((r["de_tabela"], r["de_coluna"]), (r["para_tabela"], r["para_coluna"])):
            col = tabs.get(t_, {}).get("colunas", {}).get(c_)
            if col and (col["tipo"] or "").lower() == "string":
                chaves_txt.append(f"{t_}[{c_}]")
    if chaves_txt:
        issue("perf-string-as-key", sorted(set(chaves_txt)),
              f"{len(set(chaves_txt))} coluna(s) texto usadas em relacionamento. Confirmar cardinalidade (MCP).")

    # DAX por medida
    for tn, t in reais.items():
        exprs = [("medida", mn, m["expressao"], m["linha"]) for mn, m in t["medidas"].items()]
        exprs += [("coluna", f"{tn}[{cn}]", c["expressao"], c["linha"]) for cn, c in t["colunas"].items() if c["calculada"]]
        exprs += [("calc_item", f"{tn}.{it['nome']}", it["expressao"], it["linha"]) for it in t["calc_items"]]
        for tipo, nome, expr, linha in exprs:
            if not expr:
                continue
            limpo = limpar_dax(expr)
            masc = mascarar(limpo)
            rotulo = f"[{nome}]" if tipo == "medida" else nome
            # divisão
            for m in re.finditer(r"/", masc):
                depois = masc[m.end():].lstrip()
                if re.match(r"\d+(\.\d+)?\b", depois) and float(re.match(r"\d+(\.\d+)?", depois).group(0)) != 0:
                    continue
                issue("dax-divide-operator", [rotulo], f"{rotulo} usa '/' com denominador não constante.", t["arquivo"], linha)
                break
            # referências qualificadas/não qualificadas (BPA DAX_COLUMNS_FULLY_QUALIFIED / DAX_MEASURES_UNQUALIFIED)
            for mr in REF_RE.finditer(limpo):
                tab_ = (mr.group(1) or "").replace("''", "'") or mr.group(2)
                nome_ = mr.group(3).replace("]]", "]")
                if tab_ and nome_.lower() in idx.medidas and chave(tab_, nome_) not in idx.colunas:
                    issue("dax-qualified-measure-ref", [rotulo], f"{rotulo} referencia a medida {tab_}[{nome_}] com tabela.", t["arquivo"], linha)
                    break
            if tipo == "medida":
                for mr in REF_RE.finditer(limpo):
                    if not (mr.group(1) or mr.group(2)):
                        nome_ = mr.group(3).replace("]]", "]")
                        if nome_.lower() not in idx.medidas and idx.col_por_nome.get(nome_.lower()) \
                                and not re.search(r'"' + re.escape(nome_) + r'"', expr):
                            issue("dax-unqualified-column-ref", [rotulo], f"{rotulo} usa a coluna [{nome_}] sem tabela.", t["arquivo"], linha)
                            break
            if re.search(r"\bINTERSECT\s*\(", masc, re.I):
                issue("dax-intersect", [rotulo], f"{rotulo} usa INTERSECT; para relacionamento virtual prefira TREATAS.", t["arquivo"], linha)
            if re.search(r"\bEVALUATEANDLOG\s*\(", masc, re.I):
                issue("dax-evaluateandlog", [rotulo], f"{rotulo} usa EVALUATEANDLOG (só para depuração).", t["arquivo"], linha)
            if tipo == "medida" and re.fullmatch(r"\s*\[[^\]]+\]\s*", limpo):
                issue("dax-measure-is-reference", [rotulo], f"{rotulo} = {limpo.strip()} (só repete outra medida).", t["arquivo"], linha)
            if tipo == "coluna" and re.search(r"\bRELATED\s*\(", masc, re.I):
                issue("perf-calc-column-related", [rotulo], f"{rotulo} usa RELATED; trazer o atributo na origem (Power Query/SQL) é mais leve.", t["arquivo"], linha)
            # iferror
            if re.search(r"\b(IFERROR|ISERROR)\s*\(", masc, re.I):
                issue("dax-iferror", [rotulo], f"{rotulo} usa IFERROR/ISERROR.", t["arquivo"], linha)
            # variáveis não usadas
            for m in re.finditer(r"\bVAR\s+([^\W\d]\w*)\s*=", masc, re.I | re.U):
                nv = m.group(1)
                if len(re.findall(r"(?<!\w)" + re.escape(nv) + r"(?!\w)", masc, re.I)) <= 1:
                    issue("dax-unused-variables", [rotulo], f"{rotulo}: VAR {nv} não é usada.", t["arquivo"], linha)
            # CALCULATE aninhado e FILTER em tabela inteira
            calcs = chamadas(masc, "CALCULATE")
            iters = [s for f in ITERADORES for s in chamadas(masc, f)]
            aninhado = False
            for ini, abre, fecha in calcs:
                for ini2, abre2, fecha2 in calcs:
                    if abre < ini2 < fecha:
                        legit = any(abre < a2 < ini2 < f2 <= fecha for _, a2, f2 in iters)
                        if not legit:
                            aninhado = True
            if aninhado:
                issue("dax-nested-calculate", [rotulo], f"{rotulo} tem CALCULATE dentro de CALCULATE.", t["arquivo"], linha)
            for f in ("CALCULATE", "CALCULATETABLE"):
                achou = False
                for ini, abre, fecha in chamadas(masc, f):
                    for a, b in args_topo(masc, abre, fecha)[1:]:
                        trecho = limpo[a:b].strip()
                        mf = re.match(r"FILTER\s*\(\s*('((?:[^']|'')+)'|[^\W\d]\w*)\s*,", trecho, re.I | re.U)
                        if mf:
                            tab = (mf.group(2) or mf.group(1)).replace("''", "'")
                            if tab.lower() in idx.tabelas:
                                issue("dax-filter-whole-table", [rotulo],
                                      f"{rotulo}: FILTER({tab}, ...) dentro de {f}.", t["arquivo"], linha)
                                achou = True
                                break
                    if achou:
                        break

    # ---------- regras adicionais alinhadas ao BPA oficial da Microsoft ----------
    # tipos diferentes nas pontas do relacionamento
    for r in rels:
        ca = tabs.get(r["de_tabela"], {}).get("colunas", {}).get(r["de_coluna"])
        cb = tabs.get(r["para_tabela"], {}).get("colunas", {}).get(r["para_coluna"])
        if ca and cb and ca["tipo"] and cb["tipo"] and ca["tipo"].lower() != cb["tipo"].lower():
            desc = f"{r['de_tabela']}[{r['de_coluna']}] ({ca['tipo']}) → {r['para_tabela']}[{r['para_coluna']}] ({cb['tipo']})"
            issue("rel-columns-different-types", [desc], desc, r["arquivo"], r["linha"])
    # USERELATIONSHIP contra tabela com RLS
    tabs_rls = {(pe["tabela"] or "").lower() for ro in modelo["roles"] for pe in ro["permissoes"]}
    tabs_userel = {t_ for par in pares_userel for (t_, _) in par}
    conflito = sorted(idx.tabelas.get(x, x) for x in tabs_rls & tabs_userel)
    if conflito:
        issue("rls-and-userelationship-same-table", conflito,
              f"Tabela(s) filtradas por RLS e usadas em USERELATIONSHIP: {', '.join(conflito)}. O motor rejeita a consulta para quem está na role.")
    # ponto flutuante, chaves visíveis, soma automática, mês sem ordenação
    flutuantes, fks, somam, meses = [], [], [], []
    chaves_n = {chave(r["de_tabela"], r["de_coluna"]) for r in rels if r["card_de"] == "many"} | \
               {chave(r["para_tabela"], r["para_coluna"]) for r in rels if r["card_para"] == "many"}
    em_rel = {chave(r["de_tabela"], r["de_coluna"]) for r in rels} | {chave(r["para_tabela"], r["para_coluna"]) for r in rels}
    for tn, t in reais.items():
        if t["papel_inferido"] in ("medidas", "field_parameter", "calc_group"):
            continue
        for cn, c in t["colunas"].items():
            tipo_c = (c["tipo"] or "").lower()
            if tipo_c == "double":
                flutuantes.append(f"{tn}[{cn}]")
            if chave(tn, cn) in chaves_n and not c["oculta"] and t["papel_inferido"] == "fato":
                fks.append(f"{tn}[{cn}]")
            if (tipo_c in NUMERICOS and not c["oculta"] and chave(tn, cn) not in em_rel
                    and (c.get("summarize_by") or "default").lower() != "none"):
                somam.append(f"{tn}[{cn}]")
            if tipo_c == "string" and re.search(r"\b(m[eê]s|month)\b", cn, re.I) and not c.get("sort_by") \
                    and not re.search(r"ano|year|num|n[ºo]", cn, re.I):
                meses.append(f"{tn}[{cn}]")
    if flutuantes:
        issue("perf-floating-point", flutuantes,
              f"{len(flutuantes)} coluna(s) double. Para valores monetários use decimal fixo (Decimal Fixo/Moeda): evita erro de arredondamento e comprime melhor.")
    if fks:
        issue("fmt-hide-foreign-keys", fks, f"{len(fks)} chave(s) estrangeira(s) visíveis na fato; ocultar para o usuário filtrar pela dimensão.")
    if somam:
        issue("fmt-numeric-summarize", somam,
              f"{len(somam)} coluna(s) numérica(s) visíveis com soma automática; prefira medidas explícitas e summarizeBy: none.")
    if meses:
        issue("fmt-month-not-sorted", meses, f"Coluna(s) de mês em texto sem 'Classificar por coluna': {', '.join(meses[:10])} (ordem alfabética).")
    # medidas duplicadas
    por_expr = defaultdict(list)
    for m in todas_medidas_pre:
        e = re.sub(r"\s+", "", limpar_dax(m["expressao"])).lower()
        if e:
            por_expr[e].append(f"[{m['nome']}]")
    dups = [g for g in por_expr.values() if len(g) > 1]
    if dups:
        issue("dax-duplicate-measures", [x for g in dups for x in g],
              "Mesma expressão em: " + " | ".join(" = ".join(g) for g in dups[:10]))
    # nomes com espaço nas pontas
    nomes_esp = [tn for tn in reais if tn != tn.strip()] + \
                [f"{tn}[{n}]" for tn, t in reais.items() for n in list(t["colunas"]) + list(t["medidas"]) if n != n.strip()]
    if nomes_esp:
        issue("naming-leading-trailing-space", nomes_esp, f"{len(nomes_esp)} nome(s) com espaço no início ou no fim.")
    # tabelas sem relacionamento
    sem_rel = [tn for tn, t in reais.items() if t["papel_inferido"] == "desconectada"]
    if sem_rel:
        issue("model-table-without-relationship", sem_rel,
              f"{len(sem_rel)} tabela(s) sem relacionamento e sem papel de medidas/parâmetro: {', '.join(sem_rel[:10])}.")
    # DirectQuery + time intelligence
    dq = [tn for tn, t in reais.items() if any((m or "").lower() == "directquery" for m in t.get("modo", []))]
    if dq:
        ti = [f"[{m['nome']}]" for m in todas_medidas_pre if re.search(
            r"\b(SAMEPERIODLASTYEAR|DATEADD|DATESYTD|DATESMTD|DATESQTD|TOTALYTD|TOTALMTD|TOTALQTD|PARALLELPERIOD|DATESINPERIOD)\s*\(",
            mascarar(limpar_dax(m["expressao"])), re.I)]
        if ti:
            issue("perf-directquery-time-intelligence", ti,
                  f"Modelo com DirectQuery ({', '.join(dq[:5])}) e {len(ti)} medida(s) de time intelligence: geram SQL pesado na origem.")

    # coluna calculada que poderia ser medida
    for tn, t in reais.items():
        if t["papel_inferido"] != "fato":
            continue
        for cn, c in t["colunas"].items():
            if not c["calculada"] or (c["tipo"] or "").lower() not in NUMERICOS:
                continue
            masc = mascarar(limpar_dax(c["expressao"] or ""))
            if FUNCS_AGREGACAO.search(masc) or re.search(r"\bRELATED\s*\(", masc, re.I):
                continue
            ms, cs = c.get("_deps", (set(), set()))
            if ms or any(a.lower() != tn.lower() for a, _ in cs):
                continue
            origens = usados_col.get(chave(tn, cn), set())
            uso_direto = any(not u["agregado"] for u in uso_vis.get(("coluna", tn.lower(), cn.lower()), []))
            if uso_direto or any(o.startswith(("relacionamento", "ordenacao", "hierarquia")) for o in origens):
                continue
            issue("perf-calc-column-should-be-measure", [f"{tn}[{cn}]"],
                  f"{tn}[{cn}] = {(c['expressao'] or '').strip()[:120]}", t["arquivo"], c["linha"])

    # nomenclatura de medidas
    todas_medidas = [m for t in reais.values() for m in t["medidas"].values()]
    classes = Counter(filter(None, (classe_nome(m["nome"]) for m in todas_medidas)))
    total_cls = sum(classes.values())
    dominante, share = (None, 0)
    if total_cls:
        dominante, qtd = classes.most_common(1)[0]
        share = qtd / total_cls
        if total_cls >= 5 and share < 0.7:
            issue("naming-mixed-conventions", [],
                  "Distribuição: " + ", ".join(f"{k} {v}" for k, v in classes.most_common()) +
                  f". Dominante {dominante} com {share:.0%}.")
    curtas = [f"[{m['nome']}]" for m in todas_medidas
              if not m["descricao"] and (len(m["nome"].strip()) <= 4 or re.fullmatch(r"[A-Z]{2,6}\d*", m["nome"].strip()))]
    if curtas:
        issue("naming-acronym-no-context", curtas, f"{len(curtas)} medida(s): {', '.join(curtas[:15])}")

    # prefixo de tabelas
    fd = [tn for tn, t in reais.items() if t["papel_inferido"] in ("fato", "dimensao", "calendario")]
    prefixos = Counter(filter(None, (prefixo_tabela(tn) for tn in reais)))
    com_prefixo = [tn for tn in fd if (prefixo_tabela(tn) or "").rstrip("_ ") in PREFIXOS_PAPEL]
    if len(fd) >= 2 and len(com_prefixo) / len(fd) < 0.5:
        sem = [tn for tn in fd if tn not in com_prefixo]
        issue("naming-no-table-prefix", sem, f"{len(sem)} de {len(fd)} tabelas fato/dimensão sem prefixo de papel.")

    # documentação e metadados
    sem_desc = [f"[{m['nome']}]" for m in todas_medidas if not m["descricao"]]
    if sem_desc:
        issue("doc-measures-no-description", sem_desc, f"{len(sem_desc)} de {len(todas_medidas)} medidas sem descrição.")
    tabs_doc = [tn for tn, t in reais.items() if t["papel_inferido"] not in ("field_parameter",)]
    sem_desc_t = [tn for tn in tabs_doc if not reais[tn]["descricao"]]
    if sem_desc_t:
        issue("doc-tables-no-description", sem_desc_t, f"{len(sem_desc_t)} de {len(tabs_doc)} tabelas sem descrição.")
    sem_fmt = [f"[{m['nome']}]" for m in todas_medidas if not m["formato"] and not m["formato_dinamico"]]
    if sem_fmt:
        issue("measure-no-format-string", sem_fmt, f"{len(sem_fmt)} medida(s) sem formatString.")
    dims_sem_chave = [tn for tn, t in reais.items() if t["papel_inferido"] == "dimensao"
                      and not any(c["chave"] for c in t["colunas"].values())]
    if dims_sem_chave:
        issue("doc-no-business-key-marked", dims_sem_chave, f"{len(dims_sem_chave)} dimensão(ões) sem isKey.")

    # caminho pessoal
    for tn, t in tabs.items():
        for p in t["particoes"]:
            src = (p["fonte"] or "").lower()
            achados = [x for x in PATH_PESSOAL if x in src]
            if achados:
                issue("data-source-personal-path", [tn], f"Partição de {tn} contém: {', '.join(achados)}.",
                      t["arquivo"], p["linha"])
    for e in modelo["expressoes"]:
        src = (e["expressao"] or "").lower()
        achados = [x for x in PATH_PESSOAL if x in src]
        if achados:
            if re.search(r"IsParameterQuery\s*=\s*true", e["expressao"] or "", re.I):
                issue("data-source-personal-path", [e["nome"]],
                      f"Parâmetro {e['nome']} tem valor padrão com caminho pessoal ({', '.join(achados)}). "
                      "Já está parametrizado: basta trocar o valor ao entregar o projeto para outra pessoa.",
                      e["arquivo"], e["linha"], severidade="light")
            else:
                issue("data-source-personal-path", [e["nome"]], f"Expressão {e['nome']} contém: {', '.join(achados)}.",
                      e["arquivo"], e["linha"])

    # sem uso (só com relatório)
    if tem_relatorio:
        nao_usadas = []
        for tn, t in reais.items():
            if t["papel_inferido"] in ("field_parameter", "calc_group", "medidas"):
                continue
            for cn, c in t["colunas"].items():
                if c.get("tipo_coluna") == "rowNumber":
                    continue
                if not usados_col.get(chave(tn, cn)):
                    nao_usadas.append(f"{tn}[{cn}]")
        if nao_usadas:
            issue("perf-unused-columns", nao_usadas,
                  f"{len(nao_usadas)} coluna(s) sem uso em medida, relacionamento, RLS, hierarquia, ordenação ou visual.")
        med_nao_usadas = [f"[{m['nome']}]" for m in todas_medidas
                          if not medida_usada_por.get(m["nome"]) and not medida_usada_extra.get(m["nome"])
                          and not uso_vis.get(("medida", "", m["nome"].lower()))]
        if med_nao_usadas:
            issue("measure-unused", med_nao_usadas, f"{len(med_nao_usadas)} medida(s) sem uso em visual nem em outra expressão.")
    else:
        avisos.append("Nenhum relatório encontrado na pasta: checks de colunas/medidas sem uso e mapa de visuais desativados.")

    if soltas_total:
        avisos.append("Referências DAX não resolvidas (VAR de tabela, coluna de tabela virtual ou objeto inexistente): "
                      + ", ".join(f"{k}" for k, _ in soltas_total.most_common(20)))

    # =========================== MONTAGEM ===========================
    def vis_de_medida(nome):
        return [u["ref"] for u in uso_vis.get(("medida", "", nome.lower()), [])]

    medidas_out = []
    for tn, t in tabs.items():
        for mn, m in t["medidas"].items():
            ms, cs = dep_medida[mn]
            imp = fechamento([mn])
            imp_vis = set(vis_de_medida(mn))
            for x in imp:
                imp_vis.update(vis_de_medida(x))
            medidas_out.append({
                "nome": mn, "tabela": tn, "pasta": m["pasta"], "formato": m["formato"],
                "descricao": m["descricao"], "oculta": m["oculta"], "arquivo": m["arquivo"], "linha": m["linha"],
                "expressao": m["expressao"],
                "depende_de": {"medidas": sorted(ms), "colunas": sorted(f"{a}[{b}]" for a, b in cs)},
                "usada_por_medidas": sorted(medida_usada_por.get(mn, ())),
                "usada_por_outros": sorted(medida_usada_extra.get(mn, ())),
                "impacto_medidas": sorted(imp),
                "visuais": vis_de_medida(mn), "impacto_visuais": sorted(imp_vis)})

    med_por_col = defaultdict(set)
    for mn, (ms, cs) in dep_medida.items():
        for c in cs:
            med_por_col[chave(*c)].add(mn)

    tabelas_out = []
    for tn, t in tabs.items():
        cols = []
        for cn, c in t["colunas"].items():
            k = chave(tn, cn)
            diretas = med_por_col.get(k, set())
            imp = set(diretas) | fechamento(diretas)
            vis = [u["ref"] for u in uso_vis.get(("coluna", tn.lower(), cn.lower()), [])]
            imp_vis = set(vis)
            for x in imp:
                imp_vis.update(vis_de_medida(x))
            origens = usados_col.get(k, set())
            cols.append({
                "nome": cn, "tipo": c["tipo"], "oculta": c["oculta"], "chave": c["chave"],
                "calculada": c["calculada"], "expressao": c["expressao"], "sort_by": c["sort_by"],
                "linha": c["linha"], "descricao": c["descricao"],
                "usada_por_medidas": sorted(diretas), "impacto_medidas": sorted(imp),
                "usada_em": sorted(o for o in origens if not o.startswith("medida:") and o != "visual"),
                "visuais": vis, "impacto_visuais": sorted(imp_vis)})
        tabelas_out.append({
            "nome": tn, "papel_inferido": t["papel_inferido"], "arquivo": t["arquivo"], "linha": t["linha"],
            "oculta": t["oculta"], "descricao": t["descricao"], "data_category": t["data_category"],
            "modo": t["modo"], "fontes": t["fontes"], "usa_expressoes": t["usa_expressoes"],
            "qtd_colunas": len(t["colunas"]), "qtd_medidas": len(t["medidas"]),
            "colunas": cols, "hierarquias": t["hierarquias"],
            "calc_items": [i["nome"] for i in t["calc_items"]]})

    # convenções detectadas
    pastas = Counter(m["pasta"] for m in todas_medidas if m["pasta"])
    formatos = Counter(m["formato"] for m in todas_medidas if m["formato"])
    host = Counter(m["tabela"] for m in todas_medidas)
    tabs_medidas = [tn for tn, t in reais.items() if t["papel_inferido"] == "medidas"]
    convencoes = {
        "medidas": {"padrao_dominante": dominante if share >= 0.7 else None,
                    "distribuicao": dict(classes.most_common()),
                    "participacao_dominante": round(share, 2)},
        "tabelas": {"prefixos": dict(prefixos.most_common(10)),
                    "fato_dimensao_com_prefixo": f"{len(com_prefixo)}/{len(fd)}"},
        "tabela_de_medidas": (sorted(tabs_medidas, key=lambda x: -host[x]) or [None])[0],
        "medidas_por_tabela": dict(host.most_common(10)),
        "display_folders": dict(pastas.most_common(30)),
        "format_strings": dict(formatos.most_common(10)),
        "auto_date_time": bool(autos) or modelo["anotacoes"].get("__PBI_TimeIntelligenceEnabled") == "1",
        "tabelas_calendario": calendarios,
    }

    issues.sort(key=lambda x: (ORDEM_SEV[x["severidade"]], x["familia"], x["id"]))
    paginas = sum(len(r["paginas"]) for r in relatorios)
    resumo = {
        "tabelas": len(reais), "tabelas_auto_data": len(autos),
        "colunas": sum(len(t["colunas"]) for t in reais.values()),
        "colunas_calculadas": sum(1 for t in reais.values() for c in t["colunas"].values() if c["calculada"]),
        "medidas": len(todas_medidas), "relacionamentos": len(rels),
        "relacionamentos_inativos": sum(1 for r in rels if not r["ativo"]),
        "roles": len(modelo["roles"]), "paginas": paginas, "visuais": total_vis,
        "issues": dict(Counter(i["severidade"] for i in issues)),
    }
    for r in rels:
        r.setdefault("usado_por_userelationship", None)
    rel_out = [{"dir": r["dir"], "formato": r["formato"], "modelo_ref": r["modelo_ref"],
                "paginas": [{"nome": p["nome"], "visuais": [
                    {"id": v["id"], "tipo": v["tipo"], "titulo": v["titulo"],
                     "campos": sorted({f"{c[1]}[{c[2]}]" if c[0] != "nivel" else f"{c[1]}.{c[2]}" for c in v["campos"]})}
                    for v in p["visuais"]]} for p in r["paginas"]]} for r in relatorios]
    return {
        "resumo": resumo, "convencoes_detectadas": convencoes, "tabelas": tabelas_out,
        "medidas": medidas_out, "relacionamentos": rels, "roles": modelo["roles"],
        "expressoes": modelo["expressoes"], "funcoes": [f["nome"] for f in modelo["funcoes"]],
        "relatorios": rel_out, "issues": issues, "avisos": avisos + modelo.get("erros", []),
    }


# =============================================================================
# Saída
# =============================================================================

SEV_PT = {"critical": "Crítico", "medium": "Médio", "light": "Leve"}


def resumo_md(inv):
    r, c, p = inv["resumo"], inv["convencoes_detectadas"], inv["projeto"]
    L = [f"# Inventário · {p['modelo']}", "",
         f"Gerado em {inv['gerado_em']} · formato {p['formato_modelo']} · "
         "relatórios: " + (", ".join("%s (%s)" % (x["dir"], x["formato"]) for x in inv["relatorios"]) or "nenhum"), "",
         "## Números", "",
         f"- {r['tabelas']} tabelas · {r['colunas']} colunas ({r['colunas_calculadas']} calculadas) · {r['medidas']} medidas",
         f"- {r['relacionamentos']} relacionamentos ({r['relacionamentos_inativos']} inativos) · {r['roles']} roles RLS",
         f"- {r['paginas']} páginas · {r['visuais']} visuais", "",
         "## Papel das tabelas", ""]
    por_papel = defaultdict(list)
    for t in inv["tabelas"]:
        if t["papel_inferido"] != "auto_data":
            por_papel[t["papel_inferido"]].append(t["nome"])
    for papel in ("fato", "dimensao", "calendario", "medidas", "field_parameter", "calc_group", "auxiliar", "desconectada"):
        if por_papel.get(papel):
            L.append(f"- **{papel}**: {', '.join(sorted(por_papel[papel]))}")
    L += ["", "## Convenções detectadas", "",
          f"- Nomes de medidas: {c['medidas']['padrao_dominante'] or 'sem padrão dominante'} "
          f"({', '.join(f'{k} {v}' for k, v in c['medidas']['distribuicao'].items()) or '—'})",
          f"- Tabela de medidas: {c['tabela_de_medidas'] or '—'}",
          f"- Prefixos de tabela: {', '.join(c['tabelas']['prefixos']) or '—'} "
          f"(fato/dimensão com prefixo: {c['tabelas']['fato_dimensao_com_prefixo']})",
          f"- Pastas de medidas: {', '.join(list(c['display_folders'])[:8]) or '—'}",
          f"- Formatos mais usados: {' | '.join(list(c['format_strings'])[:5]) or '—'}",
          f"- Auto Date/Time: {'ligado' if c['auto_date_time'] else 'desligado'} · "
          f"Calendário: {', '.join(c['tabelas_calendario']) or 'nenhum marcado'}", "",
          "## Checks mecânicos", ""]
    if not inv["issues"]:
        L.append("Nenhum issue detectado pelo script.")
    for i in inv["issues"]:
        rev = " · *revisar*" if i["detector"] == "script+revisar" else ""
        L.append(f"- **{SEV_PT[i['severidade']]}** · {i['titulo']} (`{i['id']}`){rev} — {i['detalhe']}")
    if inv["avisos"]:
        L += ["", "## Avisos", ""] + [f"- {a}" for a in inv["avisos"]]
    return "\n".join(L) + "\n"


def achar_modelos(caminho):
    caminho = caminho.resolve()
    if caminho.name.endswith(".SemanticModel"):
        return caminho.parent, [caminho]
    ignorar = {"_pbi", "_docs", "_review", "_testes", ".git", "node_modules"}
    modelos = [p for p in caminho.rglob("*.SemanticModel") if p.is_dir()
               and not any(part in ignorar for part in p.relative_to(caminho).parts)]
    return caminho, sorted(modelos)


class ErroProjeto(Exception):
    pass


def construir(caminho, modelo_nome=None):
    """Gera o inventário em memória. Devolve (inv, raiz). Levanta ErroProjeto com mensagem amigável."""
    raiz, modelos = achar_modelos(Path(caminho))
    if not modelos:
        msg = "Nenhuma pasta .SemanticModel encontrada."
        if list(raiz.rglob("*.pbix")):
            msg += " Há .pbix na pasta: salve como Projeto do Power BI (Arquivo → Salvar como → .pbip)."
        raise ErroProjeto(msg)
    if len(modelos) > 1:
        if not modelo_nome:
            raise ErroProjeto("Mais de um modelo encontrado; use --modelo:\n  " + "\n  ".join(m.name for m in modelos))
        modelos = [m for m in modelos if m.name.lower().startswith(modelo_nome.lower())]
        if not modelos:
            raise ErroProjeto(f"Modelo '{modelo_nome}' não encontrado.")
    mdir = modelos[0]
    if (mdir / "definition").is_dir():
        modelo = carregar_tmdl(mdir / "definition", raiz)
    elif (mdir / "model.bim").is_file():
        modelo = carregar_bim(mdir / "model.bim", raiz)
    else:
        raise ErroProjeto(f"{mdir.name} não tem definition/ (TMDL) nem model.bim.")

    relatorios = []
    for rdir in sorted(p for p in raiz.rglob("*.Report") if p.is_dir()):
        if any(part in ("_pbi", ".git") for part in rdir.relative_to(raiz).parts):
            continue
        rel = carregar_relatorio(rdir, raiz)
        alvo = (rel["modelo_ref"] or "").replace("\\", "/").rstrip("/").split("/")[-1]
        if not alvo or alvo.lower() == mdir.name.lower():
            relatorios.append(rel)

    inv = {"versao": VERSAO, "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "projeto": {"raiz": str(raiz), "modelo": mdir.name, "formato_modelo": modelo["formato"]}}
    inv.update(analisar(modelo, relatorios, raiz))
    ag = aviso_gitignore(raiz)
    if ag:
        inv["avisos"].insert(0, ag)
    return inv, raiz


MAX_HISTORICO = 10


def aviso_gitignore(raiz):
    """Se o projeto está num repositório git e _pbi/ ou _testes/ não são ignorados, devolve um aviso."""
    raiz = Path(raiz).resolve()
    if not any((d / ".git").exists() for d in [raiz, *raiz.parents]):
        return None
    faltam = []
    for pasta in ("_pbi", "_testes"):
        ignorado = None
        try:
            import subprocess
            r = subprocess.run(["git", "-C", str(raiz), "check-ignore", "-q", f"{pasta}/x.json"], capture_output=True)
            ignorado = r.returncode == 0 if r.returncode in (0, 1) else None
        except Exception:
            ignorado = None
        if ignorado is None:  # sem git disponível: olha o texto dos .gitignore
            textos = "".join((d / ".gitignore").read_text(encoding="utf-8", errors="ignore")
                             for d in [raiz, *raiz.parents] if (d / ".gitignore").is_file())
            ignorado = bool(re.search(r"(^|/)" + pasta + r"/?\s*$", textos, re.M))
        if not ignorado:
            faltam.append(pasta + "/")
    if faltam:
        return ("Projeto em repositório git e o .gitignore não exclui " + ", ".join(faltam) +
                ": essas pastas têm DAX/M e resultados de consultas e não devem ser versionadas (ver core/seguranca.md).")
    return None


def gravar(inv, saida):
    """Grava inventário e resumo; guarda o inventário anterior em historico/ (últimos 10)."""
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    atual = saida / "inventario.json"
    if atual.is_file():
        try:
            antigo = json.loads(atual.read_text(encoding="utf-8"))
            carimbo = re.sub(r"[^0-9]", "", antigo.get("gerado_em", "")) or datetime.now().strftime("%Y%m%d%H%M")
            hist = saida / "historico"
            hist.mkdir(exist_ok=True)
            (hist / f"inventario-{carimbo}.json").write_text(atual.read_text(encoding="utf-8"), encoding="utf-8")
            arquivos = sorted(hist.glob("inventario-*.json"))
            for velho in arquivos[:-MAX_HISTORICO]:
                try:
                    velho.unlink()
                except OSError:
                    pass
        except Exception:
            pass
    atual.write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
    (saida / "inventario-resumo.md").write_text(resumo_md(inv), encoding="utf-8")
    return atual


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Inventário determinístico de projeto Power BI (PBIP).")
    ap.add_argument("caminho", help="Pasta do projeto PBIP ou pasta .SemanticModel")
    ap.add_argument("--saida", help="Pasta de saída (padrão: <raiz>/_pbi)")
    ap.add_argument("--modelo", help="Nome do .SemanticModel quando há mais de um")
    a = ap.parse_args(argv)
    try:
        inv, raiz = construir(a.caminho, a.modelo)
    except ErroProjeto as e:
        print(str(e), file=sys.stderr)
        return 2
    destino = gravar(inv, Path(a.saida) if a.saida else raiz / "_pbi")
    r = inv["resumo"]
    sev = r["issues"]
    print(f"{inv['projeto']['modelo']}: {r['tabelas']} tabelas, {r['medidas']} medidas, "
          f"{r['relacionamentos']} relacionamentos, {r['visuais']} visuais")
    print(f"Issues: {sev.get('critical', 0)} críticos, {sev.get('medium', 0)} médios, {sev.get('light', 0)} leves")
    print(f"Saída: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
