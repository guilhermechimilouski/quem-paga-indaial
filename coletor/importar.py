"""Importa as planilhas exportadas à mão do Portal da Transparência (que bloqueia robôs).

dados/manual/folha/AAAA-MM.csv    folha de um mês: colunas Nome, Cargo, Proventos e 13º (o 13º é opcional)
dados/manual/diarias/AAAA.csv     diárias do ano inteiro: colunas Nome e Valor

Aceita separador ; ou , e números no formato 1.234,56. Arquivos já importados são reimportados sem duplicar.
"""
import csv
import io
import re

from .comum import BRUTOS, MANUAL, gravar, ler, up


def numero(s):
    s = (s or "").strip().replace("R$", "").replace(" ", "")
    if not s:
        return 0.0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def ler_csv(caminho):
    bruto = caminho.read_bytes()
    for cod in ("utf-8-sig", "latin-1"):
        try:
            txt = bruto.decode(cod)
            break
        except UnicodeDecodeError:
            continue
    sep = ";" if txt.count(";") >= txt.count(",") else ","
    linhas = list(csv.reader(io.StringIO(txt), delimiter=sep))
    cab = [up(c) for c in linhas[0]]
    return cab, linhas[1:]


def coluna(cab, *opcoes, obrigatoria=True):
    for i, c in enumerate(cab):
        if any(re.search(o, c) for o in opcoes):
            return i
    if obrigatoria:
        raise SystemExit(f"Coluna não encontrada ({' / '.join(opcoes)}). Cabeçalho lido: {cab}")
    return None


def importar_folha():
    arquivos = sorted((MANUAL / "folha").glob("*.csv"))
    if not arquivos:
        return
    fa = ler(BRUTOS / "folha_agg.json")
    gab = ler("gabinetes.json")
    ult = None
    for arq in arquivos:
        m = re.match(r"(20\d{2})-(\d{2})", arq.stem)
        if not m:
            print(f"Ignorado (nome deve ser AAAA-MM.csv): {arq.name}")
            continue
        mes = f"{m.group(2)}/{m.group(1)}"
        cab, linhas = ler_csv(arq)
        iN, iC = coluna(cab, r"^NOME", r"SERVIDOR", r"UNINOMERAZAO"), coluna(cab, r"CARGO", r"CARDESCRICAO")
        iP = coluna(cab, r"PROVENTO", r"BRUTO", r"REMUNERACAO")
        iD = coluna(cab, r"13|DECIMO", obrigatoria=False)
        pessoas = {}
        for l in linhas:
            if len(l) <= max(iN, iC, iP) or not l[iN].strip():
                continue
            br = numero(l[iP]) + (numero(l[iD]) if iD is not None and iD < len(l) else 0)
            k = up(l[iN])
            nome, cargo, v = pessoas.get(k, [l[iN].strip(), l[iC].strip(), 0.0])
            pessoas[k] = [nome, cargo, round(v + br, 2)]
        if mes not in fa["meses"] and mes[3:] + mes[:2] >= "202501":
            fa["meses"].append(mes)
            fa["meses"].sort(key=lambda x: x[3:] + x[:2])
        fa["tot"][mes] = [len(pessoas), round(sum(p[2] for p in pessoas.values()), 2)]
        if mes in fa["meses"]:
            i = fa["meses"].index(mes)
            for vk, ass in gab.items():
                ponto = [pessoas.get(vk, [0, 0, 0.0])[2], round(sum(pessoas.get(a, [0, 0, 0.0])[2] for a in ass), 2)]
                serie = fa["v"][vk]["s"]
                if i < len(serie):
                    serie[i] = ponto
                else:
                    serie.insert(i, ponto)
        if ult is None or mes[3:] + mes[:2] > ult[0][3:] + ult[0][:2]:
            ult = (mes, pessoas)
        print(f"Folha {mes}: {len(pessoas)} pessoas, R$ {fa['tot'][mes][1]:,.2f}")
    for f in fa["v"].values():
        f["sub"] = round(sum(s[0] for s in f["s"]), 2)
        f["ass"] = round(sum(s[1] for s in f["s"]), 2)
    gravar(BRUTOS / "folha_agg.json", fa)
    atual = ler(BRUTOS / "folha_ultimo.json")
    if ult and ult[0][3:] + ult[0][:2] >= atual["mes"][3:] + atual["mes"][:2]:
        gravar(BRUTOS / "folha_ultimo.json", dict(mes=ult[0], pessoas=ult[1]))


def importar_diarias():
    arquivos = sorted((MANUAL / "diarias").glob("*.csv"))
    if not arquivos:
        return
    hist = ler(BRUTOS / "diarias_hist.json")
    porv = ler(BRUTOS / "diarias_vereador.json")
    for arq in arquivos:
        ano = arq.stem[:4]
        cab, linhas = ler_csv(arq)
        iN, iV = coluna(cab, r"^NOME", r"FAVORECIDO", r"SERVIDOR", r"CREDOR"), coluna(cab, r"VALOR", r"TOTAL")
        soma, por = 0.0, {}
        for l in linhas:
            if len(l) <= max(iN, iV) or not l[iN].strip():
                continue
            v = numero(l[iV])
            soma += v
            por[up(l[iN])] = por.get(up(l[iN]), 0) + v
        hist[ano] = round(soma, 2)
        for k in porv:
            porv[k][ano] = round(por.get(k, 0.0), 2)
        print(f"Diárias {ano}: R$ {soma:,.2f}")
    gravar(BRUTOS / "diarias_hist.json", hist)
    gravar(BRUTOS / "diarias_vereador.json", porv)


def tudo():
    importar_folha()
    importar_diarias()
