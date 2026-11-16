import re
from .comum import up

TEMAS = [
    ("Buracos, asfalto e manutenção de ruas", r"BURAC|ASFALT|PAVIMENT|LAJOT|PATROL|CASCALH|MACADAM|ENSAIBR|TAPA|RECAPE|MANUTENCAO D[AEO]S? (RUA|VIA|ESTRADA)|ESTRADA|LEITO DA RUA|PEDRA BRITA|BRITA"),
    ("Drenagem e bueiros", r"BUEIR|BOCA DE LOBO|DRENAG|TUBULA|GALERIA|ALAGA|VALA|CANALIZ|ESCOAMENTO|ARROIO|RIBEIR"),
    ("Roçada e limpeza", r"ROCAD|ROCAG|LIMPEZA|CAPINA|LIXO|ENTULHO|VARRI"),
    ("Poda e árvores", r"PODA|ARVORE|GALHO|SUPRESSAO VEGETAL|CORTE DE ARV"),
    ("Iluminação pública", r"ILUMINA|LAMPAD|POSTE|LUMINAR|REFLETOR"),
    ("Trânsito e sinalização", r"SINALIZ|FAIXA|LOMBAD|REDUTOR|SEMAFOR|PLACA|TRANSITO|ESTACIONAMENTO|VELOCIDADE|PINTURA|RADAR|ROTATORIA|MAO UNICA"),
    ("Calçadas e acessibilidade", r"CALCAD|PASSEIO|ACESSIBIL|RAMPA|PASSARELA|CICLOV|CICLOFAIXA"),
    ("Água e esgoto", r"AGUA|ESGOT|SAMAE|HIDRANTE|SANEAMENTO|CAIXA DE INSPEC"),
    ("Transporte coletivo", r"ONIBUS|TRANSPORTE COLETIVO|TRANSPORTE ESCOLAR|PONTO DE ONIBUS|ABRIGO|PARADA"),
    ("Saúde", r"SAUDE|POSTO|UBS|ESF|MEDIC|HOSPITAL|VACIN|CONSULTA|EXAME|FARMAC|DENGUE|AMBULANC"),
    ("Educação", r"ESCOLA|CRECHE|CEI|EDUCAC|ALUNO|PROFESSOR|ENSINO|MERENDA"),
    ("Praças, esporte e lazer", r"PRACA|PARQUE|ACADEMIA|QUADRA|GINASIO|CAMPO|PLAYGROUND|PARQUINHO|ESPORT|LAZER"),
    ("Segurança", r"SEGURANCA|POLICIA|GUARDA|VIGILANC|CAMERA|VIDEOMONIT|DEFESA CIVIL"),
    ("Animais", r"ANIMA|CAES|CACHORR|GATO|CASTRAC|ZOONOSE"),
    ("Contratos e gastos", r"CONTRATO|LICITA|EMPENH|GASTO|DESPESA|PAGAMENT|CONVENIO|ADITIVO|VALOR"),
    ("Servidores e gestão", r"SERVIDOR|CONCURSO|CARGO|FUNCIONARI|COMISSIONAD|ESTAGIAR"),
    ("Obras e reformas", r"OBRA|REFORMA|CONSTRUC|AMPLIAC|PONTE|PONTILH|MURO|CONTENC"),
]
_TEMAS = [(t, re.compile(p)) for t, p in TEMAS]

ABREV = {"MAL": "MARECHAL", "DR": "DOUTOR", "PROF": "PROFESSOR", "STA": "SANTA", "STO": "SANTO",
         "GAL": "GENERAL", "CEL": "CORONEL", "PE": "PADRE", "VER": "VEREADOR", "PRES": "PRESIDENTE",
         "DEP": "DEPUTADO", "SEN": "SENADOR", "GOV": "GOVERNADOR", "ENG": "ENGENHEIRO", "CAP": "CAPITAO"}


def tema(texto):
    t = up(texto)
    for nome, rx in _TEMAS:
        if rx.search(t):
            return nome
    return "Outros"


def rua(texto):
    t = up(texto)
    t = re.sub(r"\b([A-Z]{1,4})\.\s*", lambda m: ABREV.get(m.group(1), m.group(1)) + " ", t)
    m = re.search(r"\b(RUA|AVENIDA|AV|ESTRADA|SERVIDAO|TRAVESSA|ALAMEDA|RODOVIA)\s+([A-Z0-9][A-Z0-9 ]{2,60}?)(?=,|;|\.|\bN[OU]?\s*\d|\bNO BAIRRO|\bBAIRRO|\bPROXIM|\bEM FRENTE|\bESQUINA|\bENTRE|\bJUNTO|\bNAS\b|\bNA ALTURA|\bAO LADO|\bDEFRONTE|\bATE\b|\bE RUA|$)", t)
    if not m:
        return None
    tipo = "AVENIDA" if m.group(1) == "AV" else m.group(1)
    nome = re.sub(r"\s+", " ", m.group(2)).strip()
    nome = " ".join(ABREV.get(w, w) for w in nome.split())
    return f"{tipo} {nome}".lower()


def tipo_prop(tipo, ementa):
    """Classe usada no site: indicacao, mocao_homenagem, mocao_posicionamento, pl_rua,
    pl_homenagem, pl_substantivo, req_info, req_outros, outros."""
    tp, e = up(tipo), up(ementa)
    if "INDICA" in tp:
        return "indicacao"
    if "MOC" in tp:
        return "mocao_homenagem" if re.search(r"APLAUSO|CONGRATUL|HOMENAG|PESAR|RECONHECIMENTO|PARABEN|LOUVOR", e) else "mocao_posicionamento"
    if "REQUERIMENTO" in tp:
        return "req_info" if re.search(r"INFORMAC|ENCAMINH|CÓPIA|COPIA|ESCLARECIMENT|RELACAO|RELATORIO|DADOS", e) else "req_outros"
    if "PROJETO" in tp and ("LEI" in tp or "LEI" in e):
        if re.search(r"DENOMINA|DA NOME|DENOMINACAO|LOGRADOURO", e):
            return "pl_rua"
        if re.search(r"UTILIDADE PUBLICA|CIDADAO|CIDADA HONOR|TITULO|INSTITUI O DIA|INSTITUI A SEMANA|CALENDARIO OFICIAL|DATA COMEMORATIVA|MEDALHA|COMENDA", e):
            return "pl_homenagem"
        return "pl_substantivo"
    return "outros"
