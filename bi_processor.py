"""
Módulo para processamento de arquivos BI (Entrada/Saída/Serviços).
Responsável por carregar, limpar e processar dados do Business Intelligence.
"""

import io
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from utils import (
    clean_code_main, is_empty_code_main, to_number_br_main,
    norm_text_main, read_excel_best_main, EMPTY_TOKENS_MAIN
)


# =============================================================================
# Constantes para BI
# =============================================================================
REQUIRED_COLS_DISPLAY = [
    "CFOP",
    "Lanc. Cont. Vl. Contábil",
    "Lanc. Cont. Vl. ICMS",
    "Lanc. Cont. Vl. Subst. Trib.",
    "Lanc. Cont. Vl. IPI",
]

OPTIONAL_VALUE_COLS = [
    "Valor Contábil",
    "Vl. ICMS",
    "Vl. ST",
    "Vl. IPI",
    "Cancelada",
]

INTERNAL_KEYS = {
    "CFOP": "CFOP",
    "Lanc. Cont. Vl. Contábil": "contabil",
    "Lanc. Cont. Vl. ICMS": "icms",
    "Lanc. Cont. Vl. Subst. Trib.": "icms_subst",
    "Lanc. Cont. Vl. IPI": "ipi",
}

INTERNAL_VALUE_KEYS = {
    "Valor Contábil": "valor_contabil",
    "Vl. ICMS": "vl_icms",
    "Vl. ST": "vl_st",
    "Vl. IPI": "vl_ipi",
    "Cancelada": "cancelada",
}

SERV_COLS = [
    ("Lanc Cont. Valor Documento", ["Valor Documento"], "doc"),
    ("Lanc.Cont.Vl.Cofins",        ["Vl. Cofins"],     "cofins"),
    ("Lanc.Cont.Vl.PIS",           ["Vl. PIS"],        "pis"),
    ("Lanc Cont. Vl. ISS",         ["Vl. ISS"],        "iss"),
    ("Lanc Cont. Vl. ISS Ret.",    ["Vl. ISS Ret.","Vl ISS Ret"], "iss_ret"),
    ("Lanc Cont. Vl. IRRF",        ["Vl. IRRF","Vl IRRF"],        "irrf"),
    ("Lanc Cont. Vl. PIS Ret.",    ["Vl. PIS Ret.","Vl PIS Ret"], "pis_ret"),
    ("Lanc Cont. Vl. COFINS Ret.", ["Vl. COFINS Ret.","Vl COFINS Ret"], "cofins_ret"),
    ("Lanc Cont. Vl. INSS Ret.",   ["Vl. INSS Ret.","Vl INSS Ret"], "inss_ret"),
    ("Lanc Cont. Vl. CSLL Ret.",   ["Vl. CSLL Ret.","Vl CSLL Ret"], "csll_ret"),
]


# =============================================================================
# Funções de Leitura de Arquivos
# =============================================================================
def _read_excel_first_sheet(data: bytes, engine: str) -> Optional[pd.DataFrame]:
    """Lê a primeira planilha de um arquivo Excel."""
    bio = io.BytesIO(data)
    try:
        xls = pd.ExcelFile(bio, engine=engine)
        if not xls.sheet_names:
            return None
        df = pd.read_excel(xls, sheet_name=xls.sheet_names[0], dtype=str)
        df.columns = [str(c) for c in df.columns]
        return df
    except Exception:
        return None


def _try_read_as_excel(data: bytes) -> Optional[pd.DataFrame]:
    """Tenta ler arquivo como Excel (xlsx/xls)."""
    df = _read_excel_first_sheet(data, engine="openpyxl")
    if df is not None:
        return df
    try:
        df = _read_excel_first_sheet(data, engine="xlrd")
        if df is not None:
            return df
    except Exception:
        pass
    return None


def _try_read_as_csv(data: bytes) -> Optional[pd.DataFrame]:
    """Tenta ler arquivo como CSV."""
    try:
        df = pd.read_csv(io.BytesIO(data), dtype=str, sep=None, engine="python")
        df.columns = [str(c) for c in df.columns]
        return df
    except Exception:
        return None


# =============================================================================
# Funções de Limpeza de BI
# =============================================================================
def filter_cancelada(df: pd.DataFrame) -> pd.DataFrame:
    """Remove linhas onde a coluna 'Cancelada' está vazia."""
    if df is None or df.empty or "cancelada" not in df.columns:
        return df

    df = df.copy()
    # Considera vazio: NaN, None, "", espaços em branco, "nan", etc.
    cancelada_empty = (
        df["cancelada"].isna() |
        df["cancelada"].astype(str).str.strip().eq("") |
        df["cancelada"].astype(str).str.lower().isin(["nan", "none", "null"])
    )

    # Remove linhas onde Cancelada está vazia
    return df.loc[~cancelada_empty].reset_index(drop=True)


def bi_excluir_lixo(df: pd.DataFrame) -> pd.DataFrame:
    """Remove linhas do BI quando CFOP está vazio E as 4 colunas de valores estão todas = 0."""
    if df is None or df.empty or ("CFOP" not in df.columns):
        return df

    val_cols = [c for c in ["valor_contabil", "vl_icms", "vl_st", "vl_ipi"] if c in df.columns]
    if len(val_cols) < 4:
        return df

    df = df.copy()
    for c in val_cols:
        df[c] = df[c].map(to_number_br_main)

    cfop_digits = (
        df["CFOP"].map(clean_code_main).astype(str).fillna("").str.replace(r"\D+", "", regex=True)
    )
    cfop_empty = cfop_digits.str.len().eq(0)
    all_zero = df[val_cols].fillna(0.0).astype(float).abs().sum(axis=1).eq(0.0)

    drop_mask = cfop_empty & all_zero
    return df.loc[~drop_mask].reset_index(drop=True)


def bi_es_excluir_lixo(out: pd.DataFrame, cfop_series: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
    """Remove linhas quando CFOP vazio E (v_cont, v_icms, v_st, v_ipi) = 0."""
    if out is None or out.empty or cfop_series is None:
        return out, cfop_series

    req = ["v_cont", "v_icms", "v_st", "v_ipi"]
    if not all(c in out.columns for c in req):
        return out, cfop_series

    sum_vals = out[req].fillna(0.0).astype(float).abs().sum(axis=1)
    cfop_digits = cfop_series.map(clean_code_main).astype(str).fillna("").str.replace(r"\D+", "", regex=True)
    cfop_empty = cfop_digits.str.len().eq(0)
    all_zero = sum_vals.eq(0.0)

    drop_mask = cfop_empty & all_zero
    return (
        out.loc[~drop_mask].reset_index(drop=True),
        cfop_series.loc[~drop_mask].reset_index(drop=True),
    )


# =============================================================================
# Funções de Carregamento de BI
# =============================================================================
def load_bi_strict(file, label_for_errors: str) -> Optional[pd.DataFrame]:
    """Carrega BI com verificação estrita de cabeçalhos."""
    if file is None:
        return None

    raw = file.read()
    df = _try_read_as_excel(raw)
    if df is None:
        df = _try_read_as_csv(raw)

    if df is None:
        raise ValueError(f"{label_for_errors}: não foi possível interpretar como Excel (xlsx/xls) nem como CSV.")

    df.columns = [str(c) for c in df.columns]

    missing = [c for c in REQUIRED_COLS_DISPLAY if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label_for_errors}: cabeçalhos faltantes {missing}. "
            f"Os cabeçalhos devem ser estritamente iguais a: {REQUIRED_COLS_DISPLAY}. "
            f"Colunas encontradas: {list(df.columns)}"
        )

    present_optional = [c for c in OPTIONAL_VALUE_COLS if c in df.columns]
    keep = REQUIRED_COLS_DISPLAY + present_optional
    df = df[keep].copy()

    # Mapeia para nomes internos
    for src, dst in INTERNAL_KEYS.items():
        if src in df.columns and dst != src:
            df[dst] = df[src]
    for src, dst in INTERNAL_VALUE_KEYS.items():
        if src in df.columns:
            df[dst] = df[src]

    # Limpeza: excluir quando CFOP vazio E todos os valores zerados
    val_cols = [c for c in ["valor_contabil", "vl_icms", "vl_st", "vl_ipi"] if c in df.columns]
    for c in val_cols:
        df[c] = df[c].map(to_number_br_main)

    cfop_series = df["CFOP"] if "CFOP" in df.columns else pd.Series([""] * len(df), index=df.index)
    cfop_digits = cfop_series.map(clean_code_main)
    cfop_empty = cfop_digits.eq("")

    all_zero = (
        df[val_cols].fillna(0.0).astype(float).abs().sum(axis=1).eq(0.0)
        if val_cols else pd.Series(False, index=df.index)
    )

    drop_mask = cfop_empty & all_zero
    df = df.loc[~drop_mask].reset_index(drop=True)

    # Aplicar filtro da coluna "Cancelada" se ela existir
    df = filter_cancelada(df)

    return df


def detect_bi_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Detecta colunas do BI automaticamente."""
    mapping = {c: norm_text_main(c) for c in df.columns}
    aliases = {
        "cfop":   ["cfop"],
        "la_cont":["lanc cont vl contabil", "lanc cont vl"],
        "la_icms":["lanc cont vl icms"],
        "la_st":  ["lanc cont vl subst trib", "lanc cont vl icms st", "lanc cont vl subst"],
        "la_ipi": ["lanc cont vl ipi", "trib lanc cont vl ipi"],
        "v_cont": ["valor contabil"],
        "v_icms": ["vl icms"],
        "v_st":   ["vl subst trib", "vl icms st", "vl st"],
        "v_ipi":  ["vl ipi"],
        "cancelada": ["cancelada"],
    }
    cols: Dict[str, Optional[str]] = {k: None for k in aliases}
    for key, opts in aliases.items():
        for c, nm in mapping.items():
            if nm in opts:
                cols[key] = c
                break
        if cols[key] is None and key == "la_cont":
            for c, nm in mapping.items():
                if nm.startswith("lanc cont vl") and not any(x in nm for x in ["icms", "ipi", "st", "subst"]):
                    cols[key] = c
                    break
    missing_min = [k for k in ["la_cont","la_icms","la_st","la_ipi","v_cont","v_icms","v_st","v_ipi"] if cols[k] is None]
    if missing_min:
        raise ValueError(f"Colunas do BI ausentes: {missing_min}")
    return cols


def load_bi_es(file) -> Tuple[pd.DataFrame, pd.Series]:
    """Lê BI de Entradas/Saídas, normaliza campos e remove 'lixo'."""
    df = read_excel_best_main(file)
    cols = detect_bi_columns(df)

    if cols.get("cfop"):
        cfop_raw = df[cols["cfop"]]
    else:
        cfop_raw = pd.Series([""] * len(df), index=df.index)

    cfop_series = cfop_raw.map(clean_code_main)

    out = pd.DataFrame({
        "la_cont": df[cols["la_cont"]].map(clean_code_main),
        "la_icms": df[cols["la_icms"]].map(clean_code_main),
        "la_st":   df[cols["la_st"]].map(clean_code_main),
        "la_ipi":  df[cols["la_ipi"]].map(clean_code_main),
        "v_cont":  df[cols["v_cont"]].map(to_number_br_main),
        "v_icms":  df[cols["v_icms"]].map(to_number_br_main),
        "v_st":    df[cols["v_st"]].map(to_number_br_main),
        "v_ipi":   df[cols["v_ipi"]].map(to_number_br_main),
    })

    # Adicionar coluna cancelada se existir
    if cols.get("cancelada"):
        out["cancelada"] = df[cols["cancelada"]]

    for c in ["la_cont", "la_icms", "la_st", "la_ipi"]:
        out[c] = out[c].map(clean_code_main)

    # Aplicar filtro da coluna "Cancelada" antes da limpeza de lixo
    if "cancelada" in out.columns:
        cancelada_empty = (
            out["cancelada"].isna() |
            out["cancelada"].astype(str).str.strip().eq("") |
            out["cancelada"].astype(str).str.lower().isin(["nan", "none", "null"])
        )
        # Remove linhas onde Cancelada está vazia
        keep_mask = ~cancelada_empty
        out = out.loc[keep_mask].reset_index(drop=True)
        cfop_series = cfop_series.loc[keep_mask].reset_index(drop=True)

    # Limpeza de lixo
    cfop_digits = (
        cfop_series.astype(str)
        .fillna("")
        .str.replace(r"\D+", "", regex=True)
    )
    cfop_empty = cfop_digits.str.len().eq(0)

    all_zero = (
        out[["v_cont", "v_icms", "v_st", "v_ipi"]]
        .fillna(0.0).astype(float).abs().sum(axis=1).eq(0.0)
    )

    drop_mask = cfop_empty & all_zero
    out = out.loc[~drop_mask].reset_index(drop=True)
    cfop_series = cfop_series.loc[~drop_mask].reset_index(drop=True)

    return out, cfop_series


# =============================================================================
# Funções de Agregação
# =============================================================================
def aggregate_bi_all(bi: pd.DataFrame) -> pd.DataFrame:
    """Agrega dados do BI por lançamento."""
    stacks = []
    for c_l, c_v in [("la_cont", "v_cont"), ("la_icms", "v_icms"), ("la_st", "v_st"), ("la_ipi", "v_ipi")]:
        tmp = bi[[c_l, c_v]].copy()
        tmp.columns = ["lancamento", "valor"]
        tmp["lancamento"] = tmp["lancamento"].map(clean_code_main)
        tmp = tmp[tmp["lancamento"] != ""]
        stacks.append(tmp)
    long = pd.concat(stacks, ignore_index=True) if stacks else pd.DataFrame(columns=["lancamento", "valor"])
    long["valor"] = long["valor"].fillna(0.0).astype(float)
    return (long.groupby("lancamento", as_index=False)["valor"].sum().rename(columns={"valor": "valor_bi"}))


def cfop_missing_matrix_es(bi_df: pd.DataFrame, cfop_series: pd.Series) -> pd.DataFrame:
    """Cria matriz de lacunas por CFOP para Entradas/Saídas."""
    if cfop_series is None or cfop_series.empty:
        return pd.DataFrame()
    aux = pd.DataFrame({
        "CFOP": cfop_series.map(clean_code_main),
        "has_cont": ~bi_df["la_cont"].map(is_empty_code_main),
        "has_icms": ~bi_df["la_icms"].map(is_empty_code_main),
        "has_st":   ~bi_df["la_st"].map(is_empty_code_main),
        "has_ipi":  ~bi_df["la_ipi"].map(is_empty_code_main),
    })
    aux = aux[aux["CFOP"] != ""]
    grp = aux.groupby("CFOP").agg({"has_cont": "any", "has_icms": "any", "has_st": "any", "has_ipi": "any"}).reset_index()
    out = grp.copy()
    out["Contábil"] = np.where(out["has_cont"], "OK", "FALTA")
    out["ICMS"]     = np.where(out["has_icms"], "OK", "FALTA")
    out["ST"]       = np.where(out["has_st"],   "OK", "FALTA")
    out["IPI"]      = np.where(out["has_ipi"],  "OK", "FALTA")
    out = out[["CFOP","Contábil","ICMS","ST","IPI"]]
    mask_any_missing = (out[["Contábil","ICMS","ST","IPI"]] == "FALTA").any(axis=1)
    return out[mask_any_missing].sort_values("CFOP")


# =============================================================================
# Funções para BI de Serviços
# =============================================================================
def _find_col(df: pd.DataFrame, *alvos: str) -> Optional[str]:
    """Encontra coluna no DataFrame."""
    m = {c: norm_text_main(c) for c in df.columns}
    for alvo in alvos:
        a = norm_text_main(alvo)
        for c, n in m.items():
            if n == a:
                return c
    for alvo in alvos:
        a = norm_text_main(alvo)
        for c, n in m.items():
            if n.startswith(a):
                return c
    return None


def load_bi_servico(file) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Carrega BI de Serviços."""
    df = read_excel_best_main(file)

    # Filtrar pela coluna "Cancelada" se ela existir
    cancelada_col = _find_col(df, "cancelada")
    if cancelada_col:
        cancelada_empty = (
            df[cancelada_col].isna() |
            df[cancelada_col].astype(str).str.strip().eq("") |
            df[cancelada_col].astype(str).str.lower().isin(["nan", "none", "null"])
        )
        # Remove linhas onde Cancelada está vazia
        df = df.loc[~cancelada_empty].reset_index(drop=True)

    cfop_col = _find_col(df, "cfop")
    cfop_series = pd.Series([], dtype="object")
    if cfop_col:
        cfop_series = df[cfop_col].map(clean_code_main)

    stacks, pres_cols = [], {}
    for code_label, val_opts, lbl in SERV_COLS:
        c_cod = _find_col(df, code_label, code_label.replace(".", " ").replace("  ", " "))
        c_val = None
        for vname in val_opts:
            c_val = c_val or _find_col(df, vname, vname.replace(".", " ").replace("  ", " "))
        if c_cod and c_val:
            pres_cols[lbl] = ~df[c_cod].map(is_empty_code_main)
            tmp = pd.DataFrame({"lancamento": df[c_cod].map(clean_code_main), "valor": df[c_val].map(to_number_br_main)})
            tmp = tmp[(tmp["lancamento"] != "") & (tmp["valor"].notna())]
            stacks.append(tmp)

    if not stacks:
        raise ValueError("Não encontrei nenhuma dupla código/valor do BI de Serviços.")

    long = pd.concat(stacks, ignore_index=True)
    long["valor"] = long["valor"].fillna(0.0).astype(float)
    agg = long.groupby("lancamento", as_index=False)["valor"].sum().rename(columns={"valor": "valor_bi"})

    # Matriz de lacunas por CFOP
    missing_matrix_srv = pd.DataFrame()
    if not cfop_series.empty and pres_cols:
        aux = pd.DataFrame({"CFOP": cfop_series.map(clean_code_main)})
        for lbl, ser in pres_cols.items():
            aux[lbl] = ser.fillna(False).astype(bool)
        aux = aux[aux["CFOP"] != ""]
        grp = aux.groupby("CFOP").agg({lbl:"any" for lbl in pres_cols}).reset_index()
        label_order = ["doc","cofins","pis","iss","iss_ret","irrf","pis_ret","cofins_ret","inss_ret","csll_ret"]
        col_map = {"doc":"Documento","cofins":"Cofins","pis":"PIS","iss":"ISS","iss_ret":"ISS Ret.","irrf":"IRRF","pis_ret":"PIS Ret.",
                   "cofins_ret":"COFINS Ret.","inss_ret":"INSS Ret.","csll_ret":"CSLL Ret."}
        out = grp[["CFOP"]].copy()
        for lbl in label_order:
            out[col_map[lbl]] = np.where(grp.get(lbl, False), "OK", "FALTA")
        mask_any = (out.drop(columns=["CFOP"]) == "FALTA").any(axis=1)
        missing_matrix_srv = out[mask_any].sort_values("CFOP")

    return agg, cfop_series, missing_matrix_srv