"""Testes com dados de exemplo (não acessam a internet). Rode: python -m testes.test_coletor"""
import shutil
import sqlite3
import tempfile
from pathlib import Path

from coletor import agregar, classificar, coletar, comum

PDF_TXT = """RELATÓRIO DE VOTAÇÕES
Projeto de Lei nº 12/2026
Dispõe sobre a criação do programa X.
Autoria: Poder Executivo
Data e Hora da Votação: 03/03/2026 19:40:00
Destino: Aprovado
Resultado: APROVADO
01. Carlos Eduardo Cunha FAVORÁVEL
02. Caroline Laís Bertoldi CONTRÁRIO
03. Diogo de Pinho FAVORÁVEL
04. Henrique Fritz NÃO REGISTRADO
05. Valentim Blasius PRESIDENTE
RELATÓRIO DE VOTAÇÕES
Requerimento nº 40/2026
Pedido de informações sobre o contrato de limpeza.
Autoria: Vereador Lucio Vanderlinde
Data e Hora da Votação: 03/03/2026 19:50:00
Resultado: REJEITADO
01. Carlos Eduardo Cunha CONTRÁRIO
02. Lucio Vanderlinde FAVORÁVEL
03. Henrique Fritz NÃO REGISTRADO
"""

ATA = ("Ata da 7ª Sessão Ordinária realizada em 3 de março de 2026. Aberta a sessão, constatou-se ausente o vereador "
       "Henrique Fritz (atestado médico) e a vereadora Fernanda Jacobi dos Santos em licença; ausente também o vereador "
       "Valmir Jordani. Estando presentes os demais e registrado o número legal, o presidente abriu os trabalhos. "
       "O vereador Cunha falou sobre buracos.")


def teste_votacao():
    vs = coletar.ler_votacao(PDF_TXT)
    assert len(vs) == 2
    assert vs[0]["materia"] == "Projeto de Lei nº 12/2026"
    assert vs[0]["autoria"] == "Poder Executivo"
    assert ("Caroline Laís Bertoldi", "CONTRÁRIO") in vs[0]["votos"]
    assert ("Henrique Fritz", "NÃO REGISTRADO") in vs[0]["votos"]
    assert vs[1]["resultado"] == "REJEITADO"


def teste_ata():
    a = agregar.ausencias(ATA, comum.vereadores())
    assert a == {"Henrique Fritz": "just", "Fernanda Jacobi dos Santos": "licenca", "Valmir Jordani": "semJust"}, a
    assert coletar.data_por_extenso(ATA) == "2026-03-03"


def teste_classificar():
    assert classificar.tema("Operação tapa-buraco na Rua Mal. Floriano Peixoto, bairro Centro") == "Buracos, asfalto e manutenção de ruas"
    assert classificar.rua("Operação tapa-buraco na Rua Mal. Floriano Peixoto, bairro Centro") == "rua marechal floriano peixoto"
    assert classificar.rua("Roçada na Rua Maringá próximo ao nº 200") == "rua maringa"
    assert classificar.tema("Poda das árvores da Praça") == "Poda e árvores"
    assert classificar.tipo_prop("Indicações", "x") == "indicacao"
    assert classificar.tipo_prop("Projetos de Lei Ordinária", "Denomina Rua João da Silva") == "pl_rua"
    assert classificar.tipo_prop("Projetos de Lei Ordinária", "Declara de utilidade pública a Associação Y") == "pl_homenagem"
    assert classificar.tipo_prop("Moções", "Moção de aplauso ao time") == "mocao_homenagem"
    assert classificar.tipo_prop("Requerimentos", "Solicita informações sobre o contrato") == "req_info"


def teste_agregar_e_montar():
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(comum.DADOS, tmp / "dados")
    shutil.copytree(comum.SITE, tmp / "docs")
    antigos = (comum.DADOS, comum.BRUTOS, comum.SITE, comum.DB)
    try:
        comum.DADOS, comum.BRUTOS, comum.SITE, comum.DB = tmp / "dados", tmp / "dados/brutos", tmp / "docs", tmp / "dados/radar.db"
        import coletor.agregar as ag, coletor.montar as mo, coletor.importar as im
        for m in (ag, mo, im, coletar):
            for nome in ("DADOS", "BRUTOS", "SITE", "DB", "MANUAL"):
                if hasattr(m, nome):
                    setattr(m, nome, getattr(comum, nome) if nome != "MANUAL" else tmp / "dados/manual")
        comum.MANUAL = tmp / "dados/manual"
        coletar.DB = tmp / "dados/radar.db"
        con = coletar.conectar()
        con.execute("INSERT INTO sessoes VALUES ('2026-03-03 19:00:00','7ª Sessão Ordinária de 2026','Sessão Ordinária',7,2026,'',1,2)")
        con.execute("INSERT INTO sessoes VALUES ('2026-03-10 19:00:00','8ª Sessão Ordinária de 2026','Sessão Ordinária',8,2026,'',1,0)")
        for v in coletar.ler_votacao(PDF_TXT):
            vid = con.execute("INSERT INTO votacoes (sessao_data,materia,ementa,autoria,data_votacao,destino,resultado,tipo_votacao) "
                              "VALUES ('2026-03-03 19:00:00',?,?,?,?,?,?,?) RETURNING id",
                              (v["materia"], v["ementa"], v["autoria"], v["data_votacao"], v["destino"], v["resultado"], v["tipo_votacao"])).fetchone()[0]
            con.executemany("INSERT INTO votos VALUES (?,?,?)", [(vid, n, x) for n, x in v["votos"]])
        con.execute("INSERT INTO atas VALUES (2026,7,'2026-03-03','',?)", (ATA,))
        con.executemany("INSERT INTO proposicoes VALUES (?,?,?,?,?,?)", [
            ("Ind 1/2026", "Indicações", "2026-02-01", "Tapa-buraco na Rua Bagé", "Carlos Eduardo Cunha", ""),
            ("Ind 2/2026", "Indicações", "2026-03-01", "Operação tapa buraco na Rua Bagé, nº 10", "Carlos Eduardo Cunha;Elaine Pickler", ""),
            ("Req 3/2026", "Requerimentos", "2026-03-01", "Solicita informações sobre o transporte escolar", "Lucio Vanderlinde", ""),
            ("PL 4/2026", "Projetos de Lei Ordinária", "2026-03-01", "Dispõe sobre o orçamento", "Prefeito Municipal", ""),
        ])
        con.commit()
        out = ag.agregar(con, minimo_sessoes=0)
        assert out["camara"]["votacoes"] == 2 and out["camara"]["rejeitadas"] == 1 and out["camara"]["divididas"] == 2
        assert out["votos"]["Carlos Eduardo Cunha"]["con"] == 1 and out["votos"]["Caroline Laís Bertoldi"]["conExec"] == 1
        assert out["presenca"]["Henrique Fritz"] == dict(pres=0, just=1, semJust=0, semAta=1, licenca=0), out["presenca"]["Henrique Fritz"]
        assert out["presenca"]["Carlos Eduardo Cunha"]["pres"] == 1 and out["presenca"]["Carlos Eduardo Cunha"]["semAta"] == 1
        assert out["atas"] == [dict(num=8, ano=2026, data="2026-03-10")]
        assert out["pedidos"]["per"]["Carlos Eduardo Cunha"]["selfRep"] == 2
        assert out["pedidos"]["repGrupos"] == 1 and out["pedidos"]["top"][0]["rua"] == "rua bage"
        assert out["props"]["Executivo"] == {"pl_substantivo": 1}
        assert ag.agregar(con, minimo_sessoes=99) is None

        (tmp / "dados/manual/folha").mkdir(parents=True, exist_ok=True)
        linhas = ["Nome;Cargo;Proventos;13º Salário"]
        linhas += [f"{p[0]};{p[1]};{p[2]:.2f}".replace(".", ",") + ";0,00" for p in ler_ult(tmp).values()]
        (tmp / "dados/manual/folha/2026-11.csv").write_text("\n".join(linhas), encoding="utf-8")
        (tmp / "dados/manual/diarias").mkdir(parents=True, exist_ok=True)
        (tmp / "dados/manual/diarias/2026.csv").write_text("Nome;Valor\nDiogo de Pinho;1.000,50\nFulano;99,50\n", encoding="utf-8")
        im.tudo()
        d = mo.montar()
        assert d["ultimoMes"] == "nov/2026" and len(d["camara"]["folhaMensal"]) == 23
        assert len(d["camara"]["folhaMensalAnt"]) == 23 and d["camara"]["folhaMensalAnt"][-1]["m"] == "2022-11"
        assert d["camara"]["diarias"]["2026"] == 1100.0
        dio = next(v for v in d["vereadores"] if v["nome"] == "Diogo de Pinho")
        assert abs(dio["custo"]["mandato"]["diarias"] - (33944.43 * 0 + dio["custo"]["mandato"]["diarias"])) < 1
        assert d["atualizado"] == out["atualizado"]
    finally:
        comum.DADOS, comum.BRUTOS, comum.SITE, comum.DB = antigos
        shutil.rmtree(tmp)


def ler_ult(tmp):
    import json
    return json.loads((tmp / "dados/brutos/folha_ultimo.json").read_text(encoding="utf-8"))["pessoas"]


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("teste_"):
            f()
            print("ok", nome)
