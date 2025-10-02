"""
Módulo para processamento de arquivos de Razão (TXT).
Responsável por ler, limpar e processar dados de razão contábil.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from utils import clean_code_main, to_number_br_main, extract_desc_before_first_digit_main


# =============================================================================
# Constantes - Códigos de Serviços Prestados
# =============================================================================
CODIGOS_SERVICOS_PRESTADOS = {
    "00141", "00142", "00143", "80083", "80514",
    "80535", "80107", "00000", "00406"
}


# =============================================================================
# Funções de Processamento de Razão
# =============================================================================
def read_razao_txt(file) -> pd.DataFrame:
    """Lê arquivo TXT de razão e processa os dados."""
    df = pd.read_csv(file, sep=",", header=None, engine="python", dtype=str)
    cod = df.iloc[:, 1].map(clean_code_main)
    val = df.iloc[:, 3].map(to_number_br_main)
    desc = df.iloc[:, 7].map(extract_desc_before_first_digit_main) if df.shape[1] >= 8 else ""

    out = pd.DataFrame({
        "lancamento": cod,
        "valor_razao": val,
        "descricao": desc
    })
    out = out[out["lancamento"] != ""]

    soma = out.groupby("lancamento", as_index=False)["valor_razao"].sum()
    desc1 = (out[out["descricao"].astype(str).str.len() > 0]
                .drop_duplicates(subset=["lancamento"], keep="first")[["lancamento", "descricao"]])
    razao_agg = soma.merge(desc1, on="lancamento", how="left")
    return razao_agg


def consolidate_razao_files(razao_files: List) -> pd.DataFrame:
    """Consolida múltiplos arquivos TXT de razão."""
    if not razao_files:
        return pd.DataFrame(columns=["lancamento", "valor_razao", "descricao"])

    razoes = []
    for f in razao_files:
        try:
            rz = read_razao_txt(f)
            rz["arquivo"] = f.name
            razoes.append(rz)
        except Exception as e:
            raise ValueError(f"Erro lendo TXT {f.name}: {e}")

    if not razoes:
        return pd.DataFrame(columns=["lancamento", "valor_razao", "descricao"])

    razao_total = (
        pd.concat(razoes, ignore_index=True)
          .groupby("lancamento", as_index=False)["valor_razao"].sum()
          .merge(
              pd.concat(razoes, ignore_index=True)[["lancamento", "descricao"]]
                .dropna().drop_duplicates("lancamento"),
              on="lancamento", how="left"
          )
    )
    return razao_total


# =============================================================================
# Funções de Comparação BI vs Razão
# =============================================================================
def compare_bi_vs_razao(bi: pd.DataFrame, razao: pd.DataFrame) -> pd.DataFrame:
    """Compara dados do BI com dados do Razão."""
    comp = bi.merge(razao, on="lancamento", how="outer")
    comp["valor_bi"] = comp["valor_bi"].fillna(0.0)
    comp["valor_razao"] = comp["valor_razao"].fillna(0.0)
    comp["dif"] = comp["valor_bi"] - comp["valor_razao"]
    comp["ok"] = np.isclose(comp["dif"], 0.0, atol=0.01)

    if "descricao" not in comp.columns:
        comp["descricao"] = ""

    cols = ["lancamento", "descricao", "valor_bi", "valor_razao", "dif", "ok"]
    return comp.reindex(columns=cols).sort_values(["ok", "lancamento"], ascending=[True, True])


def calculate_comparison_metrics(comp: pd.DataFrame, bi_total: pd.DataFrame, razao_total: pd.DataFrame) -> Dict[str, int]:
    """Calcula métricas da comparação BI vs Razão."""
    bi_count = int(len(bi_total))
    razao_count = int(len(razao_total))
    ok_count = int(comp.get("ok", pd.Series([], dtype=bool)).sum())
    div_count = int((~comp.get("ok", pd.Series([], dtype=bool))).sum())

    return {
        "bi_count": bi_count,
        "razao_count": razao_count,
        "ok_count": ok_count,
        "div_count": div_count
    }


def is_comparison_perfect(metrics: Dict[str, int]) -> bool:
    """Verifica se a comparação está perfeita (sem divergências)."""
    return metrics["div_count"] == 0 and metrics["ok_count"] > 0


# =============================================================================
# Funções para Filtrar Serviços Prestados
# =============================================================================
def filter_servicos_prestados(razao_total: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Separa lançamentos de serviços prestados do razão principal.

    Args:
        razao_total: DataFrame com dados do razão consolidado

    Returns:
        tuple: (razao_sem_servicos, razao_servicos)
            - razao_sem_servicos: DataFrame sem os códigos de serviços
            - razao_servicos: DataFrame apenas com os códigos de serviços
    """
    if razao_total.empty:
        return razao_total, pd.DataFrame(columns=razao_total.columns)

    # Criar máscara para identificar serviços prestados
    mask_servicos = razao_total["lancamento"].isin(CODIGOS_SERVICOS_PRESTADOS)

    # Separar em dois DataFrames
    razao_servicos = razao_total[mask_servicos].copy()
    razao_sem_servicos = razao_total[~mask_servicos].copy()

    # Renomear e reordenar colunas para exibição
    if not razao_servicos.empty:
        razao_servicos = razao_servicos.rename(columns={
            "lancamento": "Lançamento",
            "descricao": "Descrição",
            "valor_razao": "Valor"
        })
        # Reordenar colunas: Lançamento | Descrição | Valor
        cols_order = ["Lançamento", "Descrição", "Valor"]
        razao_servicos = razao_servicos[[c for c in cols_order if c in razao_servicos.columns]]

    return razao_sem_servicos, razao_servicos