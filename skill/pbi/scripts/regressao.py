#!/usr/bin/env python3
"""
regressao.py — gera consultas DAX de validação/regressão e compara resultados.

O script NÃO conecta no Power BI: ele monta o texto DAX. Quem executa é o Power BI Modeling MCP
(dax_query_operations → Execute, resultMode Inline). Toda consulta é só leitura e usa
DEFINE MEASURE, que vale apenas durante a consulta — o modelo não é alterado.

Subcomandos:
  casos      <projeto> [--casos "..."]          lista os casos de regressão (do pbi.projeto.md ou automáticos)
  baseline   <projeto> [--casos "..."]          DAX que devolve 1 linha de "impressão digital" por caso
  comparar   <antes.json> <depois.json> [--esperadas "[M1];[M2]"]   compara duas impressões digitais
  diff       <projeto> --antes <inventario.json> --medida "[M]" --por "T[C]" [--por ...]
                                                DAX que compara linha a linha a versão antiga (do inventário)
                                                com a atual, devolvendo só as linhas que mudaram
  validar    <projeto> --expressao <arquivo.dax|texto> --tabela T [--por "T[C]"] [--comparar-com "[M]"]
                                                DAX que testa uma medida proposta antes de criá-la
  rls        <projeto> [--casos "..."]          plano do teste de RLS: DAX (o mesmo do baseline) + roles,
                                                se são dinâmicas e os usuários de teste do pbi.projeto.md
  rls-comparar --base <sem_role.json> --role "Nome=arquivo.json" [--role ...]
                                                compara o resultado de cada role com o sem role

Formato de caso: "[Medida] por T[Col] e T2[Col2]"  (sem "por" = só o total). Vários casos separados por ";".
Arquivos JSON de resultado: o objeto "data" devolvido pelo Execute do MCP, salvo como está.
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inventario as invmod  # noqa: E402

TOL_PADRAO = 1e-6


# ----------------------------------------------------------------------------- utilidades

def q(nome):
    """Nome de tabela entre aspas simples para DAX."""
    return "'" + nome.replace("'", "''") + "'"


def ref_col(t, c):
    return f"{q(t)}[{c.replace(']', ']]')}]"


def ref_med(m):
    return f"[{m.replace(']', ']]')}]"


def ler_inventario(projeto, modelo=None):
    """Sempre do projeto como está agora (rápido; evita inventário desatualizado)."""
    inv, _ = invmod.construir(projeto, modelo)
    return inv


CASO_RE = re.compile(r"\[([^\]]+)\]\s*(?:por\s+(.+))?$", re.I)
COL_RE = re.compile(r"('(?:[^']|'')+'|[^\W\d][\w]*)\[([^\]]+)\]", re.U)


def parse_caso(texto, inv):
    texto = texto.strip().lstrip("-").strip()
    m = CASO_RE.match(texto)
    if not m:
        raise ValueError(f"Caso inválido: {texto}")
    medida = m.group(1)
    idx_m = {x["nome"].lower(): x for x in inv["medidas"]}
    if medida.lower() not in idx_m:
        raise ValueError(f"Medida [{medida}] não existe no modelo")
    medida = idx_m[medida.lower()]["nome"]
    cols = []
    idx_c = {(t["nome"].lower(), c["nome"].lower()): (t["nome"], c["nome"]) for t in inv["tabelas"] for c in t["colunas"]}
    for tq, c in COL_RE.findall(m.group(2) or ""):
        t = tq[1:-1].replace("''", "'") if tq.startswith("'") else tq
        k = (t.lower(), c.lower())
        if k not in idx_c:
            raise ValueError(f"Coluna {t}[{c}] não existe no modelo")
        cols.append(idx_c[k])
    return {"id": f"[{medida}]" + (" por " + ", ".join(f"{a}[{b}]" for a, b in cols) if cols else ""),
            "medida": medida, "por": cols}


def casos_do_projeto(projeto, inv):
    arq = Path(projeto) / "pbi.projeto.md"
    if not arq.is_file():
        return []
    linhas, dentro = [], False
    for l in arq.read_text(encoding="utf-8").splitlines():
        if l.strip().startswith("#"):
            dentro = "medidas-chave" in l.lower() or "medidas chave" in l.lower()
            continue
        if dentro and l.strip().startswith("-") and "[" in l:
            linhas.append(l)
    return [parse_caso(l, inv) for l in linhas]


def casos_automaticos(inv, n=5):
    """Medidas mais vistas no relatório; quebra pelo ano do calendário se houver relacionamento com ele."""
    meds = sorted(inv["medidas"], key=lambda m: (-len(m["visuais"]), -len(m["impacto_visuais"]), m["nome"]))
    meds = [m for m in meds if m["visuais"] or m["impacto_visuais"]][:n] or inv["medidas"][:n]
    cal = None
    cal_tabs = inv["convencoes_detectadas"].get("tabelas_calendario") or []
    ligadas = {r["para_tabela"] for r in inv["relacionamentos"] if r["ativo"]} | {r["de_tabela"] for r in inv["relacionamentos"] if r["ativo"]}
    for t in inv["tabelas"]:
        if t["nome"] in cal_tabs and t["nome"] in ligadas:
            for c in t["colunas"]:
                if c["nome"].lower() in ("ano", "year"):
                    cal = (t["nome"], c["nome"])
    casos = []
    for m in meds:
        casos.append({"id": f"[{m['nome']}]", "medida": m["nome"], "por": []})
        if cal:
            casos.append({"id": f"[{m['nome']}] por {cal[0]}[{cal[1]}]", "medida": m["nome"], "por": [cal]})
    return casos


def obter_casos(a, inv):
    if a.casos:
        return [parse_caso(x, inv) for x in a.casos.split(";") if x.strip()]
    casos = casos_do_projeto(a.projeto, inv)
    return casos or casos_automaticos(inv)


def tabela_linhas(por, expr_medida):
    """Tabela com as combinações das colunas e a coluna [v] (sem linhas em branco)."""
    if len(por) == 1:
        base = f"VALUES( {ref_col(*por[0])} )"
    else:
        base = "SUMMARIZECOLUMNS( " + ", ".join(ref_col(t, c) for t, c in por) + f', "__x", {expr_medida} )'
        # SUMMARIZECOLUMNS já remove linhas em branco; mantém só as colunas-chave
        base = "SELECTCOLUMNS( " + base + ", " + ", ".join(f'"{c}", {ref_col(t, c)}' for t, c in por) + " )"
        return f'FILTER( ADDCOLUMNS( {base}, "v", {expr_medida} ), NOT ISBLANK( [v] ) )', \
            " & \"|\" & ".join(f"[{c}]" for _, c in por)
    return f'FILTER( ADDCOLUMNS( {base}, "v", {expr_medida} ), NOT ISBLANK( [v] ) )', ref_col(*por[0])


# ----------------------------------------------------------------------------- DAX

def dax_baseline(casos):
    partes = []
    for c in casos:
        med = ref_med(c["medida"])
        if not c["por"]:
            partes.append(f'ROW( "caso", "{c["id"]}", "linhas", 1, "total", {med}, "soma", {med}, "checksum", {med} )')
            continue
        tab, chave_expr = tabela_linhas(c["por"], med)
        partes.append(
            f'VAR __t = ADDCOLUMNS( {tab}, "k", {chave_expr} & "" )\n'
            f'    VAR __r = ADDCOLUMNS( __t, "r", RANKX( __t, [k], , ASC, DENSE ) )\n'
            f'    RETURN ROW( "caso", "{c["id"]}", "linhas", COUNTROWS( __r ), "total", {med}, '
            f'"soma", SUMX( __r, [v] ), "checksum", SUMX( __r, [v] * [r] ) )')
    if len(partes) == 1:
        return "EVALUATE\n" + partes[0]
    return "EVALUATE\nUNION(\n    " + ",\n    ".join(partes) + "\n)"


def renomear_refs(expr, mapa):
    """Troca [X] por [__antes_X] para X em mapa (referência de medida sem tabela)."""
    def troca(m):
        nome = m.group(1).replace("]]", "]")
        novo = mapa.get(nome.lower())
        return ref_med(novo) if novo else m.group(0)
    # só refs sem tabela antes (medidas)
    return re.sub(r"(?<![\w'\]])\[((?:[^\]]|\]\])+)\]", troca, expr)


def dax_diff(inv_atual, inv_antes, medida, por, tol):
    ant = {m["nome"].lower(): m for m in inv_antes["medidas"]}
    atu = {m["nome"].lower(): m for m in inv_atual["medidas"]}
    if medida.lower() not in ant:
        raise ValueError(f"[{medida}] não existe no inventário anterior (medida nova: use 'validar')")
    # medidas antigas necessárias: fechamento das dependências da medida no inventário antigo
    necessarias, fila = set(), [medida.lower()]
    while fila:
        x = fila.pop()
        if x in necessarias or x not in ant:
            continue
        necessarias.add(x)
        fila.extend(d.lower() for d in ant[x]["depende_de"]["medidas"])
    # só redefinir as que mudaram ou que dependem (no antigo) de alguma que mudou
    mudou = {x for x in necessarias if x not in atu or invmod_norm(ant[x]["expressao"]) != invmod_norm(atu[x]["expressao"])}
    afetadas = set(mudou)
    alterou = True
    while alterou:
        alterou = False
        for x in necessarias - afetadas:
            if any(d.lower() in afetadas for d in ant[x]["depende_de"]["medidas"]):
                afetadas.add(x)
                alterou = True
    if medida.lower() not in afetadas:
        return None, "A medida e suas dependências não mudaram de expressão; diferenças viriam de dados, relacionamentos ou colunas (use baseline)."
    mapa = {x: "__antes_" + ant[x]["nome"] for x in afetadas}
    defs = []
    for x in sorted(afetadas):
        m = ant[x]
        tab = m["tabela"] if m["tabela"].lower() in {t["nome"].lower() for t in inv_atual["tabelas"]} else atu[medida.lower()]["tabela"]
        defs.append(f"    MEASURE {q(tab)}[{mapa[x]}] =\n        " + renomear_refs(m["expressao"], mapa).replace("\n", "\n        "))
    antes_ref, depois_ref = ref_med(mapa[medida.lower()]), ref_med(atu[medida.lower()]["nome"]) if medida.lower() in atu else "BLANK()"
    if por:
        base = "SUMMARIZECOLUMNS( " + ", ".join(ref_col(t, c) for t, c in por) + f', "antes", {antes_ref}, "depois", {depois_ref} )'
        corpo = (f'VAR __t = ADDCOLUMNS( {base}, "dif", [depois] - [antes] )\n'
                 f'VAR __mud = FILTER( __t, ABS( [dif] ) > {tol} || ISBLANK( [antes] ) <> ISBLANK( [depois] ) )\n'
                 f'RETURN TOPN( 50, __mud, ABS( [dif] ), DESC )')
    else:
        corpo = f'ROW( "antes", {antes_ref}, "depois", {depois_ref}, "dif", {depois_ref} - {antes_ref} )'
    return "DEFINE\n" + "\n".join(defs) + "\nEVALUATE\n" + corpo, None


def invmod_norm(e):
    return re.sub(r"\s+", " ", e or "").strip()


def dax_validar(tabela, expressao, por, comparar_com):
    nome = "__proposta"
    defs = f"DEFINE\n    MEASURE {q(tabela)}[{nome}] =\n        " + expressao.strip().replace("\n", "\n        ")
    med = ref_med(nome)
    if not por:
        return defs + f'\nEVALUATE\nROW( "total", {med} )'
    tab, _ = tabela_linhas(por, med)
    extra = ""
    if comparar_com:
        cmp_ = ref_med(comparar_com)
        extra = (f', "total_atual", {cmp_}, '
                 f'"linhas_diferentes_da_atual", COUNTROWS( FILTER( ADDCOLUMNS( __t, "a", {cmp_} ), ABS( [v] - [a] ) > {TOL_PADRAO} ) )')
    return (defs + "\nEVALUATE\n"
            f"VAR __t = {tab}\n"
            f"VAR __tot = {med}\n"
            f'RETURN ROW( "total", __tot, "linhas", COUNTROWS( __t ), "soma_das_linhas", SUMX( __t, [v] ), '
            f'"linhas_iguais_ao_total", COUNTROWS( FILTER( __t, [v] = __tot ) ), '
            f'"infinitos", COUNTROWS( FILTER( __t, [v] = 1/0 || [v] = -1/0 ) ), '
            f'"minimo", MINX( __t, [v] ), "maximo", MAXX( __t, [v] ){extra} )')


# ----------------------------------------------------------------------------- comparação de impressões digitais

def _linhas(arq):
    d = json.loads(Path(arq).read_text(encoding="utf-8"))
    d = d.get("data", d)
    rows = d.get("rows", d if isinstance(d, list) else [])
    out = {}
    for r in rows:
        g = {k.strip("[]").split("[")[-1].rstrip("]"): v for k, v in r.items()}
        out[g["caso"]] = g
    return out


def comparar_digitais(antes, depois, esperadas, tol):
    a, b = _linhas(antes), _linhas(depois)
    esp = {e.strip().strip("[]").lower() for e in esperadas if e.strip()}
    res = {"iguais": [], "mudaram_esperado": [], "mudaram_inesperado": [], "novos": sorted(b.keys() - a.keys()),
           "sumiram": sorted(a.keys() - b.keys())}

    def dif(x, y):
        if x is None or y is None:
            return x is not y
        escala = max(abs(x), abs(y))
        return abs(x - y) > max(tol, 1e-9 * escala)

    for k in sorted(a.keys() & b.keys()):
        x, y = a[k], b[k]
        mud = [c for c in ("linhas", "total", "soma", "checksum") if dif(x.get(c), y.get(c))]
        if not mud:
            res["iguais"].append(k)
            continue
        medida = re.match(r"\[([^\]]+)\]", k).group(1).lower()
        item = {"caso": k, "campos": mud, "total_antes": x.get("total"), "total_depois": y.get("total"),
                "linhas_antes": x.get("linhas"), "linhas_depois": y.get("linhas")}
        res["mudaram_esperado" if medida in esp else "mudaram_inesperado"].append(item)
    return res


def md_comparacao(r):
    L = ["# Regressão", ""]
    if r["mudaram_inesperado"]:
        L += ["## ⚠ Mudaram sem estar no plano", ""]
        L += [f"- {i['caso']}: total {i['total_antes']} → {i['total_depois']} ({', '.join(i['campos'])})" for i in r["mudaram_inesperado"]]
        L.append("")
    if r["mudaram_esperado"]:
        L += ["## Mudaram como esperado", ""]
        L += [f"- {i['caso']}: total {i['total_antes']} → {i['total_depois']}" for i in r["mudaram_esperado"]]
        L.append("")
    L += [f"Iguais: {len(r['iguais'])} caso(s)."]
    if r["novos"] or r["sumiram"]:
        L += ["", f"Casos novos: {', '.join(r['novos']) or '—'} · Casos que sumiram: {', '.join(r['sumiram']) or '—'}"]
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- RLS

def usuarios_teste(projeto):
    """Lê '## RLS' do pbi.projeto.md: '- Role: usuario@dominio (espera ...)'."""
    arq = Path(projeto) / "pbi.projeto.md"
    out = {}
    if not arq.is_file():
        return out
    dentro = False
    for l in arq.read_text(encoding="utf-8").splitlines():
        if l.strip().startswith("#"):
            dentro = l.strip("# ").strip().lower().startswith("rls")
            continue
        m = re.match(r"\s*-\s*(?:role\s+)?[\"']?([^:\"']+?)[\"']?\s*:\s*(.*)$", l, re.I) if dentro else None
        if m:
            email = re.search(r"[\w.+-]+@[\w.-]+", m.group(2))
            out.setdefault(m.group(1).strip().lower(), []).append(
                {"usuario": email.group(0) if email else None, "espera": m.group(2).strip()})
    return out


def plano_rls(projeto, inv, casos):
    testes = usuarios_teste(projeto)
    roles = []
    for ro in inv.get("roles", []):
        dinamica = any(re.search(r"\b(USERPRINCIPALNAME|USERNAME|CUSTOMDATA|USEROBJECTID)\s*\(", p["expressao"] or "", re.I)
                       for p in ro.get("permissoes", []))
        roles.append({"role": ro["nome"], "dinamica": dinamica,
                      "filtros": [f"{p['tabela']}: {p['expressao']}" for p in ro.get("permissoes", [])],
                      "testes": testes.get(ro["nome"].lower(), [])})
    return {"dax": dax_baseline(casos), "casos": [c["id"] for c in casos], "roles": roles}


def comparar_rls(base_arq, roles_arqs, tol=TOL_PADRAO):
    base = _linhas(base_arq)
    res = {"roles": [], "soma_por_caso": {}}
    for nome, arq in roles_arqs:
        r = _linhas(arq)
        item = {"role": nome, "casos": [], "veredito": None}
        vazios = iguais = 0
        for caso, b in base.items():
            x = r.get(caso)
            if x is None:
                continue
            tb, tr = b.get("total"), x.get("total")
            vazio = tr is None or (x.get("linhas") or 0) == 0
            igual = (tb is not None and tr is not None and abs(tb - tr) <= max(tol, 1e-9 * max(abs(tb), abs(tr)))
                     and x.get("linhas") == b.get("linhas"))
            vazios += vazio
            iguais += igual
            pct = (tr / tb) if (tb not in (None, 0) and tr is not None) else None
            item["casos"].append({"caso": caso, "total_sem_role": tb, "total_role": tr, "linhas_sem_role": b.get("linhas"),
                                  "linhas_role": x.get("linhas"), "proporcao": pct})
            res["soma_por_caso"].setdefault(caso, 0.0)
            res["soma_por_caso"][caso] += tr or 0.0
        n = len(item["casos"])
        if n and vazios == n:
            item["veredito"] = "nao_ve_nada"
        elif n and iguais == n:
            item["veredito"] = "nao_restringe"
        else:
            item["veredito"] = "restringe"
        res["roles"].append(item)
    res["total_sem_role"] = {c: b.get("total") for c, b in base.items()}
    return res


def md_rls(r):
    rotulo = {"nao_ve_nada": "⚠ não vê nada", "nao_restringe": "⚠ vê tudo (não restringe)", "restringe": "restringe"}
    L = ["# Teste de RLS", ""]
    for it in r["roles"]:
        L.append(f"## {it['role']} — {rotulo[it['veredito']]}")
        L.append("")
        for c in it["casos"]:
            p = f" ({c['proporcao']:.1%} do total)" if c["proporcao"] is not None else ""
            L.append(f"- {c['caso']}: {c['total_role']} de {c['total_sem_role']}{p} · linhas {c['linhas_role']}/{c['linhas_sem_role']}")
        L.append("")
    if len(r["roles"]) > 1:
        L += ["## Soma das roles × total sem role", "",
              "Se as roles dividem os dados entre si (ex.: uma por regional), a soma deveria bater com o total.", ""]
        for caso, soma in r["soma_por_caso"].items():
            L.append(f"- {caso}: soma {soma} · total {r['total_sem_role'].get(caso)}")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- CLI

def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Consultas DAX de validação e regressão (executar via Power BI Modeling MCP).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("casos", "baseline"):
        s = sub.add_parser(nome)
        s.add_argument("projeto")
        s.add_argument("--casos")
        s.add_argument("--modelo")
    s = sub.add_parser("comparar")
    s.add_argument("antes")
    s.add_argument("depois")
    s.add_argument("--esperadas", default="")
    s.add_argument("--tolerancia", type=float, default=TOL_PADRAO)
    s.add_argument("--saida")
    s = sub.add_parser("diff")
    s.add_argument("projeto")
    s.add_argument("--antes", required=True)
    s.add_argument("--medida", required=True)
    s.add_argument("--por", action="append", default=[])
    s.add_argument("--tolerancia", type=float, default=TOL_PADRAO)
    s.add_argument("--modelo")
    s = sub.add_parser("rls")
    s.add_argument("projeto")
    s.add_argument("--casos")
    s.add_argument("--modelo")
    s = sub.add_parser("rls-comparar")
    s.add_argument("--base", required=True)
    s.add_argument("--role", action="append", default=[], help='"Nome da role=arquivo.json"')
    s.add_argument("--saida")
    s = sub.add_parser("validar")
    s.add_argument("projeto")
    s.add_argument("--expressao", required=True)
    s.add_argument("--tabela", required=True)
    s.add_argument("--por", action="append", default=[])
    s.add_argument("--comparar-com")
    s.add_argument("--modelo")
    a = ap.parse_args(argv)

    try:
        if a.cmd == "comparar":
            r = comparar_digitais(a.antes, a.depois, a.esperadas.split(";"), a.tolerancia)
            md = md_comparacao(r)
            if a.saida:
                Path(a.saida).mkdir(parents=True, exist_ok=True)
                (Path(a.saida) / "regressao.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
                (Path(a.saida) / "regressao.md").write_text(md, encoding="utf-8")
            print(md)
            return 1 if r["mudaram_inesperado"] else 0

        if a.cmd == "rls-comparar":
            pares = []
            for x in a.role:
                if "=" not in x:
                    raise ValueError(f'--role deve ser "Nome=arquivo.json": {x}')
                n, f = x.split("=", 1)
                pares.append((n.strip(), f.strip()))
            r = comparar_rls(a.base, pares)
            md = md_rls(r)
            if a.saida:
                Path(a.saida).mkdir(parents=True, exist_ok=True)
                (Path(a.saida) / "rls.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
                (Path(a.saida) / "rls.md").write_text(md, encoding="utf-8")
            print(md)
            return 1 if any(i["veredito"] != "restringe" for i in r["roles"]) else 0

        inv = ler_inventario(a.projeto, getattr(a, "modelo", None))
        if a.cmd == "rls":
            plano = plano_rls(a.projeto, inv, obter_casos(a, inv))
            if not plano["roles"]:
                print("O modelo não tem roles de RLS.")
                return 0
            print(json.dumps(plano, ensure_ascii=False, indent=2))
            return 0
        if a.cmd == "casos":
            for c in obter_casos(a, inv):
                print(c["id"])
            return 0
        if a.cmd == "baseline":
            casos = obter_casos(a, inv)
            print(f"-- {len(casos)} caso(s) · gerado em {datetime.now():%Y-%m-%d %H:%M}")
            print(dax_baseline(casos))
            return 0
        if a.cmd == "diff":
            antes = json.loads(Path(a.antes).read_text(encoding="utf-8"))
            por = [parse_caso(f"[{inv['medidas'][0]['nome']}] por " + p, inv)["por"][0] for p in a.por]
            dax, aviso = dax_diff(inv, antes, a.medida.strip().strip("[]"), por, a.tolerancia)
            print(aviso if aviso else dax)
            return 0
        if a.cmd == "validar":
            expr = Path(a.expressao).read_text(encoding="utf-8") if Path(a.expressao).is_file() else a.expressao
            if inv["medidas"]:
                por = [parse_caso(f"[{inv['medidas'][0]['nome']}] por " + p, inv)["por"][0] for p in a.por]
            else:
                por = []
            print(dax_validar(a.tabela, expr, por, (a.comparar_com or "").strip().strip("[]") or None))
            return 0
    except (ValueError, invmod.ErroProjeto) as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
