# sn_pdf.py
from __future__ import annotations
import io
import re
import unicodedata
import pandas as pd

# Leitor de PDF robusto: pypdf preferido; cai para PyPDF2 se necessário
try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    from PyPDF2 import PdfReader  # type: ignore

# Padrão de número no formato BR: 1.234,56
_SN_NUM = r'(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2}'


# ------------------------ Helpers ------------------------
def _norm(s: str) -> str:
    """Normaliza string: remove acentos e espaços; lowercase."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower().replace(" ", "")


def _split_glued_amounts(txt: str) -> str:
    """Insere espaço quando 2 valores monetários ficam colados (ex.: '22.813,2681.823,08')."""
    while True:
        new = re.sub(fr'({_SN_NUM})(?={_SN_NUM})', r'\1 ', txt)
        if new == txt:
            return new
        txt = new


def _to_number_br(s: str | None) -> float:
    """Converte número BR para float (aceita parênteses como negativo)."""
    if s is None:
        return 0.0
    s = str(s).strip()
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    s = s.replace(".", "").replace("\u00A0", "").replace(" ", "").replace(",", ".")
    try:
        v = float(s)
    except Exception:
        v = 0.0
    return -v if neg else v


def _fmt_br(v: float) -> str:
    """Formata float no padrão BR."""
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _open_reader(file_or_bytes) -> PdfReader:
    """Aceita UploadedFile/bytes/caminho e devolve um PdfReader."""
    if isinstance(file_or_bytes, (bytes, bytearray)):
        return PdfReader(io.BytesIO(file_or_bytes))
    if hasattr(file_or_bytes, "read"):
        raw = file_or_bytes.read()
        try:
            file_or_bytes.seek(0)
        except Exception:
            pass
        return PdfReader(io.BytesIO(raw))
    return PdfReader(file_or_bytes)


# ------------------------ API principal ------------------------
def parse_livro_icms_pdf(
    file_or_bytes,
    bloco: str | None = None,
    keep_numeric: bool = True,
) -> pd.DataFrame:
    """
    Lê ENTRADAS e SAÍDAS (ou só um bloco) e agrega por CFOP dentro do bloco.
    Agora captura TODAS as 5 colunas do livro:

      1) base_num      -> Base de Cálculo
      2) imposto_num   -> Imposto (Creditado/Debitado)
      3) isentas_num   -> Isentas ou não tributadas
      4) outras_num    -> Outras
      5) contab_num    -> Contábeis

    Retorna, por padrão, as colunas texto 'Imposto' e 'Valor Contábil' (compat)
    e, se keep_numeric=True, as 5 colunas numéricas acima (somadas).
    """
    reader = _open_reader(file_or_bytes)
    rows: list[dict] = []
    current_block: str | None = None

    for page in reader.pages:
        txt = page.extract_text() or ""
        if not txt:
            continue
        txt = _split_glued_amounts(txt)

        for line in txt.splitlines():
            line = line.strip()
            if not line:
                continue

            n = _norm(line)
            if "entradas" in n:
                current_block = "Entradas"
                continue
            if "saidas" in n or "saida" in n:
                current_block = "Saídas"
                continue
            if current_block is None:
                continue

            m = re.match(r"^\s*(\d{4})\b(.*)$", line)
            if not m:
                continue

            cfop, tail = m.group(1), m.group(2)
            nums = re.findall(_SN_NUM, tail)
            if len(nums) < 5:
                continue

            # Ordem do livro (ambos blocos):
            # 1) Base  2) Imposto  3) Isentas  4) Outras  5) Contábeis
            base_str, imp_str, isen_str, outr_str, cont_str = nums[:5]
            base_num  = _to_number_br(base_str)
            imp_num   = _to_number_br(imp_str)
            isen_num  = _to_number_br(isen_str)
            outr_num  = _to_number_br(outr_str)
            cont_num  = _to_number_br(cont_str)

            rows.append(
                {
                    "bloco": current_block,
                    "CFOP": cfop,
                    "Imposto": imp_str,           # compat (texto)
                    "Valor Contábil": cont_str,   # compat (texto)
                    "base_num": base_num,
                    "imposto_num": imp_num,
                    "isentas_num": isen_num,
                    "outras_num": outr_num,
                    "contab_num": cont_num,
                }
            )

    if not rows:
        cols = ["bloco", "CFOP", "Imposto", "Valor Contábil"]
        if keep_numeric:
            cols += ["base_num", "imposto_num", "isentas_num", "outras_num", "contab_num"]
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(rows)

    agg = (
        df.groupby(["bloco", "CFOP"], as_index=False)[
            ["base_num", "imposto_num", "isentas_num", "outras_num", "contab_num"]
        ].sum()
    )
    # Campos texto (compat): mantém "Imposto" e "Valor Contábil" como antes
    agg["Imposto"] = agg["imposto_num"].map(_fmt_br)
    agg["Valor Contábil"] = agg["contab_num"].map(_fmt_br)

    if bloco is not None:
        agg = agg[agg["bloco"].eq(bloco)].copy()

    cols = ["bloco", "CFOP", "Imposto", "Valor Contábil"]
    if keep_numeric:
        cols += ["base_num", "imposto_num", "isentas_num", "outras_num", "contab_num"]

    sort_cols = ["bloco", "CFOP"] if "bloco" in agg.columns else ["CFOP"]
    return agg[cols].sort_values(sort_cols).reset_index(drop=True)


# ------------------------ ICMS ST ------------------------
def parse_livro_icms_st_pdf(file_or_bytes, keep_numeric: bool = True) -> pd.DataFrame:
    """
    Lê o Livro de ICMS ST (Entradas/Saídas) e agrega por CFOP:
      - Entradas: usa 2º número (Imposto Creditado)
      - Saídas  : usa 3º número (Imposto Debitado)
    Retorna colunas:
      CFOP | Imposto Creditado ST | Imposto Debitado ST (strings BR)
      + numéricas (se keep_numeric=True):
        creditado_st_num, debitado_st_num, total_st_num (= creditado + debitado)
    """
    reader = _open_reader(file_or_bytes)
    credit = {}  # cfop -> soma créditos (entradas)
    debit  = {}  # cfop -> soma débitos (saídas)
    current_block: str | None = None

    for page in reader.pages:
        txt = page.extract_text() or ""
        if not txt:
            continue
        txt = _split_glued_amounts(txt)

        for line in txt.splitlines():
            line = line.strip()
            if not line:
                continue

            n = _norm(line)
            if "entradas" in n:
                current_block = "Entradas"; continue
            if "saidas" in n or "saida" in n:
                current_block = "Saídas";   continue
            if current_block is None:
                continue

            m = re.match(r"^\s*(\d{4})\b(.*)$", line)
            if not m:
                continue

            cfop, tail = m.group(1), m.group(2)
            nums = re.findall(_SN_NUM, tail)
            if not nums:
                continue

            if current_block == "Entradas":
                # 2º número = Imposto Creditado
                if len(nums) >= 2:
                    credit[cfop] = credit.get(cfop, 0.0) + _to_number_br(nums[1])
            else:  # Saídas
                # 3º número = Imposto Debitado (há uma coluna "Operações c/ Débito" entre eles)
                if len(nums) >= 3:
                    debit[cfop]  = debit.get(cfop, 0.0)  + _to_number_br(nums[2])

    import pandas as pd
    all_cfops = sorted(set(credit) | set(debit))
    rows = []
    for c in all_cfops:
        cnum = float(credit.get(c, 0.0))
        dnum = float(debit.get(c, 0.0))
        rows.append({
            "CFOP": c,
            "creditado_st_num": cnum,
            "debitado_st_num": dnum,
            "Imposto Creditado ST": _fmt_br(cnum),
            "Imposto Debitado ST": _fmt_br(dnum),
            "total_st_num": cnum + dnum,
        })
    cols = ["CFOP", "Imposto Creditado ST", "Imposto Debitado ST"]
    if keep_numeric:
        cols += ["creditado_st_num", "debitado_st_num", "total_st_num"]
    return pd.DataFrame(rows, columns=cols)


# ------------------------ Wrappers de compatibilidade ------------------------
def parse_livro_icms_pdf_entradas(file_or_bytes, keep_numeric: bool = True) -> pd.DataFrame:
    df = parse_livro_icms_pdf(file_or_bytes, bloco="Entradas", keep_numeric=True)
    out = df[["CFOP", "Valor Contábil", "Imposto",
              "imposto_num", "contab_num"]].copy()
    out.rename(
        columns={
            "Imposto": "Imposto Creditado",
            "imposto_num": "Imposto Creditado (num)",
            "contab_num": "Valor Contábil (num)",
        },
        inplace=True,
    )
    if not keep_numeric:
        out = out[["CFOP", "Valor Contábil", "Imposto Creditado"]]
    return out


def parse_livro_icms_pdf_saidas(file_or_bytes, keep_numeric: bool = True) -> pd.DataFrame:
    df = parse_livro_icms_pdf(file_or_bytes, bloco="Saídas", keep_numeric=True)
    out = df[["CFOP", "base_num", "isentas_num"]].copy()
    out.rename(
        columns={
            "base_num": "Valor Contábil (num)",
            "isentas_num": "Imposto Debitado (num)",
        },
        inplace=True,
    )
    # monta também as colunas texto para exibição
    out["Valor Contábil"] = out["Valor Contábil (num)"].map(_fmt_br)
    out["Imposto Debitado"] = out["Imposto Debitado (num)"].map(_fmt_br)

    # ordena & organiza colunas
    cols = ["CFOP", "Valor Contábil", "Imposto Debitado"]
    if keep_numeric:
        cols += ["Valor Contábil (num)", "Imposto Debitado (num)"]
    out = out[cols].sort_values("CFOP").reset_index(drop=True)
    return out
