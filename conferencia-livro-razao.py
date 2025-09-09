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
def norm_text(s: str) -> str:
    s = str(s).strip().lower()
    s = (s.replace("ã", "a").replace("á", "a").replace("à", "a").replace("â", "a")
           .replace("ç", "c").replace("é", "e").replace("ê", "e")
           .replace("í", "i").replace("ó", "o").replace("ô", "o").replace("ú", "u"))
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def clean_code(x: str) -> str:
    """
    Mantém só dígitos, remove '.0' e corrige zeros espúrios à direita.
    Ex.: '10015.0' -> '10015', '100010' -> '10001', '001410' -> '00141'
    """
    if x is None:
        return ""
    s = str(x).strip()
    if s == "":
        return ""
    s = re.sub(r"[^0-9]", "", s)      # somente dígitos
    s = re.sub(r"\.0+$", "", s)       # tira .0 se houver
    # Enquanto tiver >5 dígitos e terminar com '0', corta 1 zero (Excel esticado)
    while len(s) > 5 and s.endswith("0"):
        s = s[:-1]
    return s

def to_number_br(v) -> float:
    """Converte '226.755,32' -> 226755.32; aceita '(123,45)' como negativo."""
    if v is None:
        return 0.0
    s = str(v).strip()
    if s == "":
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
def detect_bi_columns(df: pd.DataFrame) -> Dict[str, str]:
    mapping = {c: norm_text(c) for c in df.columns}
    aliases = {
        "la_cont": ["lanc cont vl contabil", "lanc cont vl"],
        "la_icms": ["lanc cont vl icms"],
        "la_st":   ["lanc cont vl subst trib", "lanc cont vl icms st"],
        "la_ipi":  ["lanc cont vl ipi"],
        "v_cont":  ["valor contabil"],
        "v_icms":  ["vl icms"],
        "v_st":    ["vl subst trib", "vl icms st", "vl st"],
        "v_ipi":   ["vl ipi"],
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
    missing = [k for k, v in cols.items() if v is None]
    if missing:
        raise ValueError(f"Colunas do BI ausentes: {missing}")
    return cols  # type: ignore[return-value]

def load_bi(file) -> pd.DataFrame:
    df = read_excel_best(file)
    cols = detect_bi_columns(df)
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
    # reforço de limpeza para evitar zeros espúrios
    for c in ["la_cont", "la_icms", "la_st", "la_ipi"]:
        out[c] = out[c].map(clean_code)
    return out

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

def load_bi_servico(file) -> pd.DataFrame:
    """
    Códigos (lançamentos):
      Lanc Cont. Valor Documento | Lanc.Cont.Vl.Cofins | Lanc.Cont.Vl.PIS |
      Lanc Cont. Vl. ISS | Lanc Cont. Vl. ISS Ret. | Lanc Cont. Vl. IRRF |
      Lanc Cont. Vl. PIS Ret. | Lanc Cont. Vl. COFINS Ret. |
      Lanc Cont. Vl. INSS Ret. | Lanc Cont. Vl. CSLL Ret.
    Valores:
      Valor Documento | Vl. Cofins | Vl. PIS | Vl. ISS | Vl. ISS Ret. | Vl. IRRF |
      Vl. PIS Ret. | Vl. COFINS Ret. | Vl. INSS Ret. | Vl. CSLL Ret.
    """
    df = read_excel_best(file)

    pares: List[Tuple[List[str], List[str], str]] = [
        (["Lanc Cont. Valor Documento", "Lanc Cont. Vl. Valor Documento", "Lanc Cont Valor Documento"],
         ["Valor Documento"], "doc"),
        (["Lanc.Cont.Vl.Cofins", "Lanc Cont. Vl. Cofins", "Lanc Cont Vl Cofins"],
         ["Vl. Cofins"], "cofins"),
        (["Lanc.Cont.Vl.PIS", "Lanc Cont. Vl. PIS", "Lanc Cont Vl PIS"],
         ["Vl. PIS"], "pis"),
        (["Lanc Cont. Vl. ISS", "Lanc Cont Vl ISS"],
         ["Vl. ISS"], "iss"),
        (["Lanc Cont. Vl. ISS Ret.", "Lanc Cont Vl ISS Ret"],
         ["Vl. ISS Ret.", "Vl ISS Ret"], "iss_ret"),
        (["Lanc Cont. Vl. IRRF", "Lanc Cont Vl IRRF"],
         ["Vl. IRRF", "Vl IRRF"], "irrf"),
        (["Lanc Cont. Vl. PIS Ret.", "Lanc Cont Vl PIS Ret"],
         ["Vl. PIS Ret.", "Vl PIS Ret"], "pis_ret"),
        (["Lanc Cont. Vl. COFINS Ret.", "Lanc Cont Vl COFINS Ret"],
         ["Vl. COFINS Ret.", "Vl COFINS Ret"], "cofins_ret"),
        (["Lanc Cont. Vl. INSS Ret.", "Lanc Cont Vl INSS Ret"],
         ["Vl. INSS Ret.", "Vl INSS Ret"], "inss_ret"),
        (["Lanc Cont. Vl. CSLL Ret.", "Lanc Cont Vl CSLL Ret"],
         ["Vl. CSLL Ret.", "Vl CSLL Ret"], "csll_ret"),
    ]

    stacks = []
    for cod_opts, val_opts, _rot in pares:
        c_cod = _find_col(df, *cod_opts)
        c_val = _find_col(df, *val_opts)
        if c_cod and c_val:
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
    return (long.groupby("lancamento", as_index=False)["valor"]
                .sum()
                .rename(columns={"valor": "valor_bi"}))

# ============================================================
# Razão TXT (CSV por vírgula; usa col.2=código, col.4=valor, col.8=descrição)
# ============================================================
def read_razao_txt(file) -> pd.DataFrame:
    """
    TXT como CSV por vírgula, com aspas. Usa:
      - coluna 2 (índice 1): código de lançamento
      - coluna 4 (índice 3): valor contábil
      - coluna 8 (índice 7): descrição bruta (somente trecho antes do 1º número)
    Consolida por lançamento somando o valor e pegando a 1ª descrição não vazia.
    """
    df = pd.read_csv(file, sep=",", header=None, engine="python", dtype=str)

    cod  = df.iloc[:, 1].map(clean_code)
    val  = df.iloc[:, 3].map(to_number_br)
    desc = df.iloc[:, 7].map(extract_desc_before_first_digit) if df.shape[1] >= 8 else ""

    out = pd.DataFrame({"lancamento": cod, "valor_razao": val, "descricao": desc})
    out = out[out["lancamento"] != ""]

    # soma por lançamento
    soma = out.groupby("lancamento", as_index=False)["valor_razao"].sum()

    # 1ª descrição não vazia por lançamento
    desc1 = (out[out["descricao"].astype(str).str.len() > 0]
                .drop_duplicates(subset=["lancamento"], keep="first")[["lancamento", "descricao"]])

    razao_agg = soma.merge(desc1, on="lancamento", how="left")
    return razao_agg

# ============================================================
# Comparação
# ============================================================
def compare(bi: pd.DataFrame, razao: pd.DataFrame) -> pd.DataFrame:
    comp = bi.merge(razao, on="lancamento", how="outer")  # razao inclui 'descricao'
    comp["valor_bi"] = comp["valor_bi"].fillna(0.0)
    comp["valor_razao"] = comp["valor_razao"].fillna(0.0)
    comp["dif"] = comp["valor_bi"] - comp["valor_razao"]
    comp["ok"] = np.isclose(comp["dif"], 0.0, atol=0.01)
    cols = ["lancamento", "descricao", "valor_bi", "valor_razao", "dif", "ok"]
    return comp.reindex(columns=cols).sort_values(["ok", "lancamento"], ascending=[True, True])

# ============================================================
# Interface
# ============================================================
st.title("🔎 Conferência BI (Entradas/Saídas/Serviços) × Razão (TXT)")
st.caption("Usa TODOS os códigos de lançamento; Razão via TXT (col. 2=código, col. 4=valor, col. 8=descrição). Python 3.12 + Streamlit.")

c1, c2, c3 = st.columns(3)
with c1:
    bi_ent = st.file_uploader("📥 BI Entradas (.xls/.xlsx)", type=["xls", "xlsx"], key="bi_ent")
with c2:
    bi_sai = st.file_uploader("📤 BI Saídas (.xls/.xlsx)", type=["xls", "xlsx"], key="bi_sai")
with c3:
    bi_srv = st.file_uploader("🧾 BI Serviços (.xls/.xlsx)", type=["xls", "xlsx"], key="bi_srv")

razao_files = st.file_uploader("📚 Razões TXT (pode enviar vários)", type=["txt"], accept_multiple_files=True)

st.divider()

# ---- Processar BIs
bi_parts: List[pd.DataFrame] = []

if bi_ent is not None:
    try:
        agg = aggregate_bi_all(load_bi(bi_ent))
        agg["origem"] = "entradas"
        bi_parts.append(agg)
        st.success("BI Entradas carregado.")
    except Exception as e:
        st.error(f"Erro no BI Entradas: {e}")

if bi_sai is not None:
    try:
        agg = aggregate_bi_all(load_bi(bi_sai))
        agg["origem"] = "saidas"
        bi_parts.append(agg)
        st.success("BI Saídas carregado.")
    except Exception as e:
        st.error(f"Erro no BI Saídas: {e}")

if bi_srv is not None:
    try:
        agg = load_bi_servico(bi_srv)  # já retorna (lancamento, valor_bi)
        agg["origem"] = "servicos"
        bi_parts.append(agg)
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
st.dataframe(bi_total, use_container_width=True, height=300)

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
        st.dataframe(rz, use_container_width=True, height=220)
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
st.dataframe(razao_total, use_container_width=True, height=260)

st.divider()

# ---- Comparação
st.subheader("✅ Comparação BI × Razão por Lançamento")

comp = compare(bi_total, razao_total)

c1, c2, c3 = st.columns(3)
c1.metric("Lançamentos BI", f"{len(bi_total)}")
c2.metric("Lançamentos Razão", f"{len(razao_total)}")
c3.metric("Divergências", f"{(~comp['ok']).sum()}")

# Estilo: verde quando ok, vermelho quando diverge
def _row_colors(row):
    color = "green" if row["ok"] else "red"
    return ["", "", f"color:{color}", f"color:{color}", f"color:{color}", ""]

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

st.dataframe(styled, use_container_width=True, height=460)
st.caption("Regras: limpeza dos códigos remove '.0' e zeros espúrios à direita; valores aceitam vírgula decimal e parênteses como negativo; tolerância |dif| ≤ 0,01. Descrição: trecho da coluna 8 até o primeiro número.")
