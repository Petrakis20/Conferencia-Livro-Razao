from __future__ import annotations
import pandas as pd
import numpy as np
import re
import unicodedata
from typing import Dict, Tuple, Optional

BI_COLS = {
    "valor_contabil": ["valor contabil", "valor_contabil", "vl contabil", "vl. contabil", "valor", "vl"],
    "vl_icms": ["vl icms", "vl. icms", "valor icms", "icms"],
    "lanc_cont_valor": ["lanc. cont. vl. contabil", "lanc cont vl contabil", "lancamento cont vl contabil", "lanc_cont_vl_contabil", "lancamento", "lancamento contabil", "cod lancamento", "codigo lancamento"],
    "lanc_cont_icms": ["lanc. cont. vl. icms", "lanc cont vl icms", "lancamento cont vl icms", "lanc_cont_vl_icms", "lancamento icms", "cod lancamento icms", "codigo lancamento icms"],
}

RAZAO_COLS = {
    "lancamento": [
        "lancamento", "lançamento", "num lancamento", "numero lancamento", "no lancamento",
        "historico", "hist", "documento", "doc", "num doc", "numero documento", "comprovante",
        "lote", "ref", "referencia", "codigo", "codigo lanc", "cod lancamento", "codigo historico"
    ],
    "cd": ["c/d", "cd", "deb/cred", "debito/credito", "debito credito", "dc", "tipo"],
    "valor": ["valor", "vl", "vlr", "montante", "valor lancamento"]
}

def _strip_accents(s: str) -> str:
    return ''.join(ch for ch in unicodedata.normalize('NFKD', s) if not unicodedata.combining(ch))

def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}
    for c in df.columns:
        base = _strip_accents(str(c)).lower()
        base = re.sub(r'[^a-z0-9 ]+', ' ', base)
        base = re.sub(r'\s+', ' ', base).strip()
        mapping[c] = base
    df = df.rename(columns=mapping)
    return df

def coerce_numeric(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()

    def smart_to_float(x: str) -> float:
        if x is None or x == "" or x.lower() in {"nan", "none"}:
            return np.nan
        x = x.replace(" ", "")
        if x.count(",") == 1 and x.count(".") >= 1 and x.rfind(",") > x.rfind("."):
            x = x.replace(".", "").replace(",", ".")
        elif x.count(".") == 1 and x.count(",") >= 1 and x.rfind(".") > x.rfind(","):
            x = x.replace(",", "")
        elif x.count(",") > 0 and x.count(".") == 0:
            if x.count(",") == 1 and len(x.split(",")[-1]) in (1,2):
                x = x.replace(",", ".")
            else:
                x = x.replace(",", "")
        elif x.count(".") > 0 and x.count(",") == 0:
            parts = x.split(".")
            if len(parts[-1]) in (1,2):
                pass
            else:
                x = x.replace(".", "")
        try:
            return float(x)
        except:
            x = re.sub(r'[^0-9\.-]', '', x)
            try:
                return float(x)
            except:
                return np.nan

    return s.map(smart_to_float)

def clean_lancamento(series: pd.Series) -> pd.Series:
    def _fix(x):
        if pd.isna(x):
            return pd.NA
        s = str(x).strip()
        if s == "" or s.lower() in {"nan", "none"}:
            return pd.NA
        try:
            f = float(s)
            if abs(f - int(f)) < 1e-9:
                return str(int(f))
            else:
                return re.sub(r'\.0+$', '', f"{f}")
        except Exception:
            m = re.match(r'^\s*(\d+)\.0+\s*$', s)
            if m:
                return m.group(1)
            return s
    fixed = series.map(_fix)
    return fixed.astype("string")

def find_first_existing(df_cols: list[str], candidates: list[str]) -> Optional[str]:
    for cand in candidates:
        if cand in df_cols:
            return cand
    return None

def guess_candidates(df_cols: list[str], candidates: list[str]) -> list[str]:
    cols = []
    base = set(df_cols)
    for c in candidates:
        if c in base:
            cols.append(c)
    if cols:
        return cols
    for col in df_cols:
        for tok in ["lanc", "hist", "doc", "comp", "ref", "codigo"]:
            if tok in col:
                cols.append(col)
                break
    return list(dict.fromkeys(cols))

def load_bi(raw: pd.DataFrame, tipo: str) -> pd.DataFrame:
    df = normalize_cols(raw.copy())

    col_valor = find_first_existing(df.columns.tolist(), BI_COLS["valor_contabil"])
    col_vl_icms = find_first_existing(df.columns.tolist(), BI_COLS["vl_icms"])
    col_lanc_valor = find_first_existing(df.columns.tolist(), BI_COLS["lanc_cont_valor"])
    col_lanc_icms = find_first_existing(df.columns.tolist(), BI_COLS["lanc_cont_icms"])

    missing = [("Valor Contábil", col_valor), ("Vl. ICMS", col_vl_icms),
               ("Lanc. Cont. Vl. Contábil", col_lanc_valor), ("Lanc. Cont. Vl. ICMS", col_lanc_icms)]
    missing = [m[0] for m in missing if m[1] is None]
    if missing:
        raise ValueError(f"Colunas não encontradas no BI ({tipo}): {', '.join(missing)}")

    out = pd.DataFrame({
        "fonte": tipo.lower(),
        "lanc_valor": clean_lancamento(df[col_lanc_valor]),
        "valor_contabil": coerce_numeric(df[col_valor]),
        "lanc_icms": clean_lancamento(df[col_lanc_icms]),
        "valor_icms": coerce_numeric(df[col_vl_icms]),
    })
    return out

def load_razao(raw: pd.DataFrame, conta_rotulo: str,
               override_cols: Optional[dict] = None) -> pd.DataFrame:
    df = normalize_cols(raw.copy())
    cols = df.columns.tolist()

    if override_cols:
        c_lanc = override_cols.get("lancamento")
        c_cd   = override_cols.get("cd")
        c_val  = override_cols.get("valor")
    else:
        c_lanc = find_first_existing(cols, RAZAO_COLS["lancamento"])
        c_cd   = find_first_existing(cols, RAZAO_COLS["cd"])
        c_val  = find_first_existing(cols, RAZAO_COLS["valor"])

    missing = [("lancamento", c_lanc), ("cd", c_cd), ("valor", c_val)]
    missing = [m[0] for m in missing if m[1] is None]
    if missing:
        raise KeyError(" / ".join(missing))

    cd = df[c_cd].astype(str).str.strip().str.upper()
    val = coerce_numeric(df[c_val])
    sinalizado = np.where(cd.eq("C"), -abs(val), abs(val))
    out = pd.DataFrame({
        "conta": conta_rotulo,
        "lancamento": clean_lancamento(df[c_lanc]),
        "cd": cd,
        "valor_sinalizado": sinalizado,
    })
    return out

def aggregate_bi(bi_entradas: pd.DataFrame | None, bi_saidas: pd.DataFrame | None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    if bi_entradas is not None:
        frames.append(bi_entradas[["lanc_valor", "valor_contabil", "lanc_icms", "valor_icms"]].copy())
    if bi_saidas is not None:
        frames.append(bi_saidas[["lanc_valor", "valor_contabil", "lanc_icms", "valor_icms"]].copy())
    if not frames:
        return (pd.DataFrame(columns=["lancamento", "valor_bi"]), pd.DataFrame(columns=["lancamento", "valor_bi_icms"]))

    both = pd.concat(frames, ignore_index=True)

    # drop NaNs so they don't appear in comparison
    both_lanc_val = both.dropna(subset=["lanc_valor", "valor_contabil"]).copy()
    both_lanc_icms = both.dropna(subset=["lanc_icms", "valor_icms"]).copy()

    bi_valor = both_lanc_val.groupby("lanc_valor", dropna=False, as_index=False)["valor_contabil"].sum()
    bi_valor = bi_valor.rename(columns={"lanc_valor": "lancamento", "valor_contabil": "valor_bi"})
    bi_icms = both_lanc_icms.groupby("lanc_icms", dropna=False, as_index=False)["valor_icms"].sum()
    bi_icms = bi_icms.rename(columns={"lanc_icms": "lancamento", "valor_icms": "valor_bi_icms"})

    # remove lancamentos NA/empty after grouping
    bi_valor = bi_valor[bi_valor["lancamento"].notna() & (bi_valor["lancamento"].astype(str).str.len() > 0)]
    bi_icms = bi_icms[bi_icms["lancamento"].notna() & (bi_icms["lancamento"].astype(str).str.len() > 0)]

    return bi_valor, bi_icms

def aggregate_razao(razao: pd.DataFrame) -> pd.DataFrame:
    df = razao.dropna(subset=["lancamento", "valor_sinalizado"]).copy()
    agg = (df.groupby("lancamento", as_index=False)["valor_sinalizado"]
             .sum()
             .rename(columns={"valor_sinalizado": "valor_razao"}))
    agg = agg[agg["lancamento"].notna() & (agg["lancamento"].astype(str).str.len() > 0)]
    return agg

def compare_by_lancamento(agg_bi_valor: pd.DataFrame, agg_bi_icms: pd.DataFrame,
                          agg_razao: pd.DataFrame, modo: str) -> pd.DataFrame:
    if modo in ("icms", "st"):
        base_bi = agg_bi_icms.rename(columns={"valor_bi_icms": "valor_bi"})
    else:
        base_bi = agg_bi_valor.copy()

    df = pd.merge(base_bi, agg_razao, on="lancamento", how="outer")
    # drop NaN lancamentos entirely
    df = df[df["lancamento"].notna() & (df["lancamento"].astype(str).str.len() > 0)]
    df["valor_bi"] = df["valor_bi"].fillna(0.0)
    df["valor_razao"] = df["valor_razao"].fillna(0.0)
    df["diferenca"] = df["valor_bi"] - df["valor_razao"]
    return df.sort_values("lancamento", key=lambda s: s.astype(str))
