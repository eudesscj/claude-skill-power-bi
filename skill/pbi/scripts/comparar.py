#!/usr/bin/env python3
"""
comparar.py — o que mudou num projeto Power BI (PBIP) entre dois momentos.

Compara dois inventários (gerados por inventario.py) e lista medidas, colunas, tabelas,
relacionamentos, RLS e parâmetros adicionados, removidos ou alterados — com o impacto
(medidas e visuais afetados) e as referências que ficaram quebradas.

Formas de uso (sempre a partir da pasta do projeto):
  python comparar.py <projeto> --antes <inventario.json>     antes = arquivo salvo; depois = projeto agora
  python comparar.py <projeto> --git [REF]                   antes = versão do git (padrão HEAD); depois = agora
  python comparar.py <projeto> --historico                   antes = inventário anterior em _pbi/historico/
  opcional: --depois <inventario.json>  --saida DIR  --modelo NOME

Saída: <saida>/comparacao.json e comparacao.md (padrão: <projeto>/_pbi/).
Só leitura no projeto. Só biblioteca padrão.
"""
import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inventario as invmod  # noqa: E402


def norm(expr):
    return re.sub(r"\s+", " ", (expr or "")).strip()


def _diff_campos(a, b, campos):
    mud = {}
    for c in campos:
        va, vb = a.get(c), b.get(c)
        if c in ("expressao",):
            if norm(va) != norm(vb):
                mud[c] = {"antes": va, "depois": vb}
            elif (va or "") != (vb or ""):
                mud["formatacao_expressao"] = True
        elif (va or None) != (vb or None):
            mud[c] = {"antes": va, "depois": vb}
    return mud


def _idx_medidas(inv):
    return {m["nome"].lower(): m for m in inv.get("medidas", [])}


def _idx_colunas(inv):
    out = {}
    for t in inv.get("tabelas", []):
        if t.get("papel_inferido") == "auto_data":
            continue
        for c in t["colunas"]:
            out[(t["nome"].lower(), c["nome"].lower())] = dict(c, tabela=t["nome"])
    return out


def _chave_rel(r):
    return tuple((x or "").lower() for x in (r["de_tabela"], r["de_coluna"], r["para_tabela"], r["para_coluna"]))


def _desc_rel(r):
    return f"{r['de_tabela']}[{r['de_coluna']}] → {r['para_tabela']}[{r['para_coluna']}]"


def comparar(antes, depois):
    res = {"antes": {"gerado_em": antes.get("gerado_em"), "origem": antes.get("_origem")},
           "depois": {"gerado_em": depois.get("gerado_em"), "origem": depois.get("_origem")}}

    # tabelas
    ta = {t["nome"].lower(): t for t in antes.get("tabelas", []) if t.get("papel_inferido") != "auto_data"}
    tb = {t["nome"].lower(): t for t in depois.get("tabelas", []) if t.get("papel_inferido") != "auto_data"}
    res["tabelas"] = {
        "adicionadas": sorted(tb[k]["nome"] for k in tb.keys() - ta.keys()),
        "removidas": sorted(ta[k]["nome"] for k in ta.keys() - tb.keys()),
        "alteradas": [],
    }
    for k in sorted(ta.keys() & tb.keys()):
        m = _diff_campos(ta[k], tb[k], ["descricao", "oculta", "data_category", "fontes", "modo"])
        if m:
            res["tabelas"]["alteradas"].append({"nome": tb[k]["nome"], "mudancas": m})

    # medidas
    ma, mb = _idx_medidas(antes), _idx_medidas(depois)
    res["medidas"] = {
        "adicionadas": [{"nome": mb[k]["nome"], "tabela": mb[k]["tabela"], "pasta": mb[k]["pasta"],
                         "expressao": mb[k]["expressao"]} for k in sorted(mb.keys() - ma.keys())],
        "removidas": [{"nome": ma[k]["nome"], "tabela": ma[k]["tabela"],
                       "usada_por_medidas": ma[k]["usada_por_medidas"], "visuais": ma[k]["visuais"]}
                      for k in sorted(ma.keys() - mb.keys())],
        "alteradas": [],
    }
    res["medidas"]["so_formatacao"] = []
    for k in sorted(ma.keys() & mb.keys()):
        m = _diff_campos(ma[k], mb[k], ["expressao", "formato", "pasta", "descricao", "tabela", "oculta"])
        if m == {"formatacao_expressao": True}:
            res["medidas"]["so_formatacao"].append(mb[k]["nome"])
        elif m:
            m.pop("formatacao_expressao", None)
            res["medidas"]["alteradas"].append({
                "nome": mb[k]["nome"], "mudancas": m,
                "impacto_medidas": mb[k]["impacto_medidas"], "impacto_visuais": mb[k]["impacto_visuais"]})

    # colunas
    ca, cb = _idx_colunas(antes), _idx_colunas(depois)
    novas_tab = {t.lower() for t in res["tabelas"]["adicionadas"]}
    velhas_tab = {t.lower() for t in res["tabelas"]["removidas"]}
    res["colunas"] = {
        "adicionadas": [f"{cb[k]['tabela']}[{cb[k]['nome']}]" for k in sorted(cb.keys() - ca.keys()) if k[0] not in novas_tab],
        "removidas": [{"coluna": f"{ca[k]['tabela']}[{ca[k]['nome']}]", "usada_por_medidas": ca[k]["usada_por_medidas"],
                       "usada_em": ca[k]["usada_em"], "visuais": ca[k]["visuais"]}
                      for k in sorted(ca.keys() - cb.keys()) if k[0] not in velhas_tab],
        "alteradas": [],
    }
    for k in sorted(ca.keys() & cb.keys()):
        m = _diff_campos(ca[k], cb[k], ["tipo", "expressao", "oculta", "chave", "sort_by", "descricao"])
        m.pop("formatacao_expressao", None)
        if m:
            res["colunas"]["alteradas"].append({
                "coluna": f"{cb[k]['tabela']}[{cb[k]['nome']}]", "mudancas": m,
                "impacto_medidas": cb[k]["impacto_medidas"], "impacto_visuais": cb[k]["impacto_visuais"]})

    # relacionamentos
    ra = {_chave_rel(r): r for r in antes.get("relacionamentos", [])}
    rb = {_chave_rel(r): r for r in depois.get("relacionamentos", [])}
    res["relacionamentos"] = {
        "adicionados": [_desc_rel(rb[k]) for k in sorted(rb.keys() - ra.keys())],
        "removidos": [_desc_rel(ra[k]) for k in sorted(ra.keys() - rb.keys())],
        "alterados": [],
    }
    for k in sorted(ra.keys() & rb.keys()):
        m = _diff_campos(ra[k], rb[k], ["ativo", "direcao", "card_de", "card_para"])
        if m:
            res["relacionamentos"]["alterados"].append({"relacionamento": _desc_rel(rb[k]), "mudancas": m})

    # RLS
    def perms(inv):
        out = {}
        for ro in inv.get("roles", []):
            for p in ro.get("permissoes", []):
                out[(ro["nome"].lower(), (p["tabela"] or "").lower())] = (ro["nome"], p["tabela"], p["expressao"])
            if not ro.get("permissoes"):
                out[(ro["nome"].lower(), "")] = (ro["nome"], "", "")
        return out
    pa, pb = perms(antes), perms(depois)
    res["rls"] = {
        "adicionadas": [f"{pb[k][0]} / {pb[k][1]}" for k in sorted(pb.keys() - pa.keys())],
        "removidas": [f"{pa[k][0]} / {pa[k][1]}" for k in sorted(pa.keys() - pb.keys())],
        "alteradas": [{"role": pb[k][0], "tabela": pb[k][1], "antes": pa[k][2], "depois": pb[k][2]}
                      for k in sorted(pa.keys() & pb.keys()) if norm(pa[k][2]) != norm(pb[k][2])],
    }

    # parâmetros / expressões M compartilhadas
    ea = {e["nome"].lower(): e for e in antes.get("expressoes", [])}
    eb = {e["nome"].lower(): e for e in depois.get("expressoes", [])}
    res["expressoes"] = {
        "adicionadas": sorted(eb[k]["nome"] for k in eb.keys() - ea.keys()),
        "removidas": sorted(ea[k]["nome"] for k in ea.keys() - eb.keys()),
        "alteradas": [eb[k]["nome"] for k in sorted(ea.keys() & eb.keys())
                      if norm(ea[k]["expressao"]) != norm(eb[k]["expressao"])],
    }

    # referências quebradas: dependentes de objetos removidos que ainda existem
    quebradas = []
    for m in res["medidas"]["removidas"]:
        vivos = [d for d in m["usada_por_medidas"] if d.lower() in mb]
        if vivos or m["visuais"]:
            quebradas.append({"objeto": f"[{m['nome']}]", "medidas": vivos, "visuais": m["visuais"]})
    for c in res["colunas"]["removidas"]:
        vivos = [d for d in c["usada_por_medidas"] if d.lower() in mb]
        if vivos or c["visuais"] or c["usada_em"]:
            quebradas.append({"objeto": c["coluna"], "medidas": vivos, "visuais": c["visuais"], "outros": c["usada_em"]})
    res["referencias_quebradas"] = quebradas
    res["avisos_novos"] = sorted(a for a in set(depois.get("avisos", [])) - set(antes.get("avisos", []))
                                 if ".gitignore" not in a)

    # issues
    def por_id(inv):
        d = {}
        for i in inv.get("issues", []):
            x = d.setdefault(i["id"], {"id": i["id"], "severidade": i["severidade"], "objetos": set(), "detalhes": []})
            x["objetos"].update(i.get("objetos") or [])
            x["detalhes"].append(i["detalhe"])
        return d
    ia, ib = por_id(antes), por_id(depois)
    res["issues"] = {
        "novos": [{"id": k, "severidade": ib[k]["severidade"], "detalhe": " | ".join(ib[k]["detalhes"][:3])}
                  for k in sorted(ib.keys() - ia.keys())],
        "resolvidos": [{"id": k, "severidade": ia[k]["severidade"]} for k in sorted(ia.keys() - ib.keys())],
        "mudaram": [{"id": k, "severidade": ib[k]["severidade"],
                     "entraram": sorted(ib[k]["objetos"] - ia[k]["objetos"]),
                     "sairam": sorted(ia[k]["objetos"] - ib[k]["objetos"])}
                    for k in sorted(ia.keys() & ib.keys()) if ia[k]["objetos"] != ib[k]["objetos"]],
    }

    # impacto consolidado
    imp_m, imp_v = set(), set()
    for x in res["medidas"]["alteradas"] + res["colunas"]["alteradas"]:
        imp_m.update(x["impacto_medidas"])
        imp_v.update(x["impacto_visuais"])
    for q in quebradas:
        imp_m.update(q["medidas"])
        imp_v.update(q["visuais"])
        for d in q["medidas"]:
            imp_v.update(mb[d.lower()]["impacto_visuais"])
    for m in res["medidas"]["alteradas"]:
        imp_m.add(m["nome"])
    res["impacto"] = {"medidas": sorted(imp_m), "visuais": sorted(imp_v)}

    secoes = ["tabelas", "medidas", "colunas", "relacionamentos", "rls", "expressoes"]
    res["sem_mudancas"] = not any(v for s in secoes for v in res[s].values())
    return res


def resumo_md(r):
    L = [f"# Comparação · {r['antes']['origem']} → {r['depois']['origem']}", "",
         f"Antes: {r['antes']['gerado_em']} · Depois: {r['depois']['gerado_em']}", ""]
    if r["sem_mudancas"]:
        L.append("Nenhuma mudança estrutural no modelo.")
    def bloco(titulo, itens):
        if itens:
            L.append(f"## {titulo}")
            L.append("")
            L.extend(f"- {i}" for i in itens)
            L.append("")
    med = r["medidas"]
    bloco("Medidas adicionadas", [f"[{m['nome']}] ({m['tabela']}{' · ' + m['pasta'] if m['pasta'] else ''})" for m in med["adicionadas"]])
    bloco("Medidas alteradas", [f"[{m['nome']}]: {', '.join(m['mudancas'])}"
                                f" · afeta {len(m['impacto_medidas'])} medida(s) e {len(m['impacto_visuais'])} visual(is)"
                                for m in med["alteradas"]])
    bloco("Medidas removidas", [f"[{m['nome']}]" for m in med["removidas"]])
    bloco("Medidas só reformatadas (sem mudança de lógica)", [f"[{n}]" for n in med["so_formatacao"]])
    col = r["colunas"]
    bloco("Colunas adicionadas", col["adicionadas"])
    bloco("Colunas alteradas", [f"{c['coluna']}: {', '.join(c['mudancas'])}" for c in col["alteradas"]])
    bloco("Colunas removidas", [c["coluna"] for c in col["removidas"]])
    t = r["tabelas"]
    bloco("Tabelas", [f"+ {x}" for x in t["adicionadas"]] + [f"− {x}" for x in t["removidas"]]
          + [f"~ {x['nome']}: {', '.join(x['mudancas'])}" for x in t["alteradas"]])
    rel = r["relacionamentos"]
    bloco("Relacionamentos", [f"+ {x}" for x in rel["adicionados"]] + [f"− {x}" for x in rel["removidos"]]
          + [f"~ {x['relacionamento']}: " + ", ".join(f"{k} {v['antes']}→{v['depois']}" for k, v in x["mudancas"].items())
             for x in rel["alterados"]])
    rls = r["rls"]
    bloco("RLS", [f"+ {x}" for x in rls["adicionadas"]] + [f"− {x}" for x in rls["removidas"]]
          + [f"~ {x['role']} / {x['tabela']}" for x in rls["alteradas"]])
    ex = r["expressoes"]
    bloco("Parâmetros / consultas compartilhadas", [f"+ {x}" for x in ex["adicionadas"]] + [f"− {x}" for x in ex["removidas"]]
          + [f"~ {x}" for x in ex["alteradas"]])
    bloco("⚠ Referências quebradas", [f"{q['objeto']} ainda usado por: " + ", ".join(
        [f"[{m}]" for m in q["medidas"]] + q["visuais"] + q.get("outros", [])) for q in r["referencias_quebradas"]])
    bloco("⚠ Avisos novos", r["avisos_novos"])
    bloco("Impacto: visuais para conferir", r["impacto"]["visuais"])
    bloco("Issues novos", [f"{i['severidade']} · {i['id']} — {i['detalhe']}" for i in r["issues"]["novos"]])
    bloco("Issues resolvidos", [f"{i['severidade']} · {i['id']}" for i in r["issues"]["resolvidos"]])
    bloco("Issues que mudaram de alcance", [f"{i['id']}: +{len(i['entraram'])} / −{len(i['sairam'])} objeto(s)"
                                            for i in r["issues"]["mudaram"]])
    return "\n".join(L) + "\n"


def digital(inv):
    """Impressão digital estrutural do modelo (ignora data de geração e issues)."""
    base = {
        "m": sorted((m["nome"], m["tabela"], norm(m["expressao"]), m.get("formato"), m.get("pasta"), m.get("descricao"))
                    for m in inv.get("medidas", [])),
        "c": sorted((t["nome"], c["nome"], c.get("tipo"), norm(c.get("expressao")), c.get("oculta"))
                    for t in inv.get("tabelas", []) for c in t["colunas"]),
        "r": sorted((_desc_rel(r), r["ativo"], r["direcao"], r["card_de"], r["card_para"]) for r in inv.get("relacionamentos", [])),
        "s": sorted((ro["nome"], p["tabela"], norm(p["expressao"])) for ro in inv.get("roles", []) for p in ro.get("permissoes", [])),
        "e": sorted((e["nome"], norm(e["expressao"])) for e in inv.get("expressoes", [])),
    }
    return json.dumps(base, ensure_ascii=False, sort_keys=True, default=str)


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True)


def inventario_do_git(raiz, ref, modelo_nome):
    top = _git(["rev-parse", "--show-toplevel"], raiz)
    if top.returncode != 0:
        raise invmod.ErroProjeto("A pasta do projeto não está num repositório git. Use --antes ou --historico.")
    top = Path(top.stdout.decode().strip())
    rel = raiz.resolve().relative_to(top.resolve()).as_posix()
    arq = _git(["archive", "--format=tar", ref, "--", rel or "."], top)
    if arq.returncode != 0:
        raise invmod.ErroProjeto(f"git archive falhou para '{ref}': {arq.stderr.decode(errors='ignore').strip()}")
    tmp = Path(tempfile.mkdtemp(prefix="pbi_git_"))
    with tarfile.open(fileobj=io.BytesIO(arq.stdout)) as tf:
        membros = [m for m in tf.getmembers() if not (m.name.startswith("/") or ".." in Path(m.name).parts)]
        try:
            tf.extractall(tmp, members=membros, filter="data")
        except TypeError:
            tf.extractall(tmp, members=membros)
    inv, _ = invmod.construir(tmp / rel if rel else tmp, modelo_nome)
    sha = _git(["rev-parse", "--short", ref], top).stdout.decode().strip()
    inv["_origem"] = f"git {ref} ({sha})"
    return inv


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Compara dois momentos de um projeto Power BI (PBIP).")
    ap.add_argument("caminho", help="Pasta do projeto PBIP")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--antes", help="inventario.json do momento anterior")
    g.add_argument("--git", nargs="?", const="HEAD", help="Referência git do momento anterior (padrão HEAD)")
    g.add_argument("--historico", action="store_true", help="Usar o inventário anterior em _pbi/historico/")
    ap.add_argument("--depois", help="inventario.json do momento posterior (padrão: gerar agora)")
    ap.add_argument("--saida", help="Pasta de saída (padrão: <projeto>/_pbi)")
    ap.add_argument("--modelo", help="Nome do .SemanticModel quando há mais de um")
    a = ap.parse_args(argv)

    try:
        if a.depois:
            depois = json.loads(Path(a.depois).read_text(encoding="utf-8"))
            depois["_origem"] = Path(a.depois).name
            raiz = Path(depois["projeto"]["raiz"])
        else:
            depois, raiz = invmod.construir(a.caminho, a.modelo)
            depois["_origem"] = "projeto atual"
        if a.antes:
            antes = json.loads(Path(a.antes).read_text(encoding="utf-8"))
            antes["_origem"] = Path(a.antes).name
        elif a.historico:
            pbi = raiz / "_pbi"
            cands = sorted((pbi / "historico").glob("inventario-*.json")) if (pbi / "historico").is_dir() else []
            if (pbi / "inventario.json").is_file():
                cands.append(pbi / "inventario.json")
            if not cands:
                raise invmod.ErroProjeto("Não há inventário anterior em _pbi/ para comparar.")
            # o mais recente cujo modelo seja diferente do atual
            alvo = digital(depois)
            escolhido = None
            for c in reversed(cands):
                inv_c = json.loads(c.read_text(encoding="utf-8"))
                if digital(inv_c) != alvo:
                    escolhido = (c, inv_c)
                    break
            if not escolhido:
                print("Nenhuma mudança no modelo desde o último inventário salvo.")
                return 0
            antes = escolhido[1]
            antes["_origem"] = escolhido[0].name
        else:
            antes = inventario_do_git(raiz, a.git, a.modelo)
    except invmod.ErroProjeto as e:
        print(str(e), file=sys.stderr)
        return 2

    r = comparar(antes, depois)
    r["gerado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    saida = Path(a.saida) if a.saida else raiz / "_pbi"
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "comparacao.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    (saida / "comparacao.md").write_text(resumo_md(r), encoding="utf-8")
    med, col = r["medidas"], r["colunas"]
    print(f"{r['antes']['origem']} → {r['depois']['origem']}")
    print(f"Medidas: +{len(med['adicionadas'])} ~{len(med['alteradas'])} −{len(med['removidas'])} · "
          f"Colunas: +{len(col['adicionadas'])} ~{len(col['alteradas'])} −{len(col['removidas'])} · "
          f"Referências quebradas: {len(r['referencias_quebradas'])}")
    print(f"Saída: {saida / 'comparacao.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
