"""Páginas estáticas para o Google: uma por vereador, sitemap e lista de links na página inicial.

Lê docs/data.json (gerado por montar.py) e escreve:
  docs/vereador/<slug>/index.html
  docs/sitemap.xml
  bloco de links entre <!--VEREADORES--> e <!--/VEREADORES--> em docs/index.html
"""
import html
import json
import re
from datetime import datetime

from . import comum

URL = "https://quempagaindaial.com.br"
NOME_SITE = "Quem paga, Indaial?"
AUTOR = "Guilherme Patrick Chimilouski Glatz"


def brl(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s


def brl0(v):
    return "R$ " + f"{round(v):,}".replace(",", ".")


def esc(s):
    return html.escape(str(s), quote=True)


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c") + "</script>"


def cargo(v):
    f = (v.get("funcao") or "").strip()
    return f"Vereador ({f})" if f and f.lower() != "vereador" else "Vereador"


def pagina(v, d):
    slug, nome = v["slug"], v["nome"]
    url = f"{URL}/vereador/{slug}/"
    man, mes = v["custo"]["mandato"], v["custo"]["mesAtual"]
    p, vt, pr = v["presenca"], v["votos"], v["props"]
    sessoes = p["pres"] + p["just"] + p["semJust"] + p["licenca"] + p["semAta"]
    titulo = f"Quanto ganha e quanto custa o vereador {nome} | Indaial"
    desc = (f"{nome} ({v['partido']}) custou {brl0(man['total'])} aos cofres de Indaial no mandato "
            f"({d['periodoFolha']}): salário, assessores, diárias e encargos. Veja presença, votos e pedidos, com fonte oficial.")
    ass = "".join(f"<li>{esc(a['nome'])}, {esc(a['cargo'])}: {brl(a['bruto'])}</li>" for a in mes["assessores"]) or "<li>Nenhum assessor na folha do mês.</li>"
    props = {"indicacao": "Indicações", "req_info": "Pedidos de informação", "pl_substantivo": "Projetos de lei (conteúdo)",
             "pl_rua": "Projetos de lei (nome de rua)", "pl_homenagem": "Projetos de lei (homenagem)",
             "mocao_homenagem": "Moções de homenagem", "mocao_posicionamento": "Moções de posicionamento",
             "req_outros": "Outros requerimentos", "outros": "Outros"}
    lp = "".join(f"<li>{rot}: {pr[k]}</li>" for k, rot in props.items() if pr.get(k))
    ld = [
        {"@context": "https://schema.org", "@type": "ProfilePage", "url": url, "name": titulo, "inLanguage": "pt-BR",
         "dateModified": datetime.now().strftime("%Y-%m-%d"),
         "mainEntity": {"@type": "Person", "name": nome, "jobTitle": cargo(v), "sameAs": [v["perfil"]],
                        "memberOf": {"@type": "GovernmentOrganization", "name": "Câmara Municipal de Indaial",
                                     "url": "https://www.camaraindaial.sc.gov.br"},
                        "affiliation": {"@type": "Organization", "name": v["partido"]}}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": NOME_SITE, "item": URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Vereadores", "item": URL + "/#vereadores"},
            {"@type": "ListItem", "position": 3, "name": nome, "item": url}]},
    ]
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="profile">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="{NOME_SITE}">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{URL}/og.png">
<meta property="og:image:alt" content="Quem paga, Indaial? Quanto custa cada vereador">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#b3121f">
{jsonld(ld)}
<style>
body{{margin:0;background:#f2f1ed;color:#15171c;font:16px/1.55 "IBM Plex Sans","Segoe UI",Roboto,sans-serif}}
.w{{max-width:760px;margin:0 auto;padding:20px}}
a{{color:#b3121f}}
.logo{{font:900 20px "Archivo",Arial,sans-serif;text-decoration:none;color:#15171c}}.logo span{{color:#b3121f}}
h1{{font:900 30px/1.15 "Archivo",Arial,sans-serif;margin:18px 0 6px}}
h2{{font:700 19px "Archivo",Arial,sans-serif;margin:26px 0 8px}}
.card{{background:#fff;border:1px solid #e1dfd9;border-radius:14px;padding:16px 18px;margin:12px 0}}
.big{{font:900 34px "Archivo",Arial,sans-serif;color:#b3121f}}
.mut{{color:#61656e;font-size:14px}}
.btn{{display:inline-block;background:#b3121f;color:#fff;text-decoration:none;padding:10px 16px;border-radius:10px;font-weight:600}}
ul{{padding-left:20px}}
</style>
</head>
<body>
<div class="w">
<a class="logo" href="/">Quem paga, <span>Indaial?</span></a>
<nav class="mut"><a href="/">Início</a> › <a href="/#vereadores">Vereadores</a> › {esc(nome)}</nav>
<h1>{esc(nome)}</h1>
<p class="mut">{esc(cargo(v))} · {esc(v['partido'])} · {v['votosEleicao']} votos em 2024 · <a href="{esc(v['perfil'])}" rel="nofollow">perfil oficial na Câmara</a></p>

<div class="card">
<div class="mut">Custo total no mandato ({esc(d['periodoFolha'])})</div>
<div class="big">{brl(man['total'])}</div>
<ul>
<li>Salário do vereador: {brl(man['subsidio'])}</li>
<li>Salários de assessores: {brl(man['assessores'])}</li>
<li>Diárias: {brl(man['diarias'])}</li>
<li>INSS pago pela Câmara (estimado em 20%): {brl(man['patronal'])}</li>
</ul>
</div>

<h2>Quanto custa em {esc(d['ultimoMes'])}</h2>
<div class="card">
<p>Salário do vereador: <b>{brl(mes['subsidio'])}</b></p>
<ul>{ass}</ul>
<p>Total do gabinete no mês: <b>{brl(mes['total'])}</b></p>
</div>

<h2>Presença</h2>
<div class="card">
<p>Presente em <b>{p['pres']}</b> de {sessoes} sessões. Faltas justificadas: {p['just']}. Faltas sem justificativa: {p['semJust']}. Licenças: {p['licenca']}. Sessões ainda sem ata: {p['semAta']}.</p>
</div>

<h2>Como vota</h2>
<div class="card">
<ul><li>A favor: <b>{vt['fav']}</b></li><li>Contra: <b>{vt['con']}</b> (contra projetos da Prefeitura: {vt['conExec']})</li>{f"<li>Abstenções: {vt['abs']}</li>" if vt['abs'] else ""}<li>Sem voto registrado: {vt['nr']}</li>{f"<li>Presidindo a sessão (não vota): {vt['pres']}</li>" if vt['pres'] else ""}</ul>
</div>

<h2>O que propõe</h2>
<div class="card"><ul>{lp}</ul></div>

<p><a class="btn" href="/#v-{esc(slug)}">Ver a página completa, com gráficos e cada votação</a></p>
<p class="mut">Dados atualizados em {esc(d['atualizado'])}. Fontes: Portal da Transparência da Câmara de Indaial, API de dados abertos, relatórios do painel de votação e atas oficiais. O site não dá nota nem apoia partido. Encontrou um erro? <a href="/#sobre">Veja como pedir correção</a>.</p>
</div>
</body>
</html>
"""


def sitemap(vs, hoje):
    urls = [(URL + "/", "1.0")] + [(f"{URL}/vereador/{v['slug']}/", "0.8") for v in vs]
    itens = "\n".join(f"  <url><loc>{u}</loc><lastmod>{hoje}</lastmod><changefreq>daily</changefreq><priority>{p}</priority></url>" for u, p in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{itens}\n</urlset>\n'


def links_home(vs):
    li = "".join(f'<li><a href="/vereador/{v["slug"]}/">{esc(v["nome"])} ({esc(v["partido"])})</a></li>' for v in sorted(vs, key=lambda x: x["nome"]))
    return f'<!--VEREADORES--><nav class="wrap seo-links" aria-label="Páginas dos vereadores"><b>Vereadores de Indaial:</b><ul>{li}</ul></nav><!--/VEREADORES-->'


def gerar():
    d = json.loads((comum.SITE / "data.json").read_text(encoding="utf-8"))
    vs = d["vereadores"]
    for v in vs:
        pasta = comum.SITE / "vereador" / v["slug"]
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "index.html").write_text(pagina(v, d), encoding="utf-8")
    hoje = datetime.now().strftime("%Y-%m-%d")
    (comum.SITE / "sitemap.xml").write_text(sitemap(vs, hoje), encoding="utf-8")
    idx = comum.SITE / "index.html"
    t = idx.read_text(encoding="utf-8")
    bloco = links_home(vs)
    if "<!--VEREADORES-->" in t:
        t = re.sub(r"<!--VEREADORES-->.*?<!--/VEREADORES-->", lambda _: bloco, t, flags=re.S)
    else:
        t = t.replace("<footer class=\"wrap\">", bloco + "\n<footer class=\"wrap\">", 1)
    idx.write_text(t, encoding="utf-8")
    print(f"Páginas de {len(vs)} vereadores, sitemap e links da página inicial gerados")
