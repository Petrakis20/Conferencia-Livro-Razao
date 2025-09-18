# streamlit_app.py
# Python 3.12

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# =============================================================================
# Config
# =============================================================================
st.set_page_config(page_title="Pipeline Fiscal • BI → CFOP/ Razão", layout="wide")
st.title("📊 Pipeline Fiscal")
st.caption("① Análise do BI (CFOP × Base CFOP)  →  ② Conferência BI (Entradas/Saídas/Serviços) × Razão (TXT)")

# =============================================================================
# Sidebar — Base CFOP (JSON do disco)
# =============================================================================
st.sidebar.header("Base de CFOP (JSON do disco)")
DEFAULT_BASE_PATH = Path("cfop_base.json")

@st.cache_data(show_spinner=False)
def load_base_json(p: Path) -> Dict[str, Dict]:
    with p.open(encoding="utf-8") as f:
        return json.load(f)

base_path = Path(st.sidebar.text_input("Caminho do arquivo JSON", value=str(DEFAULT_BASE_PATH))).expanduser()
base_map: Dict[str, Dict] = {}
try:
    if base_path.exists():
        base_map = load_base_json(base_path)
        st.sidebar.success(f"Base carregada: {base_path.name} • {len(base_map)} CFOPs")
    else:
        st.sidebar.error("Arquivo cfop_base.json não encontrado. Informe um caminho válido na sidebar.")
except Exception as e:
    st.sidebar.error(f"Erro ao carregar base: {e}")

# =============================================================================
# PARTE 1 — Análise do BI (CFOP × Base CFOP)
# =============================================================================
REQUIRED_COLS_DISPLAY = [
    "CFOP",
    "Lanc. Cont. Vl. Contábil",
    "Lanc. Cont. Vl. ICMS",
    "Lanc. Cont. Vl. Subst. Trib.",           # <- estrito como você pediu
    "Lanc. Cont. Vl. IPI",        # <- estrito como você pediu
]
OPTIONAL_VALUE_COLS = [
    "Valor Contábil",
    "Vl. ICMS",
    "Vl. ST",
    "Vl. IPI",
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
}

def normalize_code(val: Optional[str]) -> Optional[str]:
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s and s.lower() != "nan" else None

def compare_row(cfop_code: str, row: Dict[str, Optional[str]], base_map: Dict[str, Dict]) -> Tuple[str, str, Optional[Dict], Dict, Optional[str]]:
    cfop = normalize_code(cfop_code)
    found = {
        "contabil": normalize_code(row.get("contabil")),
        "icms": normalize_code(row.get("icms")),
        "icms_subst": normalize_code(row.get("icms_subst")),
        "ipi": normalize_code(row.get("ipi")),
    }
    base = base_map.get(str(cfop)) if cfop is not None else None

    if base is None:
        status = "⚠️ CFOP não encontrado na base"
        details = "CFOP não existe na base."
        expected = None
    else:
        expected = {
            "contabil": normalize_code(base.get("contabil")),
            "icms": normalize_code(base.get("icms")),
            "icms_subst": normalize_code(base.get("icms_subst")),
            "ipi": normalize_code(base.get("ipi")),
        }
        zeros, mismatches = [], []
        for key, lbl in [("contabil", "Contábil"), ("icms", "ICMS"), ("icms_subst", "ICMS Subst. Trib."), ("ipi", "IPI")]:
            exp, got = expected.get(key), found.get(key)
            if exp is None and got is None:
                continue
            if exp is not None and got is None:
                zeros.append(f"{lbl}: zerado no BI, esperado {exp}")
                continue
            if exp is None and got is not None:
                mismatches.append(f"{lbl}: encontrado {got}, esperado vazio")
                continue
            if str(exp) != str(got):
                mismatches.append(f"{lbl}: encontrado {got}, deveria ser {exp}")

        # Anexa valores do BI no detalhe quando houver divergência/zerado
        valores_resumo = []
        for k, label in [("valor_contabil", "Valor Contábil"), ("vl_icms", "Vl. ICMS"), ("vl_st", "Vl. ST"), ("vl_ipi", "Vl. IPI")]:
            v = row.get(k)
            if v is not None and str(v).strip() != "":
                valores_resumo.append(f"{label}={v}")
        resumo_valores = " | ".join(valores_resumo) if valores_resumo else ""

        if mismatches:
            status = "❌ Diferente da base"
            det = "; ".join(mismatches + zeros)
            details = f"{det}" + (f"  •  Valores (BI): {resumo_valores}" if resumo_valores else "")
        elif zeros:
            status = "🟡 Zerado no BI"
            details = "; ".join(zeros) + (f"  •  Valores (BI): {resumo_valores}" if resumo_valores else "")
        else:
            status = "OK"
            details = "Tudo certo conforme a base."

    nome = None if base is None else base.get("nome")
    return status, details, expected, found, nome

# --- Leitura BI robusta (csv/xlsx/xls) para Parte 1 (cabeçalho estrito) ---
def _read_excel_first_sheet(data: bytes, engine: str) -> Optional[pd.DataFrame]:
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
    df = _read_excel_first_sheet(data, engine="openpyxl")  # xlsx/xlsm
    if df is not None:
        return df
    try:
        import xlrd  # noqa: F401
        df = _read_excel_first_sheet(data, engine="xlrd")  # xls
        if df is not None:
            return df
    except Exception:
        pass
    return None

def _try_read_as_csv(data: bytes) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(io.BytesIO(data), dtype=str, sep=None, engine="python")
        df.columns = [str(c) for c in df.columns]
        return df
    except Exception:
        return None

def load_bi_strict(file, label_for_errors: str) -> Optional[pd.DataFrame]:
    if file is None:
        return None

    raw = file.read()

    # ✅ nada de "or" entre DataFrames
    df = _try_read_as_excel(raw)
    if df is None:
        df = _try_read_as_csv(raw)

    if df is None:
        st.error(f"{label_for_errors}: não foi possível interpretar como Excel (xlsx/xls) nem como CSV.")
        return None

    df.columns = [str(c) for c in df.columns]  # cabeçalho estrito

    missing = [c for c in REQUIRED_COLS_DISPLAY if c not in df.columns]
    if missing:
        st.error(
            f"{label_for_errors}: cabeçalhos faltantes {missing}. "
            f"Os cabeçalhos devem ser estritamente iguais a: {REQUIRED_COLS_DISPLAY}. "
            f"Colunas encontradas: {list(df.columns)}"
        )
        return None

    present_optional = [c for c in OPTIONAL_VALUE_COLS if c in df.columns]
    keep = REQUIRED_COLS_DISPLAY + present_optional
    df = df[keep].copy()

    for src, dst in INTERNAL_KEYS.items():
        if src in df.columns and dst != src:
            df[dst] = df[src]
    for src, dst in INTERNAL_VALUE_KEYS.items():
        if src in df.columns:
            df[dst] = df[src]

    return df

# =============================================================================
# PARTE 2 — Conferência BI (Entradas/Saídas/Serviços) × Razão (TXT)
# (unificado do seu conferencia-livro-razao.py + utilidades do utils.py)
# =============================================================================
EMPTY_TOKENS = {"", "nan", "none", "nao possui", "não possui", "x"}

def norm_text(s: str) -> str:
    s = str(s).strip().lower()
    s = (s.replace("ã","a").replace("á","a").replace("à","a").replace("â","a")
           .replace("ç","c").replace("é","e").replace("ê","e")
           .replace("í","i").replace("ó","o").replace("ô","o").replace("ú","u"))
    s = re.sub(r"[^a-z0-9 ]+"," ", s)
    s = re.sub(r"\s+"," ", s).strip()
    return s

def clean_code(x: str) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    if s == "" or norm_text(s) in EMPTY_TOKENS:
        return ""
    s = re.sub(r"[^0-9]", "", s)
    s = re.sub(r"\.0+$", "", s)
    while len(s) > 5 and s.endswith("0"):
        s = s[:-1]
    return s

def is_empty_code(x: str) -> bool:
    s = clean_code(x)
    return s == "" or set(s) == {"0"}

def to_number_br(v) -> float:
    if v is None:
        return 0.0
    s = str(v).strip()
    if s == "" or norm_text(s) in EMPTY_TOKENS:
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    s = s.replace(".", "").replace(",", ".")
    try:
        val = float(s)
    except Exception:
        val = float(re.sub(r"[^0-9\.\-]", "", s) or 0)
    return -val if neg else val

def extract_desc_before_first_digit(s: str) -> str:
    if s is None:
        return ""
    txt = str(s).strip()
    if not txt:
        return ""
    part = re.split(r"\d", txt, maxsplit=1)[0]
    return part.strip(" -–—•|:;/,.").strip()

def read_excel_best(file) -> pd.DataFrame:
    xls = pd.ExcelFile(file)
    best_df, best_cols = None, -1
    for sh in xls.sheet_names:
        df = xls.parse(sh)
        if df.shape[1] > best_cols:
            best_df, best_cols = df, df.shape[1]
    return best_df if best_df is not None else pd.DataFrame()

def detect_bi_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    mapping = {c: norm_text(c) for c in df.columns}
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
    df = read_excel_best(file)
    cols = detect_bi_columns(df)
    cfop_series = pd.Series([], dtype="object")
    if cols.get("cfop"):
        cfop_series = df[cols["cfop"]].map(clean_code)

    out = pd.DataFrame({
        "la_cont": df[cols["la_cont"]].map(clean_code),
        "la_icms": df[cols["la_icms"]].map(clean_code),
        "la_st":   df[cols["la_st"]].map(clean_code),
        "la_ipi":  df[cols["la_ipi"]].map(clean_code),
        "v_cont":  df[cols["v_cont"]].map(to_number_br),
        "v_icms":  df[cols["v_icms"]].map(to_number_br),
        "v_st":    df[cols["v_st"]].map(to_number_br),
        "v_ipi":   df[cols["v_ipi"]].map(to_number_br),
    })
    for c in ["la_cont","la_icms","la_st","la_ipi"]:
        out[c] = out[c].map(clean_code)
    return out, cfop_series

def aggregate_bi_all(bi: pd.DataFrame) -> pd.DataFrame:
    stacks = []
    for c_l, c_v in [("la_cont", "v_cont"), ("la_icms", "v_icms"), ("la_st", "v_st"), ("la_ipi", "v_ipi")]:
        tmp = bi[[c_l, c_v]].copy()
        tmp.columns = ["lancamento", "valor"]
        tmp["lancamento"] = tmp["lancamento"].map(clean_code)
        tmp = tmp[tmp["lancamento"] != ""]
        stacks.append(tmp)
    long = pd.concat(stacks, ignore_index=True) if stacks else pd.DataFrame(columns=["lancamento", "valor"])
    long["valor"] = long["valor"].fillna(0.0).astype(float)
    return (long.groupby("lancamento", as_index=False)["valor"].sum().rename(columns={"valor": "valor_bi"}))

def cfop_missing_matrix_es(bi_df: pd.DataFrame, cfop_series: pd.Series) -> pd.DataFrame:
    if cfop_series is None or cfop_series.empty:
        return pd.DataFrame()
    aux = pd.DataFrame({
        "CFOP": cfop_series.map(clean_code),
        "has_cont": ~bi_df["la_cont"].map(is_empty_code),
        "has_icms": ~bi_df["la_icms"].map(is_empty_code),
        "has_st":   ~bi_df["la_st"].map(is_empty_code),
        "has_ipi":  ~bi_df["la_ipi"].map(is_empty_code),
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

def _find_col(df: pd.DataFrame, *alvos: str) -> Optional[str]:
    m = {c: norm_text(c) for c in df.columns}
    for alvo in alvos:
        a = norm_text(alvo)
        for c, n in m.items():
            if n == a:
                return c
    for alvo in alvos:
        a = norm_text(alvo)
        for c, n in m.items():
            if n.startswith(a):
                return c
    return None

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

def load_bi_servico(file) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    df = read_excel_best(file)
    cfop_col = _find_col(df, "cfop")
    cfop_series = pd.Series([], dtype="object")
    if cfop_col:
        cfop_series = df[cfop_col].map(clean_code)

    stacks, pres_cols = [], {}
    for code_label, val_opts, lbl in SERV_COLS:
        c_cod = _find_col(df, code_label, code_label.replace(".", " ").replace("  ", " "))
        c_val = None
        for vname in val_opts:
            c_val = c_val or _find_col(df, vname, vname.replace(".", " ").replace("  ", " "))
        if c_cod and c_val:
            pres_cols[lbl] = ~df[c_cod].map(is_empty_code)
            tmp = pd.DataFrame({"lancamento": df[c_cod].map(clean_code), "valor": df[c_val].map(to_number_br)})
            tmp = tmp[(tmp["lancamento"] != "") & (tmp["valor"].notna())]
            stacks.append(tmp)

    if not stacks:
        raise ValueError("Não encontrei nenhuma dupla código/valor do BI de Serviços.")

    long = pd.concat(stacks, ignore_index=True)
    long["valor"] = long["valor"].fillna(0.0).astype(float)
    agg = long.groupby("lancamento", as_index=False)["valor"].sum().rename(columns={"valor": "valor_bi"})

    # Matriz de lacunas por CFOP (se CFOP existe)
    missing_matrix_srv = pd.DataFrame()
    if not cfop_series.empty and pres_cols:
        aux = pd.DataFrame({"CFOP": cfop_series.map(clean_code)})
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

def read_razao_txt(file) -> pd.DataFrame:
    df = pd.read_csv(file, sep=",", header=None, engine="python", dtype=str)
    cod  = df.iloc[:, 1].map(clean_code)
    val  = df.iloc[:, 3].map(to_number_br)
    desc = df.iloc[:, 7].map(extract_desc_before_first_digit) if df.shape[1] >= 8 else ""
    out = pd.DataFrame({"lancamento": cod, "valor_razao": val, "descricao": desc})
    out = out[out["lancamento"] != ""]
    soma = out.groupby("lancamento", as_index=False)["valor_razao"].sum()
    desc1 = (out[out["descricao"].astype(str).str.len() > 0]
                .drop_duplicates(subset=["lancamento"], keep="first")[["lancamento", "descricao"]])
    razao_agg = soma.merge(desc1, on="lancamento", how="left")
    return razao_agg

def compare_bi_vs_razao(bi: pd.DataFrame, razao: pd.DataFrame) -> pd.DataFrame:
    comp = bi.merge(razao, on="lancamento", how="outer")
    comp["valor_bi"] = comp["valor_bi"].fillna(0.0)
    comp["valor_razao"] = comp["valor_razao"].fillna(0.0)
    comp["dif"] = comp["valor_bi"] - comp["valor_razao"]
    comp["ok"] = np.isclose(comp["dif"], 0.0, atol=0.01)
    if "descricao" not in comp.columns:
        comp["descricao"] = ""
    cols = ["lancamento", "descricao", "valor_bi", "valor_razao", "dif", "ok"]
    return comp.reindex(columns=cols).sort_values(["ok","lancamento"], ascending=[True, True])

# =============================================================================
# UI — Abas
# =============================================================================
tab1, tab2 = st.tabs(["① Análise do BI (CFOP × Base CFOP)", "② Conferência BI × Razão (TXT)"])

with tab1:
    st.header("Parte 1 — Análise do BI (CFOP × Base CFOP)")
    st.write("Cabeçalhos obrigatórios **estritos**:")
    st.code(" | ".join(REQUIRED_COLS_DISPLAY), language="text")
    st.write("Colunas opcionais de **valores** (se presentes, serão exibidas quando houver diferença/zerado):")
    st.code(" | ".join(OPTIONAL_VALUE_COLS), language="text")

    bi_entrada = st.file_uploader("BI Entrada (obrigatório)", type=["csv", "xlsx", "xls"], key="p1_entrada")
    bi_saida   = st.file_uploader("BI Saída (opcional)",   type=["csv", "xlsx", "xls"], key="p1_saida")

    dfs = []
    if bi_entrada is not None:
        df_ent = load_bi_strict(bi_entrada, "BI Entrada")
        if df_ent is not None:
            df_ent["origem"] = "Entrada"
            dfs.append(df_ent)

    if bi_saida is not None:
        df_sai = load_bi_strict(bi_saida, "BI Saída")
        if df_sai is not None:
            df_sai["origem"] = "Saída"
            dfs.append(df_sai)

    if not base_map:
        st.error("Base de CFOP não carregada. Informe um caminho válido na sidebar.")
    elif len(dfs) == 0:
        st.info("Envie ao menos um arquivo de BI para conferir.")
    else:
        bi_all = pd.concat(dfs, ignore_index=True)

        results = []
        for _, r in bi_all.iterrows():
            status, details, expected, found, nome = compare_row(
                r.get("CFOP"),
                {
                    "contabil": r.get("contabil"),
                    "icms": r.get("icms"),
                    "icms_subst": r.get("icms_subst"),
                    "ipi": r.get("ipi"),
                    "valor_contabil": r.get("valor_contabil"),
                    "vl_icms": r.get("vl_icms"),
                    "vl_st": r.get("vl_st"),
                    "vl_ipi": r.get("vl_ipi"),
                },
                base_map
            )

            row_out = {
                "origem": r.get("origem"),
                "CFOP": r.get("CFOP"),
                "Nome (Base)": nome,
                "Status": status,
                "Detalhes": details,
                "Esperado Contábil": None if expected is None else expected.get("contabil"),
                "Encontrado Contábil": None if expected is None else found.get("contabil"),
                "Esperado ICMS": None if expected is None else expected.get("icms"),
                "Encontrado ICMS": None if expected is None else found.get("icms"),
                "Esperado ICMS Subst. Trib.": None if expected is None else expected.get("icms_subst"),
                "Encontrado ICMS Subst. Trib.": None if expected is None else found.get("icms_subst"),
                "Esperado IPI": None if expected is None else expected.get("ipi"),
                "Encontrado IPI": None if expected is None else found.get("ipi"),
            }

            if status in ("❌ Diferente da base", "🟡 Zerado no BI"):
                if "valor_contabil" in bi_all.columns:
                    row_out["Valor Contábil"] = r.get("valor_contabil")
                if "vl_icms" in bi_all.columns:
                    row_out["Vl. ICMS"] = r.get("vl_icms")
                if "vl_st" in bi_all.columns:
                    row_out["Vl. ST"] = r.get("vl_st")
                if "vl_ipi" in bi_all.columns:
                    row_out["Vl. IPI"] = r.get("vl_ipi")

            results.append(row_out)

        out_df = pd.DataFrame(results)

        # persistir para eventual uso futuro
        st.session_state["p1_bi_all"] = bi_all
        st.session_state["p1_result"] = out_df

        st.subheader("Resultado da Validação")
        ok_count = int((out_df["Status"] == "OK").sum())
        diff_count = int((out_df["Status"] == "❌ Diferente da base").sum())
        zero_count = int((out_df["Status"] == "🟡 Zerado no BI").sum())
        notfound_count = int((out_df["Status"].str.contains("CFOP não encontrado", na=False)).sum())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("OK", ok_count)
        c2.metric("Diferente", diff_count)
        c3.metric("Zerado no BI", zero_count)
        c4.metric("CFOP ausente na base", notfound_count)

        status_filter = st.multiselect("Filtrar por Status", options=sorted(out_df["Status"].dropna().unique().tolist()))
        origem_filter = st.multiselect("Filtrar por Origem", options=sorted(out_df["origem"].dropna().unique().tolist()))

        filtered = out_df.copy()
        if status_filter:
            filtered = filtered[filtered["Status"].isin(status_filter)]
        if origem_filter:
            filtered = filtered[filtered["origem"].isin(origem_filter)]

        st.dataframe(filtered, use_container_width=True)

        # Downloads (CSV/Excel)
        csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Baixar Parte 1 (.csv)", data=csv_bytes, file_name="resultado_validacao_cfop.csv", mime="text/csv")

        def make_excel_bytes(df: pd.DataFrame) -> Tuple[bytes, str, str]:
            try:
                import xlwt  # noqa: F401
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="xlwt") as writer:
                    df.to_excel(writer, index=False, sheet_name="Relatorio")
                return buf.getvalue(), "resultado_validacao_cfop.xls", "application/vnd.ms-excel"
            except Exception:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Relatorio")
                return (buf.getvalue(), "resultado_validacao_cfop.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        excel_bytes, excel_name, excel_mime = make_excel_bytes(filtered)
        st.download_button("Baixar Parte 1 (Excel)", data=excel_bytes, file_name=excel_name, mime=excel_mime)

with tab2:
    st.header("Parte 2 — Conferência BI (Entradas/Saídas/Serviços) × Razão (TXT)")
    c1, c2, c3 = st.columns(3)
    with c1:
        bi_ent = st.file_uploader("📥 BI Entradas (.xls/.xlsx)", type=["xls","xlsx"], key="bi_ent")
    with c2:
        bi_sai = st.file_uploader("📤 BI Saídas (.xls/.xlsx)", type=["xls","xlsx"], key="bi_sai")
    with c3:
        bi_srv = st.file_uploader("🧾 BI Serviços (.xls/.xlsx)", type=["xls","xlsx"], key="bi_srv")

    razao_files = st.file_uploader("📚 Razões TXT (pode enviar vários)", type=["txt"], accept_multiple_files=True)

    st.divider()

    # Processar BIs
    bi_parts: List[pd.DataFrame] = []
    lacunas_es_parts: List[pd.DataFrame] = []
    lacunas_srv_tbl = pd.DataFrame()

    if bi_ent is not None:
        try:
            bi_df_ent, cfop_ent = load_bi_es(bi_ent)
            agg_ent = aggregate_bi_all(bi_df_ent); agg_ent["origem"] = "entradas"
            bi_parts.append(agg_ent)
            faltas_ent = cfop_missing_matrix_es(bi_df_ent, cfop_ent)
            if not faltas_ent.empty:
                faltas_ent.insert(0, "Origem", "Entradas")
                lacunas_es_parts.append(faltas_ent)
            st.success("BI Entradas carregado.")
        except Exception as e:
            st.error(f"Erro no BI Entradas: {e}")

    if bi_sai is not None:
        try:
            bi_df_sai, cfop_sai = load_bi_es(bi_sai)
            agg_sai = aggregate_bi_all(bi_df_sai); agg_sai["origem"] = "saidas"
            bi_parts.append(agg_sai)
            faltas_sai = cfop_missing_matrix_es(bi_df_sai, cfop_sai)
            if not faltas_sai.empty:
                faltas_sai.insert(0, "Origem", "Saídas")
                lacunas_es_parts.append(faltas_sai)
            st.success("BI Saídas carregado.")
        except Exception as e:
            st.error(f"Erro no BI Saídas: {e}")

    if bi_srv is not None:
        try:
            agg_srv, cfop_srv, faltas_srv = load_bi_servico(bi_srv)
            agg_srv["origem"] = "servicos"
            bi_parts.append(agg_srv)
            if not faltas_srv.empty:
                faltas_srv.insert(0, "Origem", "Serviços")
                lacunas_srv_tbl = faltas_srv
            st.success("BI Serviços carregado.")
        except Exception as e:
            st.error(f"Erro no BI Serviços: {e}")

    if not bi_parts:
        st.info("Envie ao menos um BI (Entradas, Saídas ou Serviços).")
        st.stop()

    bi_total = (pd.concat(bi_parts, ignore_index=True).groupby("lancamento", as_index=False)["valor_bi"].sum())
    st.subheader("📊 BI — Soma por Lançamento")
    st.dataframe(bi_total, use_container_width=True, height=280)

    # Lacunas por CFOP
    if lacunas_es_parts or (not lacunas_srv_tbl.empty):
        st.divider()
        st.subheader("⚠️ CFOP × Lançamentos faltantes")
        if lacunas_es_parts:
            tbl_es = pd.concat(lacunas_es_parts, ignore_index=True)
            st.markdown("**Entradas/Saídas**")
            st.dataframe(tbl_es, use_container_width=True, height=280)
        if not lacunas_srv_tbl.empty:
            st.markdown("**Serviços**")
            st.dataframe(lacunas_srv_tbl, use_container_width=True, height=280)
    else:
        st.info("Nenhuma lacuna de lançamento por CFOP identificada (ou planilhas sem coluna CFOP).")

    st.divider()

    # Razões
    if not razao_files:
        st.info("Envie ao menos um arquivo TXT de Razão.")
        st.stop()

    razoes = []
    for f in razao_files:
        try:
            rz = read_razao_txt(f); rz["arquivo"] = f.name
            razoes.append(rz)
            with st.expander(f"Prévia TXT: {f.name}"):
                st.dataframe(rz.head(200), use_container_width=True, height=200)
        except Exception as e:
            st.error(f"Erro lendo TXT {f.name}: {e}")

    razao_total = (pd.concat(razoes, ignore_index=True)
                     .groupby("lancamento", as_index=False)["valor_razao"].sum()
                     .merge(pd.concat(razoes, ignore_index=True)[["lancamento", "descricao"]]
                               .dropna().drop_duplicates("lancamento"),
                            on="lancamento", how="left"))

    st.subheader("📒 Razão consolidado (todos TXT)")
    st.dataframe(razao_total, use_container_width=True, height=240)

    st.divider()

    # Comparação
    st.subheader("✅ Comparação BI × Razão por Lançamento")
    comp = compare_bi_vs_razao(bi_total, razao_total)

    c1, c2, c3 = st.columns(3)
    c1.metric("Lançamentos BI", f"{len(bi_total)}")
    c2.metric("Lançamentos Razão", f"{len(razao_total)}")
    c3.metric("Divergências", f"{(~comp['ok']).sum()}")

    styled = (
        comp.style
            .format({"valor_bi": "{:,.2f}", "valor_razao": "{:,.2f}", "dif": "{:,.2f}"})
            .apply(lambda s: pd.Series(np.where(comp["ok"], "color:green", "color:red"), index=comp.index), subset=["dif"])
    )
    st.dataframe(styled, use_container_width=True, height=420)

    # Downloads (CSV/Excel)
    cdl1, cdl2, cdl3 = st.columns(3)
    with cdl1:
        csv_bi = bi_total.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Baixar BI (CSV)", data=csv_bi, file_name="bi_por_lancamento.csv", mime="text/csv")
    with cdl2:
        csv_rz = razao_total.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Baixar Razão (CSV)", data=csv_rz, file_name="razao_consolidado.csv", mime="text/csv")
    with cdl3:
        csv_comp = comp.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Baixar Comparação (CSV)", data=csv_comp, file_name="comparacao_bi_razao.csv", mime="text/csv")

    def make_excel_bytes(df: pd.DataFrame, sheet: str) -> Tuple[bytes, str, str]:
        try:
            import xlwt  # noqa: F401
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="xlwt") as writer:
                df.to_excel(writer, index=False, sheet_name=sheet)
            return buf.getvalue(), f"{sheet.lower().replace(' ','_')}.xls", "application/vnd.ms-excel"
        except Exception:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name=sheet)
            return (buf.getvalue(), f"{sheet.lower().replace(' ','_')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    ex1, nm1, mm1 = make_excel_bytes(bi_total, "BI_Por_Lancamento")
    ex2, nm2, mm2 = make_excel_bytes(razao_total, "Razao_Consolidado")
    ex3, nm3, mm3 = make_excel_bytes(comp, "Comparacao_BI_Razao")

    cex1, cex2, cex3 = st.columns(3)
    with cex1:
        st.download_button("Baixar BI (Excel)", data=ex1, file_name=nm1, mime=mm1)
    with cex2:
        st.download_button("Baixar Razão (Excel)", data=ex2, file_name=nm2, mime=mm2)
    with cex3:
        st.download_button("Baixar Comparação (Excel)", data=ex3, file_name=nm3, mime=mm3)

# =============================================================================
# Fim
# =============================================================================
