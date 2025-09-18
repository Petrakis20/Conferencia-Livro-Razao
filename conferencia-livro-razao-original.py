from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Conferência BI x Razão (TXT)", layout="wide")

# ============================================================
# Utilitários de normalização
# ============================================================
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
    """
    Mantém só dígitos, remove '.0' e corrige zeros espúrios à direita.
    Ex.: '10015.0' -> '10015', '100010' -> '10001', '001410' -> '00141'
    """
    if x is None:
        return ""
    s = str(x).strip()
    if s == "" or norm_text(s) in EMPTY_TOKENS:
        return ""
    s = re.sub(r"[^0-9]", "", s)      # somente dígitos
    s = re.sub(r"\.0+$", "", s)       # tira .0 se houver
    while len(s) > 5 and s.endswith("0"):
        s = s[:-1]
    return s

def is_empty_code(x: str) -> bool:
    s = clean_code(x)
    return s == "" or set(s) == {"0"}  # trata '0', '00' como vazio

def to_number_br(v) -> float:
    """Converte '226.755,32' -> 226755.32; aceita '(123,45)' como negativo."""
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
    """Pega só o trecho antes do primeiro dígito (0-9)."""
    if s is None:
        return ""
    txt = str(s).strip()
    if not txt:
        return ""
    part = re.split(r"\d", txt, maxsplit=1)[0]
    return part.strip(" -–—•|:;/,.").strip()

# ============================================================
# Leitura de Excel (pega a aba com mais colunas)
# ============================================================
def read_excel_best(file) -> pd.DataFrame:
    xls = pd.ExcelFile(file)
    best_df, best_cols = None, -1
    for sh in xls.sheet_names:
        df = xls.parse(sh)
        if df.shape[1] > best_cols:
            best_df, best_cols = df, df.shape[1]
    return best_df if best_df is not None else pd.DataFrame()

# ============================================================
# BI Entradas/Saídas (quatro eixos: contábil, icms, st, ipi)
# ============================================================
def detect_bi_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    mapping = {c: norm_text(c) for c in df.columns}
    aliases = {
        "cfop":   ["cfop"],
        "la_cont":["lanc cont vl contabil", "lanc cont vl"],
        "la_icms":["lanc cont vl icms"],
        "la_st":  ["lanc cont vl subst trib", "lanc cont vl icms st"],
        "la_ipi": ["lanc cont vl ipi"],
        "v_cont": ["valor contabil"],
        "v_icms": ["vl icms"],
        "v_st":   ["vl subst trib", "vl icms st", "vl st"],
        "v_ipi":  ["vl ipi"],
    }
    cols: Dict[str, Optional[str]] = {k: None for k in aliases}
    for key, opts in aliases.items():
        # match exato
        for c, nm in mapping.items():
            if nm in opts:
                cols[key] = c
                break
        # fallback genérico p/ la_cont
        if cols[key] is None and key == "la_cont":
            for c, nm in mapping.items():
                if nm.startswith("lanc cont vl") and not any(x in nm for x in ["icms", "ipi", "st", "subst"]):
                    cols[key] = c
                    break
    missing_min = [k for k in ["la_cont","la_icms","la_st","la_ipi","v_cont","v_icms","v_st","v_ipi"] if cols[k] is None]
    if missing_min:
        raise ValueError(f"Colunas do BI ausentes: {missing_min}")
    return cols

def load_bi(file) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Retorna:
      - df_codes: DataFrame com colunas de códigos/valores (para agregação)
      - cfop_series: Série com CFOP limpo (se existir no arquivo); caso contrário, série vazia
    """
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
    for c_l, c_v in [("la_cont", "v_cont"), ("la_icms", "v_icms"),
                     ("la_st", "v_st"), ("la_ipi", "v_ipi")]:
        tmp = bi[[c_l, c_v]].copy()
        tmp.columns = ["lancamento", "valor"]
        tmp["lancamento"] = tmp["lancamento"].map(clean_code)
        tmp = tmp[tmp["lancamento"] != ""]
        stacks.append(tmp)
    long = pd.concat(stacks, ignore_index=True) if stacks else pd.DataFrame(columns=["lancamento", "valor"])
    long["valor"] = long["valor"].fillna(0.0).astype(float)
    return (long.groupby("lancamento", as_index=False)["valor"]
                .sum()
                .rename(columns={"valor": "valor_bi"}))

# --------- NOVO: matriz de lacunas para Entradas/Saídas ----------
def cfop_missing_matrix_es(bi_df: pd.DataFrame, cfop_series: pd.Series) -> pd.DataFrame:
    """Tabela CFOP × {Contábil, ICMS, ST, IPI} marcando 'FALTA' quando nenhum código foi encontrado em TODO o BI para aquele CFOP."""
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
    # por CFOP, queremos saber se EM ALGUMA linha apareceu o código daquele tipo
    grp = aux.groupby("CFOP").agg({
        "has_cont": "any", "has_icms": "any", "has_st": "any", "has_ipi": "any"
    }).reset_index()
    # marca FALTA/OK
    out = grp.copy()
    out["Contábil"] = np.where(out["has_cont"], "OK", "FALTA")
    out["ICMS"]     = np.where(out["has_icms"], "OK", "FALTA")
    out["ST"]       = np.where(out["has_st"],   "OK", "FALTA")
    out["IPI"]      = np.where(out["has_ipi"],  "OK", "FALTA")
    out = out[["CFOP","Contábil","ICMS","ST","IPI"]]
    # filtra somente CFOPs com ao menos uma falta
    mask_any_missing = (out[["Contábil","ICMS","ST","IPI"]] == "FALTA").any(axis=1)
    return out[mask_any_missing].sort_values("CFOP")

# ============================================================
# BI Serviços (códigos exatamente como especificado)
# ============================================================
def _find_col(df: pd.DataFrame, *alvos: str) -> Optional[str]:
    m = {c: norm_text(c) for c in df.columns}
    # igual
    for alvo in alvos:
        a = norm_text(alvo)
        for c, n in m.items():
            if n == a:
                return c
    # começa com
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
    """
    Retorna:
      - agg_serv: DF agregado por lançamento (lancamento, valor_bi)
      - cfop_series: Série CFOP (se existir)
      - missing_matrix_srv: matriz CFOP × tipos serviço, marcando FALTA/OK
    """
    df = read_excel_best(file)
    cfop_col = _find_col(df, "cfop")
    cfop_series = pd.Series([], dtype="object")
    if cfop_col:
        cfop_series = df[cfop_col].map(clean_code)

    stacks = []
    present_code_cols = []
    # presença por linha para construir matriz de lacunas
    pres_cols = {}  # label -> boolean series
    for code_label, val_opts, lbl in SERV_COLS:
        c_cod = _find_col(df, code_label, code_label.replace(".", " ").replace("  ", " "))
        c_val = None
        # achar uma das colunas de valor aproximadas
        for vname in val_opts:
            c_val = c_val or _find_col(df, vname, vname.replace(".", " ").replace("  ", " "))
        if c_cod and c_val:
            present_code_cols.append(c_cod)
            # presença por linha (se existe algum código não-vazio)
            pres_cols[lbl] = ~df[c_cod].map(is_empty_code)
            tmp = pd.DataFrame({
                "lancamento": df[c_cod].map(clean_code),
                "valor": df[c_val].map(to_number_br),
            })
            tmp = tmp[(tmp["lancamento"] != "") & (tmp["valor"].notna())]
            stacks.append(tmp)

    if not stacks:
        raise ValueError("Não encontrei nenhuma dupla código/valor do BI de Serviços.")

    long = pd.concat(stacks, ignore_index=True)
    long["valor"] = long["valor"].fillna(0.0).astype(float)
    agg = (long.groupby("lancamento", as_index=False)["valor"]
               .sum()
               .rename(columns={"valor": "valor_bi"}))

    # --- matriz de lacunas por CFOP (se CFOP existe)
    missing_matrix_srv = pd.DataFrame()
    if not cfop_series.empty and pres_cols:
        aux = pd.DataFrame({"CFOP": cfop_series.map(clean_code)})
        for lbl, ser in pres_cols.items():
            aux[lbl] = ser.fillna(False).astype(bool)
        aux = aux[aux["CFOP"] != ""]
        grp = aux.groupby("CFOP").agg({lbl:"any" for lbl in pres_cols}).reset_index()
        # marcar FALTA/OK para cada coluna
        label_order = ["doc","cofins","pis","iss","iss_ret","irrf","pis_ret","cofins_ret","inss_ret","csll_ret"]
        col_map = {
            "doc":"Documento","cofins":"Cofins","pis":"PIS","iss":"ISS",
            "iss_ret":"ISS Ret.","irrf":"IRRF","pis_ret":"PIS Ret.",
            "cofins_ret":"COFINS Ret.","inss_ret":"INSS Ret.","csll_ret":"CSLL Ret."
        }
        out = grp[["CFOP"]].copy()
        for lbl in label_order:
            if lbl in grp.columns:
                out[col_map[lbl]] = np.where(grp[lbl], "OK", "FALTA")
            else:
                out[col_map[lbl]] = "FALTA"
        # apenas CFOPs com alguma falta
        mask_any = (out.drop(columns=["CFOP"]) == "FALTA").any(axis=1)
        missing_matrix_srv = out[mask_any].sort_values("CFOP")

    return agg, cfop_series, missing_matrix_srv

# ============================================================
# Razão TXT (CSV por vírgula; usa col.2=código, col.4=valor, col.8=descrição)
# ============================================================
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

# ============================================================
# Comparação
# ============================================================
def compare(bi: pd.DataFrame, razao: pd.DataFrame) -> pd.DataFrame:
    comp = bi.merge(razao, on="lancamento", how="outer")
    comp["valor_bi"] = comp["valor_bi"].fillna(0.0)
    comp["valor_razao"] = comp["valor_razao"].fillna(0.0)
    comp["dif"] = comp["valor_bi"] - comp["valor_razao"]
    comp["ok"] = np.isclose(comp["dif"], 0.0, atol=0.01)
    cols = ["lancamento", "descricao", "valor_bi", "valor_razao", "dif", "ok"]
    if "descricao" not in comp.columns:
        comp["descricao"] = ""
    return comp.reindex(columns=cols).sort_values(["ok","lancamento"], ascending=[True, True])

# ============================================================
# Interface
# ============================================================
st.title("🔎 Conferência BI (Entradas/Saídas/Serviços) × Razão (TXT)")
st.caption("Usa TODOS os códigos de lançamento; Razão via TXT (col. 2=código, col. 4=valor, col. 8=descrição). Inclui lacunas por CFOP.")

c1, c2, c3 = st.columns(3)
with c1:
    bi_ent = st.file_uploader("📥 BI Entradas (.xls/.xlsx)", type=["xls","xlsx"], key="bi_ent")
with c2:
    bi_sai = st.file_uploader("📤 BI Saídas (.xls/.xlsx)", type=["xls","xlsx"], key="bi_sai")
with c3:
    bi_srv = st.file_uploader("🧾 BI Serviços (.xls/.xlsx)", type=["xls","xlsx"], key="bi_srv")

razao_files = st.file_uploader("📚 Razões TXT (pode enviar vários)", type=["txt"], accept_multiple_files=True)

st.divider()

# ---- Processar BIs
bi_parts: List[pd.DataFrame] = []
lacunas_es_parts: List[pd.DataFrame] = []  # Entradas/Saídas
lacunas_srv_tbl = pd.DataFrame()

# Entradas
if bi_ent is not None:
    try:
        bi_df_ent, cfop_ent = load_bi(bi_ent)
        agg_ent = aggregate_bi_all(bi_df_ent)
        agg_ent["origem"] = "entradas"
        bi_parts.append(agg_ent)

        faltas_ent = cfop_missing_matrix_es(bi_df_ent, cfop_ent)
        if not faltas_ent.empty:
            faltas_ent.insert(0, "Origem", "Entradas")
            lacunas_es_parts.append(faltas_ent)

        st.success("BI Entradas carregado.")
    except Exception as e:
        st.error(f"Erro no BI Entradas: {e}")

# Saídas
if bi_sai is not None:
    try:
        bi_df_sai, cfop_sai = load_bi(bi_sai)
        agg_sai = aggregate_bi_all(bi_df_sai)
        agg_sai["origem"] = "saidas"
        bi_parts.append(agg_sai)

        faltas_sai = cfop_missing_matrix_es(bi_df_sai, cfop_sai)
        if not faltas_sai.empty:
            faltas_sai.insert(0, "Origem", "Saídas")
            lacunas_es_parts.append(faltas_sai)

        st.success("BI Saídas carregado.")
    except Exception as e:
        st.error(f"Erro no BI Saídas: {e}")

# Serviços
if bi_srv is not None:
    try:
        agg_srv, cfop_srv, faltas_srv = load_bi_servico(bi_srv)  # já traz matriz de lacunas se houver CFOP
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

bi_total = (pd.concat(bi_parts, ignore_index=True)
              .groupby("lancamento", as_index=False)["valor_bi"]
              .sum())

st.subheader("📊 BI — Soma por Lançamento")
st.dataframe(bi_total, use_container_width=True, height=280)

# ---- Tabela de lacunas (CFOP x Lançamento)
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

# ---- Processar Razões
if not razao_files:
    st.info("Envie ao menos um arquivo TXT de Razão.")
    st.stop()

razoes = []
for f in razao_files:
    try:
        rz = read_razao_txt(f)
        rz["arquivo"] = f.name
        razoes.append(rz)
        st.markdown(f"**{f.name}**")
        st.dataframe(rz, use_container_width=True, height=200)
    except Exception as e:
        st.error(f"Erro lendo TXT {f.name}: {e}")

razao_total = (pd.concat(razoes, ignore_index=True)
                 .groupby("lancamento", as_index=False)["valor_razao"]
                 .sum()
                 .merge(
                     pd.concat(razoes, ignore_index=True)[["lancamento", "descricao"]]
                     .dropna()
                     .drop_duplicates("lancamento"),
                     on="lancamento", how="left"
                 ))

st.subheader("📒 Razão consolidado (todos TXT)")
st.dataframe(razao_total, use_container_width=True, height=240)

st.divider()

# ---- Comparação
st.subheader("✅ Comparação BI × Razão por Lançamento")
comp = compare(bi_total, razao_total)

c1, c2, c3 = st.columns(3)
c1.metric("Lançamentos BI", f"{len(bi_total)}")
c2.metric("Lançamentos Razão", f"{len(razao_total)}")
c3.metric("Divergências", f"{(~comp['ok']).sum()}")

# Estilo: APENAS a coluna 'dif' (verde=ok, vermelho=diverge)
styled = (
    comp.style
        .format({"valor_bi": "{:,.2f}", "valor_razao": "{:,.2f}", "dif": "{:,.2f}"})
        .apply(
            lambda s: pd.Series(
                np.where(comp["ok"], "color:green", "color:red"),
                index=comp.index
            ),
            subset=["dif"]
        )
)

st.dataframe(styled, use_container_width=True, height=420)

st.caption("Regras: limpeza de códigos considera 'Não possui'/'x' como vazio, remove '.0' e zeros espúrios à direita; valores aceitam vírgula decimal e parênteses como negativo; tolerância |dif| ≤ 0,01. Descrição: trecho da coluna 8 até o primeiro número.")
