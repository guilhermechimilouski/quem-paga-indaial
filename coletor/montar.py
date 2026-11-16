"""Junta tudo em docs/data.json, o único arquivo que o site lê."""
from datetime import date

from .comum import BRUTOS, SITE, gravar, ler, up

MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def per(m):
    return MES[int(m[:2]) - 1] + "/" + m[3:]


def iso(m):
    return m[3:] + "-" + m[:2]


def montar():
    cfg = ler("config.json")
    lista = ler("vereadores.json")
    gab = ler("gabinetes.json")
    seed = ler(BRUTOS / "base_v1.json")
    col = ler(BRUTOS / "coletado.json")
    fa = ler(BRUTOS / "folha_agg.json")
    fu = ler(BRUTOS / "folha_ultimo.json")
    ult, ult_mes = fu["pessoas"], fu["mes"]
    dh = ler(BRUTOS / "diarias_hist.json")
    dv = ler(BRUTOS / "diarias_vereador.json")
    desp = ler(BRUTOS / "despesas2026.json")
    seedv = {v["nome"]: v for v in seed["vereadores"]}
    col = col or {}
    tem = lambda k: k in col
    pres = col["presenca"] if tem("presenca") else ler(BRUTOS / "presenca.json")
    ped = col["pedidos"] if tem("pedidos") else ler(BRUTOS / "pedidos.json")
    PATR = cfg["patronal"]

    mand = fa["meses"]
    tot = fa["tot"]
    ano0 = 2021
    ant = [f"{(i % 12) + 1:02d}/{ano0 + i // 12}" for i in range(len(mand))]
    falta = [m for m in ant if m not in tot]
    if falta:
        raise SystemExit(f"Faltam meses da legislatura anterior para comparar: {falta}")

    V, gab_total = [], 0
    for v in lista:
        k = up(v["nome"])
        f = fa["v"][k]
        serie = [{"m": iso(m), "v": s[0], "a": s[1]} for m, s in zip(mand, f["s"])]
        desde = next((x["m"] for x in serie if x["a"] > 0), None)
        anos = sorted(a for a in dv.get(k, {}) if a >= "2025")
        diar = round(sum(dv[k][a] for a in anos), 2)
        sal = f["sub"] + f["ass"]
        cur = [{"nome": ult[a][0].title(), "cargo": ult[a][1].capitalize(), "bruto": ult[a][2]} for a in gab[k] if a in ult]
        if ult_mes == "10/2026":
            cur = [{"nome": a["nome"], "cargo": a["cargo"], "bruto": a["bruto"]} for a in seedv[v["nome"]]["assessores"]]
        last = f["s"][-1]
        gab_total += sal
        sv = seedv[v["nome"]]
        V.append(dict(nome=v["nome"], slug=v["slug"], partido=v["partido"], funcao=v["funcao"], votosEleicao=v["votosEleicao"],
                      perfil=v["perfil"],
                      custo=dict(mesAtual=dict(subsidio=last[0], assessores=cur, total=round(last[0] + sum(a["bruto"] for a in cur), 2)),
                                 mandato=dict(subsidio=f["sub"], assessores=f["ass"], diarias=diar, patronal=round(sal * PATR, 2),
                                              total=round(sal + diar + round(sal * PATR, 2), 2)),
                                 serie=serie, assessorDesde=desde),
                      presenca=pres[v["nome"]],
                      votos=col["votos"][v["nome"]] if tem("votos") else sv["votos"],
                      props=col["props"].get(v["nome"], {}) if tem("props") else sv["props"],
                      contra=col["contra"][v["nome"]] if tem("contra") else sv["contra"],
                      pedidos={x: ped["per"][v["nome"]][x] for x in ("ind", "inf", "selfRep", "selfTop")}))

    c = dict(seed["camara"], **col.get("camara", {}))
    anteriores = [a for a in dh if "2021" <= a <= "2024"]
    anos_mand = sorted(a for a in dh if a >= "2025")
    cam = dict(folhaMandato=round(sum(tot[m][1] for m in mand), 2),
               folhaAnteriorMesmoPeriodo=round(sum(tot[m][1] for m in ant), 2),
               folhaPessoasMes=tot[mand[-1]][0], gabinetesMandato=round(gab_total, 2),
               gabineteMedioMes=round(sum(x["custo"]["mesAtual"]["total"] for x in V) / len(V), 2),
               diarias={a: dh[a] for a in anos_mand}, diariasMediaAnterior=round(sum(dh[a] for a in anteriores) / len(anteriores), 2),
               diariasHist=dh, despesas=desp,
               **{k: c[k] for k in ("votacoes", "sessoes", "rejeitadas", "divididas", "rejSemAta", "divSemAta", "propsTotal")},
               folhaMensal=[{"m": iso(m), "v": tot[m][1]} for m in mand],
               folhaMensalAnt=[{"m": iso(m), "v": tot[m][1]} for m in ant],
               subsidio2025=cfg["subsidio"]["2025"], subsidio2026=cfg["subsidio"]["2026"])
    data = dict(atualizado=col.get("atualizado") or col.get("atualizadoProps") or seed["atualizado"],
                periodoFolha=f"{per(mand[0])} a {per(mand[-1])}", ultimoMes=per(mand[-1]),
                camara=cam, vereadores=V,
                divididas=col["divididas"] if tem("divididas") else seed["divididas"],
                atas=col["atas"] if tem("atas") else seed["atas"],
                pedidos={x: ped[x] for x in ("top", "indT", "infT", "repGrupos", "repPedidos", "indTotal", "infTotal")},
                repo=cfg.get("repo", ""), correcoes=ler("correcoes.json", []))
    gravar(SITE / "data.json", data, compacto=True)
    from . import paginas
    paginas.gerar()
    print(f"docs/data.json gerado: folha até {per(mand[-1])}, {len(V)} vereadores, atualizado {data['atualizado']}")
    return data
