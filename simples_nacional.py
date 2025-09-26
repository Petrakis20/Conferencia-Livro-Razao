"""
Módulo para processamento do Livro de ICMS x Lote Contábil.
Responsável por processar PDFs e TXTs do Livro de ICMS x Lote Contábil.
"""

import io
import os
import re
import csv
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from utils import clean_code_main, to_number_br_main, format_brazilian_number
from sn_pdf import (
    parse_livro_icms_pdf_entradas,
    parse_livro_icms_pdf_saidas,
    parse_livro_icms_st_pdf,
)


# =============================================================================
# Funções de Processamento de PDF
# =============================================================================
def process_icms_pdf(pdf_file, base_map: Dict[str, Dict]) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """Processa PDF de ICMS (Entradas + Saídas)."""
    if pdf_file is None:
        return pd.DataFrame(), pd.DataFrame(), []

    try:
        df_ent = parse_livro_icms_pdf_entradas(pdf_file, keep_numeric=True)
        df_sai = parse_livro_icms_pdf_saidas(pdf_file, keep_numeric=True)
    except Exception as e:
        raise ValueError(f"Falha ao ler o PDF (ICMS): {e}")

    # Combina E+S numéricos por CFOP
    e_num = (df_ent[["CFOP","Valor Contábil (num)","Imposto Creditado (num)"]]
             .rename(columns={"Valor Contábil (num)":"vc_num",
                              "Imposto Creditado (num)":"icms_num"})
             if not df_ent.empty else pd.DataFrame(columns=["CFOP","vc_num","icms_num"]))

    s_num = (df_sai[["CFOP","Valor Contábil (num)","Imposto Debitado (num)"]]
             .rename(columns={"Valor Contábil (num)":"vc_num",
                              "Imposto Debitado (num)":"icms_num"})
             if not df_sai.empty else pd.DataFrame(columns=["CFOP","vc_num","icms_num"]))

    # Agregado de Imposto Debitado (somente SAÍDAS) para o LOG
    s_deb_agg = (df_sai[["CFOP","Imposto Debitado (num)"]]
                 .rename(columns={"Imposto Debitado (num)":"imposto_debitado_num"})
                 .groupby("CFOP", as_index=False)["imposto_debitado_num"].sum()
                 if not df_sai.empty else pd.DataFrame(columns=["CFOP","imposto_debitado_num"]))

    both = pd.concat([e_num, s_num], ignore_index=True)

    if both.empty:
        return pd.DataFrame(), pd.DataFrame(), []

    # Soma E+S por CFOP
    both = both.groupby("CFOP", as_index=False)[["vc_num","icms_num"]].sum()

    # LOG: Contábil (E+S) vs Imposto Debitado (S)
    log_df = (both.merge(s_deb_agg, on="CFOP", how="left")
                    .fillna({"imposto_debitado_num": 0.0}))
    log_df["Valor Contábil"] = log_df["vc_num"].map(format_brazilian_number)
    log_df["Imposto Debitado"] = log_df["imposto_debitado_num"].map(format_brazilian_number)

    # Saída normal do pipeline
    df_pdf_extr = both.assign(
        **{
            "Valor Contábil": both["vc_num"].map(format_brazilian_number),
            "Imposto Creditado": both["icms_num"].map(format_brazilian_number),
        }
    )[["CFOP","Valor Contábil","Imposto Creditado"]].copy()

    # Mapeia CFOP → lançamentos via base
    pdf_lanc_tot = pd.DataFrame(columns=["lancamento","valor"])
    comp_map = {}
    cfop_sem_mapa = []

    if not both.empty and base_map:
        rows = []
        for _, r in both.iterrows():
            cfop = clean_code_main(r["CFOP"])
            mapa = base_map.get(cfop) or {}
            lc = clean_code_main(mapa.get("contabil") or "")
            li = clean_code_main(mapa.get("icms") or "")
            if lc:
                rows.append({"lancamento": lc, "valor": float(r["vc_num"])})
                comp_map.setdefault(lc, set()).add(cfop)
            if li:
                rows.append({"lancamento": li, "valor": float(r["icms_num"])})
                comp_map.setdefault(li, set()).add(cfop)
            if not lc and not li:
                cfop_sem_mapa.append(cfop)

        if rows:
            pdf_lanc_tot = pd.DataFrame(rows).groupby("lancamento", as_index=False)["valor"].sum()

    return pdf_lanc_tot, log_df, cfop_sem_mapa


def process_icms_st_pdf(pdf_file_st, base_map: Dict[str, Dict]) -> Tuple[pd.DataFrame, List[str]]:
    """Processa PDF de ICMS ST."""
    if pdf_file_st is None or not base_map:
        return pd.DataFrame(columns=["lancamento","valor"]), []

    try:
        df_st = parse_livro_icms_st_pdf(pdf_file_st, keep_numeric=True)
        df_st["total_st_num"] = df_st.get("total_st_num", 0.0)

        rows_st = []
        cfop_st_sem_mapa = []

        for _, r in df_st.iterrows():
            cf = clean_code_main(r["CFOP"])
            mapa = base_map.get(cf) or {}
            lanc_st = clean_code_main(mapa.get("icms_subst") or "")
            if lanc_st:
                val = float(r["total_st_num"])
                if val != 0.0:
                    rows_st.append({"lancamento": lanc_st, "valor": val})
            else:
                cfop_st_sem_mapa.append(cf)

        if rows_st:
            st_lanc_tot = pd.DataFrame(rows_st).groupby("lancamento", as_index=False)["valor"].sum()
        else:
            st_lanc_tot = pd.DataFrame(columns=["lancamento","valor"])

        return st_lanc_tot, cfop_st_sem_mapa

    except Exception as e:
        raise ValueError(f"Falha ao ler o PDF de ICMS ST: {e}")


# =============================================================================
# Funções de Processamento de TXT
# =============================================================================
def parse_txt_lancamento_valor_desc(txt_file) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Retorna:
      - df_val : lancamento | valor
      - df_desc: lancamento | descricao
    Lê CSV/TXT com delimitador ',', ';', '\t' ou '|', respeitando aspas.
    """
    def _read_bytes(f):
        if f is None:
            return b""
        if hasattr(f, "read"):
            b = f.read()
            try:
                f.seek(0)
            except Exception:
                pass
            return b
        if isinstance(f, (bytes, bytearray)):
            return bytes(f)
        if isinstance(f, str) and os.path.exists(f):
            with open(f, "rb") as fh:
                return fh.read()
        return b""

    raw = _read_bytes(txt_file)
    if not raw:
        return (pd.DataFrame(columns=["lancamento","valor"]),
                pd.DataFrame(columns=["lancamento","descricao"]))

    text = None
    for enc in ("utf-8-sig","utf-8","latin-1","cp1252"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        return (pd.DataFrame(columns=["lancamento","valor"]),
                pd.DataFrame(columns=["lancamento","descricao"]))

    sample = text[:2000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",",";","\t","|"])
        delim = dialect.delimiter
    except Exception:
        delim = ";" if sample.count(";") > sample.count(",") else ","

    reader = csv.reader(io.StringIO(text), delimiter=delim, quotechar='"', skipinitialspace=True)

    def br_to_float(s: str) -> float:
        if s is None:
            return 0.0
        s = str(s).strip().strip('"').strip()
        neg = s.startswith("(") and s.endswith(")")
        if neg:
            s = s[1:-1]
        s = s.replace(".", "").replace("\u00A0", "").replace(" ", "").replace(",", ".")
        m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
        v = float(m.group(0)) if m else 0.0
        return -v if neg and v > 0 else v

    def only_text_until_first_digit(s: str) -> str:
        if s is None:
            return ""
        s = str(s).strip()
        parts = re.split(r"\d", s, maxsplit=1)
        head = parts[0] if parts else s
        head = head.replace(";", " ").strip(" -–—:•\t").strip()
        return " ".join(head.split())

    vals, descs = [], []
    for row in reader:
        if not row or len(row) < 8:
            continue
        lanc = clean_code_main(row[1])     # coluna 2
        if lanc == "":
            continue
        val = br_to_float(row[3])    # coluna 4
        vals.append({"lancamento": lanc, "valor": float(val)})

        desc = only_text_until_first_digit(row[7])  # coluna 8
        if desc:
            descs.append({"lancamento": lanc, "descricao": desc})

    if vals:
        df_val = pd.DataFrame(vals).groupby("lancamento", as_index=False)["valor"].sum()
    else:
        df_val = pd.DataFrame(columns=["lancamento","valor"])

    if descs:
        df_desc = (pd.DataFrame(descs)
                   .sort_values(["lancamento", "descricao"], key=lambda s: s.str.len(), ascending=False)
                   .drop_duplicates("lancamento"))
    else:
        df_desc = pd.DataFrame(columns=["lancamento","descricao"])

    return df_val, df_desc


# =============================================================================
# Funções de Comparação
# =============================================================================
def compare_simples_nacional(pdf_icms: pd.DataFrame, pdf_icms_st: pd.DataFrame,
                           txt_lanc_tot: pd.DataFrame, txt_desc: pd.DataFrame,
                           comp_map_union: Dict) -> pd.DataFrame:
    """Compara dados do Livro de ICMS x Lote Contábil: PDF (ICMS + ST) vs TXT."""
    # Composição por lançamento
    comp_cfop_union = (
        pd.DataFrame([{"lancamento": k, "cfops": ", ".join(sorted(v))} for k, v in comp_map_union.items()])
        if comp_map_union else pd.DataFrame(columns=["lancamento","cfops"])
    )

    # Comparação final
    pdf_icms_renamed = (pdf_icms.rename(columns={"valor": "Livro ICMS"})
                       if not pdf_icms.empty else pd.DataFrame(columns=["lancamento","Livro ICMS"]))
    pdf_icms_st_renamed = (pdf_icms_st.rename(columns={"valor": "Livro ICMS ST"})
                          if not pdf_icms_st.empty else pd.DataFrame(columns=["lancamento","Livro ICMS ST"]))

    comp = pd.merge(pdf_icms_renamed, pdf_icms_st_renamed, on="lancamento", how="outer")
    comp = pd.merge(comp, txt_lanc_tot.rename(columns={"valor":"Lote Contábil"}), on="lancamento", how="outer")
    comp = pd.merge(comp, comp_cfop_union, on="lancamento", how="left")
    comp = pd.merge(comp, txt_desc, on="lancamento", how="left")

    for c in ["Livro ICMS","Livro ICMS ST","Lote Contábil"]:
        if c in comp.columns:
            comp[c] = comp[c].fillna(0.0).astype(float)

    comp["Diferença"] = comp["Lote Contábil"] - (comp["Livro ICMS"].fillna(0.0) + comp["Livro ICMS ST"].fillna(0.0))

    tol = 0.01
    comp["Status"] = np.where(
        comp["Diferença"].abs() <= tol, "OK ✅",
        np.where(
            ((comp["Livro ICMS"].fillna(0)+comp["Livro ICMS ST"].fillna(0)) > 0) & (comp["Lote Contábil"] == 0), "Ausente no TXT",
            np.where(
                ((comp["Livro ICMS"].fillna(0)+comp["Livro ICMS ST"].fillna(0)) == 0) & (comp["Lote Contábil"] > 0), "Extra no TXT",
                "Diferente ❌"
            )
        )
    )

    comp.rename(columns={"lancamento": "Lançamento",
                         "cfops": "Composição do Lançamento (CFOP)",
                         "descricao": "Descrição"}, inplace=True)

    cols_final = ["Composição do Lançamento (CFOP)", "Lançamento", "Descrição",
                  "Livro ICMS", "Livro ICMS ST", "Lote Contábil", "Diferença", "Status"]
    comp = comp.reindex(columns=[c for c in cols_final if c in comp.columns]).sort_values("Lançamento")

    return comp


def calculate_simples_nacional_metrics(comp: pd.DataFrame, pdf_icms: pd.DataFrame,
                                     pdf_icms_st: pd.DataFrame, txt_lanc_tot: pd.DataFrame) -> Dict[str, int]:
    """Calcula métricas do Livro de ICMS x Lote Contábil."""
    pdf_lanc_count = int(len(set(pdf_icms.get("lancamento", pd.Series([]))) |
                            set(pdf_icms_st.get("lancamento", pd.Series([])))))
    ok_count = int((comp["Status"]=="OK ✅").sum())
    div_count = int(len(comp) - ok_count)
    rz_count = int(txt_lanc_tot.shape[0])

    return {
        "pdf_lanc_count": pdf_lanc_count,
        "ok_count": ok_count,
        "div_count": div_count,
        "rz_count": rz_count
    }


def is_simples_nacional_perfect(metrics: Dict[str, int]) -> bool:
    """Verifica se a análise do Livro de ICMS x Lote Contábil está perfeita."""
    return metrics["div_count"] == 0 and metrics["ok_count"] > 0