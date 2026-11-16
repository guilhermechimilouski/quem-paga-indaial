"""Transforma o banco coletado (dados/radar.db) nos números que o site usa (dados/brutos/coletado.json)."""
import collections
import re
from datetime import date

from .classificar import rua, tema, tipo_prop
from .comum import BRUTOS, gravar, identificar, ler, up, vereadores

PLENARIO = ("Sessão Ordinária", "Sessão Extraordinária")
CLASSES = ["indicacao", "mocao_homenagem", "mocao_posicionamento", "pl_rua", "pl_homenagem", "pl_substantivo",
           "req_info", "req_outros", "outros"]


def ausencias(texto, lista):
    """Lê o trecho da ata antes de 'número legal' e devolve {vereador: 'licenca'|'just'|'semJust'}."""
    t = up(texto)
    corte = t.find("NUMERO LEGAL")
    trecho = t[:corte] if corte > 0 else t[:4000]
    saida = {}
    def motivo(txt):
        if "LICENC" in txt:
            return "licenca"
        if re.search(r"JUSTIFIC|ATESTADO|MOTIVO|\(", txt):
            return "just"
        return None

    for clausula in re.split(r"[.;]\s", trecho):
        if "AUSEN" not in clausula and "LICENC" not in clausula:
            continue
        achados = []
        for v in lista:
            m = re.search(up(v["token"]).replace("\\B", "\\b"), clausula)
            if m:
                achados.append((m.start(), v["nome"]))
        achados.sort()
        cauda = motivo(clausula[achados[-1][0]:]) if achados else None
        for i, (ini, nome) in enumerate(achados):
            fim = achados[i + 1][0] if i + 1 < len(achados) else len(clausula)
            saida[nome] = motivo(clausula[ini:fim]) or cauda or "semJust"
    return saida


def proposicoes(con, lista, nomes):
    props = {n: collections.Counter() for n in nomes + ["Executivo"]}
    ind_t, inf_t = collections.Counter(), collections.Counter()
    per = {n: dict(ind=collections.Counter(), inf=collections.Counter(), grupos=collections.Counter()) for n in nomes}
    grupos = collections.defaultdict(lambda: dict(n=0, de="9999", ate="0000", aut=collections.Counter()))
    total_props = 0
    for tipo, data, ementa, autoria in con.execute("SELECT tipo, data, ementa, autoria FROM proposicoes WHERE data >= '2025-01-01'"):
        total_props += 1
        classe = tipo_prop(tipo, ementa)
        autores = [x for x in (autoria or "").split(";") if x.strip()]
        quem = set()
        for a in autores:
            n = identificar(a, lista) or ("Executivo" if re.search(r"PREFEIT|EXECUTIVO", up(a)) else None)
            if n:
                quem.add(n)
        for n in quem:
            props[n][classe] += 1
        if classe not in ("indicacao", "req_info"):
            continue
        tm = tema(ementa)
        (ind_t if classe == "indicacao" else inf_t)[tm] += 1
        r = rua(ementa) if classe == "indicacao" else None
        for n in quem & set(nomes):
            per[n]["ind" if classe == "indicacao" else "inf"][tm] += 1
            if r:
                per[n]["grupos"][f"{tm}|{r}"] += 1
        if r:
            g = grupos[(tm, r)]
            g["n"] += 1
            g["de"], g["ate"] = min(g["de"], data[:10]), max(g["ate"], data[:10])
            for n in quem & set(nomes):
                g["aut"][n] += 1

    rep = [g for g in grupos.values() if g["n"] > 1]
    top = sorted(([k, g] for k, g in grupos.items() if g["n"] > 1), key=lambda x: -x[1]["n"])[:30]
    pedidos = dict(
        per={n: dict(ind=dict(per[n]["ind"]), inf=dict(per[n]["inf"]),
                     selfRep=sum(c for c in per[n]["grupos"].values() if c > 1),
                     selfTop=[[k, c] for k, c in per[n]["grupos"].most_common(5) if c > 1]) for n in nomes},
        top=[dict(tema=k[0], rua=k[1], n=g["n"], de=g["de"], ate=g["ate"], aut=dict(g["aut"])) for k, g in top],
        indT=dict(ind_t), infT=dict(inf_t), repGrupos=len(rep), repPedidos=sum(g["n"] for g in rep),
        indTotal=sum(ind_t.values()), infTotal=sum(inf_t.values()))

    props = {n: {c: props[n][c] for c in CLASSES if props[n][c]} for n in props}
    return props, pedidos, total_props


def agregar(con, minimo_sessoes=None):
    lista = vereadores()
    nomes = [v["nome"] for v in lista]
    hoje = date.today().isoformat()
    seed = ler(BRUTOS / "base_v1.json", {})
    minimo = minimo_sessoes if minimo_sessoes is not None else seed.get("camara", {}).get("sessoes", 0)

    sess = con.execute("SELECT data, tipo, numero, ano FROM sessoes WHERE tipo IN (?,?) AND data >= '2025-01-01' AND data <= ? "
                       "AND votacao_coletada = 1 ORDER BY data", (*PLENARIO, hoje + " 23:59")).fetchall()
    if len(sess) < minimo:
        print(f"Votações e presença NÃO atualizadas: só {len(sess)} sessões com votação lida (o site já tem {minimo}). "
              "Rode o RODAR.bat para completar. Proposições e pedidos foram atualizados.")
        if not con.execute("SELECT COUNT(*) FROM proposicoes").fetchone()[0]:
            return None
        anterior = ler(BRUTOS / "coletado.json", {}) or {}
        props, pedidos, total_props = proposicoes(con, lista, nomes)
        anterior.update(atualizadoProps=date.today().strftime("%d/%m/%Y"), props=props, pedidos=pedidos)
        anterior.setdefault("camara", {})["propsTotal"] = total_props
        gravar(BRUTOS / "coletado.json", anterior)
        return None

    atas = {(a, n): (d, t) for a, n, d, t in con.execute("SELECT ano, numero, data, texto FROM atas")}
    vot = con.execute("SELECT id, sessao_data, materia, ementa, autoria, resultado, tipo_votacao FROM votacoes "
                      "WHERE sessao_data >= '2025-01-01' ORDER BY sessao_data, data_votacao").fetchall()
    votos = collections.defaultdict(dict)
    for vid, quem, voto in con.execute("SELECT votacao_id, vereador, voto FROM votos"):
        n = identificar(quem, lista)
        if n:
            votos[vid][n] = up(voto)

    # sessões sem ata (só ordinárias têm ata publicada nessa página)
    sem_ata = [dict(num=n, ano=a, data=d[:10]) for d, t, n, a in sess if t == "Sessão Ordinária" and n and (a, n) not in atas]
    sem_ata_datas = {x["data"] for x in sem_ata}

    # votos e votações divididas
    agg = {n: dict(fav=0, con=0, conExec=0, nr=0, abs=0, pres=0, sessoes=0, semVoto=0) for n in nomes}
    votou = collections.defaultdict(set)
    div, rej, nominais, vot_sem_ata = [], 0, 0, 0
    for vid, sdata, materia, ementa, autoria, resultado, tipo in vot:
        vs = votos.get(vid, {})
        if not vs:
            continue
        nominais += 1
        d = sdata[:10]
        vot_sem_ata += d in sem_ata_datas
        exec_ = bool(re.search(r"EXECUTIVO|PREFEIT", up(autoria)))
        for n, v in vs.items():
            if v.startswith("FAVOR"):
                agg[n]["fav"] += 1
            elif v.startswith("CONTR"):
                agg[n]["con"] += 1
                agg[n]["conExec"] += exec_
            elif v.startswith("NAO REG") or v.startswith("AUSENTE"):
                agg[n]["nr"] += 1
            elif v.startswith("ABST"):
                agg[n]["abs"] += 1
            elif v.startswith("PRESID"):
                agg[n]["pres"] += 1
            if not (v.startswith("NAO REG") or v.startswith("AUSENTE")):
                votou[d].add(n)
        contra = [n for n in nomes if vs.get(n, "").startswith("CONTR")]
        rejeitada = up(resultado).startswith("REJEIT")
        rej += rejeitada
        if contra or rejeitada:
            fav = sum(1 for x in vs.values() if x.startswith("FAVOR"))
            res = ("Rejeitado" if rejeitada else "Aprovado") + f" · {fav} a favor · contra {len(contra)}"
            div.append(dict(data=d, materia=materia.strip(), ementa=(ementa or "").strip().rstrip(".").capitalize()
                            if (ementa or "").isupper() else (ementa or "").strip(),
                            autoria="Prefeitura" if exec_ else (autoria or "").strip(), rejeitada=rejeitada,
                            resultado=res, contra=contra, semAta=d in sem_ata_datas))
    contra_idx = {n: [i for i, x in enumerate(div) if n in x["contra"]] for n in nomes}

    # presença
    pres = {n: dict(pres=0, just=0, semJust=0, semAta=0, licenca=0) for n in nomes}
    for d, t, num, ano in sess:
        d = d[:10]
        ata = atas.get((ano, num)) if t == "Sessão Ordinária" else None
        aus = ausencias(ata[1], lista) if ata else {}
        for n in nomes:
            agg[n]["sessoes"] += 1
            if n not in votou[d]:
                agg[n]["semVoto"] += 1
            if n in aus:
                pres[n][aus[n]] += 1
            elif ata or n in votou[d]:
                pres[n]["pres"] += 1
            else:
                pres[n]["semAta"] += 1

    props, pedidos, total_props = proposicoes(con, lista, nomes)

    out = dict(
        atualizado=date.today().strftime("%d/%m/%Y"),
        props=props,
        votos=agg, contra=contra_idx, divididas=div, atas=sem_ata, presenca=pres, pedidos=pedidos,
        camara=dict(votacoes=nominais, sessoes=len(sess), rejeitadas=rej, divididas=len(div),
                    rejSemAta=sum(1 for x in div if x["rejeitada"] and x["semAta"]),
                    divSemAta=sum(1 for x in div if x["semAta"]), votSemAta=vot_sem_ata, propsTotal=total_props))
    gravar(BRUTOS / "coletado.json", out)
    print(f"Agregado: {nominais} votações, {len(sess)} sessões, {len(div)} divididas, {len(sem_ata)} sem ata, {total_props} proposições")
    return out
