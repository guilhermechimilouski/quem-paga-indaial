"""
Quem paga, Indaial? - coletor

Uso (na pasta do projeto):
  python -m coletor.coletar atualizar     -> coleta tudo o que é novo, recalcula e gera docs/data.json
  python -m coletor.coletar api           -> vereadores, proposições e sessões (API de dados abertos)
  python -m coletor.coletar votacoes      -> PDFs de votação nominal das sessões
  python -m coletor.coletar atas          -> atas publicadas (presença e ausências)
  python -m coletor.coletar montar        -> só recalcula e gera docs/data.json com o que já existe
  python -m coletor.coletar importar      -> importa planilhas manuais (folha e diárias) de dados/manual/
  python -m coletor.coletar resumo        -> mostra o que já foi coletado

O token da API fica na variável de ambiente RADAR_TOKEN ou no arquivo .env (nunca no repositório).
"""
import argparse
import html
import io
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta

import requests

from .comum import DB, DADOS, RAIZ

BASE = "https://www.camaraindaial.sc.gov.br"
API = BASE + "/jsonweb/web-aplicativo.php"
VOTACAO_PDF = BASE + "/ciga/votacao_print_pdf.php"
PAUSA = 2.0
PLENARIO = ("Sessão Ordinária", "Sessão Extraordinária")
MESES = {m: i for i, m in enumerate(["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho",
                                     "agosto", "setembro", "outubro", "novembro", "dezembro"], 1)}


class Bloqueado(Exception):
    pass


def carregar_token():
    token = os.environ.get("RADAR_TOKEN")
    env = RAIZ / ".env"
    if not token and env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if linha.strip().startswith("RADAR_TOKEN="):
                token = linha.split("=", 1)[1].strip().strip('"').strip("'")
    if not token or token == "cole_seu_token_aqui":
        sys.exit("Token não encontrado. Crie o arquivo .env com RADAR_TOKEN=seu_token (ou o secret RADAR_TOKEN no GitHub).")
    return token


def http():
    s = requests.Session()
    s.headers["User-Agent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 QuemPagaIndaial/1.0")
    return s


def conectar():
    DADOS.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS vereadores (nome TEXT PRIMARY KEY, partido TEXT, funcao TEXT, link TEXT, atualizado_em TEXT);
        CREATE TABLE IF NOT EXISTS proposicoes (titulo TEXT PRIMARY KEY, tipo TEXT, data TEXT, ementa TEXT, autoria TEXT, link TEXT);
        CREATE TABLE IF NOT EXISTS sessoes (data TEXT PRIMARY KEY, titulo TEXT, tipo TEXT, numero INTEGER, ano INTEGER,
            link TEXT, votacao_coletada INTEGER DEFAULT 0, qtd_votacoes INTEGER);
        CREATE TABLE IF NOT EXISTS votacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, sessao_data TEXT, materia TEXT, ementa TEXT,
            autoria TEXT, data_votacao TEXT, destino TEXT, resultado TEXT, tipo_votacao TEXT,
            UNIQUE (sessao_data, materia, data_votacao, destino));
        CREATE TABLE IF NOT EXISTS votos (votacao_id INTEGER, vereador TEXT, voto TEXT, PRIMARY KEY (votacao_id, vereador));
        CREATE TABLE IF NOT EXISTS atas (ano INTEGER, numero INTEGER, data TEXT, link TEXT, texto TEXT, PRIMARY KEY (ano, numero));
    """)
    return con


def _bloqueio(texto):
    t = texto[:5000].lower()
    return "captcha" in t or "verifica" in t and "rob" in t or "turnstile" in t


def api_get(s, token, call, **params):
    r = s.get(API, params={"keysoft": token, "call": call, **params}, timeout=60)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError:
        if _bloqueio(r.text):
            raise Bloqueado("a API devolveu a página de verificação anti-robô")
        raise


def api_paginado(s, token, call, **params):
    pagina = 1
    while True:
        dados = api_get(s, token, call, pagina=pagina, **params)
        if not dados:
            return
        yield from dados
        pagina += 1
        time.sleep(PAUSA / 2)


def tipo_sessao(titulo):
    for t in ("Sessão Ordinária", "Sessão Extraordinária", "Sessão Solene", "Sessão Preparatória", "Audiência Pública", "Reunião"):
        if t.lower() in titulo.lower():
            return t
    return "Outro"


def coletar_api(con, s, token, desde):
    agora = datetime.now().isoformat(timespec="seconds")
    vs = api_get(s, token, "vereadores")
    con.executemany("INSERT OR REPLACE INTO vereadores VALUES (?,?,?,?,?)",
                    [(v.get("nome"), v.get("partido"), v.get("funcao"), v.get("link"), agora) for v in vs])
    print(f"Vereadores: {len(vs)}")
    for t in api_get(s, token, "proposicoes_tipos"):
        n = 0
        for p in api_paginado(s, token, "proposicoes", tipo=t["contract"]):
            if (p.get("data") or "") < desde:
                break
            con.execute("INSERT OR REPLACE INTO proposicoes VALUES (?,?,?,?,?,?)",
                        (p.get("titulo"), t["titulo"], p.get("data"), p.get("ementa"), p.get("autoria"), p.get("link")))
            n += 1
        con.commit()
        print(f"  {t['titulo']}: {n}")
    n = 0
    for p in api_paginado(s, token, "pautas"):
        data = p.get("data") or ""
        if data < desde:
            break
        titulo = p.get("titulo") or ""
        m = re.search(r"(\d+)\s*[ªa]", titulo)
        a = re.search(r"(20\d{2})", titulo) or re.search(r"(20\d{2})", data)
        con.execute("""INSERT INTO sessoes (data, titulo, tipo, numero, ano, link) VALUES (?,?,?,?,?,?)
                       ON CONFLICT(data) DO UPDATE SET titulo=excluded.titulo, tipo=excluded.tipo,
                       numero=excluded.numero, ano=excluded.ano, link=excluded.link""",
                    (data, titulo, tipo_sessao(titulo), int(m.group(1)) if m else None,
                     int(a.group(1)) if a else None, p.get("link")))
        n += 1
    con.commit()
    print(f"Sessões desde {desde}: {n}")


RE_VOTO = re.compile(r"^(\d{2})\.\s+(.+?)\s+(FAVOR[ÁA]VEL|CONTR[ÁA]RIO|N[ÃA]O REGISTRADO|PRESIDENTE|"
                     r"ABSTEN[ÇC][ÃA]O|AUSENTE|IMPEDIDO)\s*$", re.MULTILINE)


def _campo(padrao, texto):
    m = re.search(padrao, texto)
    return m.group(1).strip() if m else None


def ler_votacao(texto):
    saida = []
    for bloco in re.split(r"RELAT[ÓO]RIO DE VOTA[ÇC][ÕO]ES", texto)[1:]:
        linhas = [l.strip() for l in bloco.splitlines() if l.strip()]
        if not linhas:
            continue
        ementa = []
        for l in linhas[1:]:
            if l.startswith(("Autoria:", "Data e Hora")):
                break
            ementa.append(l)
        votos = [(n.strip(), v.strip()) for _, n, v in RE_VOTO.findall(bloco)]
        saida.append(dict(materia=linhas[0], ementa=" ".join(ementa) or None,
                          autoria=_campo(r"Autoria:\s*(.+)", bloco),
                          data_votacao=_campo(r"Data e Hora da Vota[çc][ãa]o:\s*([\d/]+\s+[\d:]+)", bloco),
                          destino=_campo(r"Destino:\s*(.+)", bloco),
                          resultado=_campo(r"Resultado:\s*(.+)", bloco),
                          tipo_votacao="Nominal" if votos else "Sem registro nominal", votos=votos))
    return saida


def baixar_pdf(s, data_sessao):
    r = s.get(VOTACAO_PDF, params={"data": data_sessao}, timeout=120)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        if _bloqueio(r.content.decode("latin-1")):
            raise Bloqueado("o site devolveu a verificação anti-robô em vez do PDF")
        return None
    return r.content


def texto_pdf(conteudo):
    import pdfplumber
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def coletar_votacoes(con, s, desde, refazer=False):
    recente = (datetime.now() - timedelta(days=21)).strftime("%Y-%m-%d")
    filtro = "" if refazer else "AND (votacao_coletada = 0 OR data >= ?)"
    params = [desde, *PLENARIO] + ([] if refazer else [recente])
    sessoes = con.execute(f"SELECT data, titulo FROM sessoes WHERE data >= ? AND tipo IN (?,?) {filtro} ORDER BY data",
                          params).fetchall()
    print(f"Sessões para ler votação: {len(sessoes)}")
    for i, (data, titulo) in enumerate(sessoes, 1):
        try:
            pdf = baixar_pdf(s, data)
        except requests.RequestException as e:
            print(f"  [{i}] {titulo}: erro de rede ({e}), fica para a próxima")
            continue
        vts = ler_votacao(texto_pdf(pdf)) if pdf else []
        for v in vts:
            vid = con.execute("""INSERT INTO votacoes (sessao_data, materia, ementa, autoria, data_votacao, destino, resultado, tipo_votacao)
                VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(sessao_data, materia, data_votacao, destino) DO UPDATE SET
                ementa=excluded.ementa, autoria=excluded.autoria, resultado=excluded.resultado, tipo_votacao=excluded.tipo_votacao
                RETURNING id""", (data, v["materia"], v["ementa"], v["autoria"], v["data_votacao"], v["destino"],
                                  v["resultado"], v["tipo_votacao"])).fetchone()[0]
            con.executemany("INSERT OR REPLACE INTO votos VALUES (?,?,?)", [(vid, n, x) for n, x in v["votos"]])
        con.execute("UPDATE sessoes SET votacao_coletada=1, qtd_votacoes=? WHERE data=?", (len(vts), data))
        con.commit()
        print(f"  [{i}/{len(sessoes)}] {titulo}: {len(vts)} votações")
        time.sleep(PAUSA)


def limpar_html(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", h)
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def data_por_extenso(t):
    from .comum import up
    m = re.search(r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(20\d{2})", up(t).lower())
    if m and m.group(2) in MESES:
        return f"{m.group(3)}-{MESES[m.group(2)]:02d}-{int(m.group(1)):02d}"
    m = re.search(r"(\d{2})/(\d{2})/(20\d{2})", t)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def coletar_atas(con, s, anos):
    for ano in anos:
        r = s.get(f"{BASE}/atas/sessao_ordinaria/{ano}", timeout=60)
        if _bloqueio(r.text):
            raise Bloqueado("a página de atas pediu verificação anti-robô")
        links = sorted(set(re.findall(r'href="([^"]*/atas/[^"]*(?:show|visualizar|ata)[^"]*)"', r.text, re.I)))
        conhecidas = {n for (n,) in con.execute("SELECT numero FROM atas WHERE ano=?", (ano,))}
        novas = 0
        for link in links:
            url = link if link.startswith("http") else BASE + "/" + link.lstrip("/")
            p = s.get(url, timeout=60)
            if _bloqueio(p.text):
                raise Bloqueado("a página da ata pediu verificação anti-robô")
            txt = limpar_html(p.text)
            m = re.search(r"(\d+)\s*[ªa]\s*Sess[ãa]o Ordin[áa]ria", txt, re.I)
            if not m or int(m.group(1)) in conhecidas:
                continue
            con.execute("INSERT OR REPLACE INTO atas VALUES (?,?,?,?,?)",
                        (ano, int(m.group(1)), data_por_extenso(txt), url, txt[:20000]))
            conhecidas.add(int(m.group(1)))
            novas += 1
            time.sleep(PAUSA)
        con.commit()
        print(f"Atas {ano}: {len(links)} links, {novas} novas")


def resumo(con):
    q = lambda sql, *p: con.execute(sql, p).fetchone()[0]
    print("Proposições:", q("SELECT COUNT(*) FROM proposicoes"))
    print("Sessões plenárias:", q("SELECT COUNT(*) FROM sessoes WHERE tipo IN (?,?)", *PLENARIO),
          "| com votação lida:", q("SELECT COUNT(*) FROM sessoes WHERE votacao_coletada=1"))
    print("Votações:", q("SELECT COUNT(*) FROM votacoes"), "| votos:", q("SELECT COUNT(*) FROM votos"))
    print("Atas lidas:", q("SELECT COUNT(*) FROM atas"))


def main():
    ap = argparse.ArgumentParser(description="Quem paga, Indaial? - coletor")
    ap.add_argument("comando", choices=["atualizar", "api", "votacoes", "atas", "montar", "importar", "resumo"])
    ap.add_argument("--desde", default="2025-01-01")
    ap.add_argument("--refazer", action="store_true")
    a = ap.parse_args()

    from . import agregar, importar, montar
    if a.comando == "importar":
        importar.tudo()
        return
    if a.comando == "montar":
        montar.montar()
        return
    con = conectar()
    s = http()
    bloqueado = None
    try:
        if a.comando in ("api", "atualizar"):
            coletar_api(con, s, carregar_token(), a.desde)
        if a.comando in ("votacoes", "atualizar"):
            coletar_votacoes(con, s, a.desde, a.refazer)
        if a.comando in ("atas", "atualizar"):
            coletar_atas(con, s, range(int(a.desde[:4]), datetime.now().year + 1))
    except Bloqueado as e:
        bloqueado = str(e)
        print(f"\nPARADO: {bloqueado}. O que já foi coletado está salvo.")
    if a.comando == "resumo":
        resumo(con)
    if a.comando == "atualizar":
        importar.tudo()
        if con.execute("SELECT COUNT(*) FROM votacoes").fetchone()[0]:
            agregar.agregar(con)
        montar.montar()
    con.close()
    if bloqueado:
        sys.exit(2)


if __name__ == "__main__":
    main()
