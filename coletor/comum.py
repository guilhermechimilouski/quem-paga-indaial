import json
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
BRUTOS = DADOS / "brutos"
MANUAL = DADOS / "manual"
SITE = RAIZ / "docs"
DB = DADOS / "radar.db"


def up(s):
    return unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().upper().strip()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", up(s).lower()).strip("-")


def ler(nome, padrao=None):
    p = nome if isinstance(nome, Path) else DADOS / nome
    if not p.exists():
        return padrao
    return json.loads(p.read_text(encoding="utf-8"))


def gravar(nome, obj, compacto=False):
    p = nome if isinstance(nome, Path) else DADOS / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) if compacto else json.dumps(obj, ensure_ascii=False, indent=1)
    p.write_text(txt, encoding="utf-8")


def vereadores():
    return ler("vereadores.json")


def identificar(texto, lista=None):
    """Devolve o nome oficial do vereador citado em `texto` (ou None)."""
    t = up(texto)
    for v in lista or vereadores():
        if re.search(up(v["token"]).replace("\\B", "\\b"), t):
            return v["nome"]
    return None
