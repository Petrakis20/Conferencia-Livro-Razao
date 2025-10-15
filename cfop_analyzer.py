"""
Módulo para análise e comparação de CFOP com base de dados.
Responsável por validar códigos de lançamento contra a base CFOP.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from utils import clean_code_main


# =============================================================================
# Funções de Carregamento da Base CFOP
# =============================================================================
def load_base_json(path: Path) -> Dict[str, Dict]:
    """Carrega base de CFOP do arquivo JSON."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# Funções de Comparação CFOP
# =============================================================================
def normalize_code_cfop(val: Optional[str]) -> Optional[str]:
    """Normaliza códigos garantindo que None/NaN sejam tratados."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s and s.lower() != "nan" else None


def compare_row(cfop_code: str, row: Dict[str, Optional[str]], base_map: Dict[str, Dict]) -> Tuple[str, str, Optional[Dict], Dict, Optional[str]]:
    """Compara uma linha do BI com a base CFOP."""
    cfop = normalize_code_cfop(cfop_code)
    found = {
        "contabil": normalize_code_cfop(row.get("contabil")),
        "icms": normalize_code_cfop(row.get("icms")),
        "icms_subst": normalize_code_cfop(row.get("icms_subst")),
        "ipi": normalize_code_cfop(row.get("ipi")),
    }
    base = base_map.get(str(cfop)) if cfop is not None else None

    # Verificar ausência de lançamento automático quando valor != 0 mas código está vazio
    # Pares: (chave_lancamento, chave_valor, label)
    pares_verificacao = [
        ("contabil", "valor_contabil", "Contábil"),
        ("icms", "vl_icms", "ICMS"),
        ("icms_subst", "vl_st", "ICMS Subst. Trib."),
        ("ipi", "vl_ipi", "IPI")
    ]

    ausencia_lancamento = []
    for lanc_key, valor_key, lbl in pares_verificacao:
        valor = row.get(valor_key)
        lancamento = found.get(lanc_key)

        # Verifica se o valor é diferente de zero e não vazio
        valor_existe = False
        if valor is not None:
            try:
                valor_num = float(valor)
                valor_existe = valor_num != 0.0
            except (ValueError, TypeError):
                valor_existe = False

        # Se valor existe (!=0) mas lançamento está vazio -> ausência de lançamento automático
        if valor_existe and lancamento is None:
            ausencia_lancamento.append(f"{lbl}: valor {valor} sem lançamento automático")

    if base is None:
        # Se CFOP não está na base, mas há valores sem lançamento, marcar como ausência
        if ausencia_lancamento:
            status = "🟡 Ausência de lançamento automático"
            details = "; ".join(ausencia_lancamento)
        else:
            status = "⚠️ CFOP não cadastrado"
            details = "CFOP não existe na base."
        expected = None
    else:
        expected = {
            "contabil": normalize_code_cfop(base.get("contabil")),
            "icms": normalize_code_cfop(base.get("icms")),
            "icms_subst": normalize_code_cfop(base.get("icms_subst")),
            "ipi": normalize_code_cfop(base.get("ipi")),
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

        # Prioridade: mismatches > ausência de lançamento > zeros > OK
        if mismatches:
            status = "❌ Código de lançamento incorreto"
            det = "; ".join(mismatches + zeros)
            details = f"{det}" + (f"  •  Valores (BI): {resumo_valores}" if resumo_valores else "")
        elif ausencia_lancamento:
            # Nova condição: ausência de lançamento automático quando valor != 0
            status = "🟡 Ausência de lançamento automático"
            details = "; ".join(ausencia_lancamento + zeros) + (f"  •  Valores (BI): {resumo_valores}" if resumo_valores else "")
        elif zeros:
            status = "🟡 Ausência de lançamento automático"
            details = "; ".join(zeros) + (f"  •  Valores (BI): {resumo_valores}" if resumo_valores else "")
        else:
            status = "OK"
            details = "Tudo certo conforme a base."

    nome = None if base is None else base.get("nome")
    return status, details, expected, found, nome


def analyze_bi_against_base(bi_df: pd.DataFrame, base_map: Dict[str, Dict]) -> pd.DataFrame:
    """Analisa todo o BI contra a base CFOP."""
    results = []
    for _, r in bi_df.iterrows():
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

        # Sempre incluir os valores do BI no Resultado da Validação
        for k, label in (
            ("valor_contabil", "Valor Contábil"),
            ("vl_icms",       "Vl. ICMS"),
            ("vl_st",         "Vl. ST"),
            ("vl_ipi",        "Vl. IPI"),
        ):
            row_out[label] = r.get(k) if k in bi_df.columns else None

        results.append(row_out)

    out_df = pd.DataFrame(results)

    # Ordenar colunas
    col_order = [
        "origem", "CFOP", "Nome (Base)", "Status", "Detalhes",
        "Esperado Contábil", "Encontrado Contábil","Valor Contábil",
        "Esperado ICMS", "Encontrado ICMS","Vl. ICMS",
        "Esperado ICMS Subst. Trib.", "Encontrado ICMS Subst. Trib.","Vl. ST",
        "Esperado IPI", "Encontrado IPI","Vl. IPI"
    ]
    out_df = out_df.reindex(columns=[c for c in col_order if c in out_df.columns])

    return out_df


def calculate_analysis_metrics(result_df: pd.DataFrame) -> Dict[str, int]:
    """Calcula métricas da análise CFOP."""
    ok_count = int((result_df["Status"] == "OK").sum())
    diff_count = int((result_df["Status"] == "❌ Código de lançamento incorreto").sum())
    zero_count = int((result_df["Status"] == "🟡 Ausência de lançamento automático").sum())
    notfound_count = int((result_df["Status"].str.contains("⚠️ CFOP não cadastrado", na=False)).sum())

    return {
        "ok_count": ok_count,
        "diff_count": diff_count,
        "zero_count": zero_count,
        "notfound_count": notfound_count
    }


def is_analysis_perfect(metrics: Dict[str, int]) -> bool:
    """Verifica se a análise está perfeita (sem divergências)."""
    return (metrics["diff_count"] == 0 and
            metrics["zero_count"] == 0 and
            metrics["notfound_count"] == 0 and
            metrics["ok_count"] > 0)