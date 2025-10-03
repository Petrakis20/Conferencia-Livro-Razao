# streamlit_app.py
# Python 3.12

from __future__ import annotations
from sn_pdf import (
    parse_livro_icms_pdf_entradas,
    parse_livro_icms_pdf_saidas,
    parse_livro_icms_st_pdf,   # <-- este é o novo
)

import json
import re, io, csv, os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

def kpi_card(title: str, value, bg="#ffffff", border="#e5e7eb", fg="#111827"):
    st.markdown(
        f"""
        <div style="
             border-radius:16px;
             padding:24px 28px;
             background:{bg};
             border:1px solid {border};
             box-shadow:0 4px 16px rgba(0,0,0,.06);
             height: 200px;
        ">
          <div style="font-weight:800;font-size:22px;line-height:1.2;margin-bottom:6px;">
            {title}
          </div>
          <div style="font-size:48px;font-weight:900;color:{fg};">
            {value}
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def trigger_fireworks():
    """Dispara animação de fogos de artifício com explosões de partículas quando todas as análises estão OK"""
    st.markdown(
        """
        <style>
        @keyframes particle-explode {
            0% {
                transform: translate(0, 0) scale(1);
                opacity: 1;
            }
            100% {
                transform: translate(var(--dx), var(--dy)) scale(0);
                opacity: 0;
            }
        }

        @keyframes rocket-launch {
            0% {
                transform: translateY(100vh);
                opacity: 1;
            }
            100% {
                transform: translateY(var(--target-y));
                opacity: 0;
            }
        }

        .firework-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: 9999;
        }

        .rocket {
            position: absolute;
            width: 4px;
            height: 15px;
            background: linear-gradient(to top, #ff6b35, #f7931e);
            border-radius: 2px;
            animation: rocket-launch 1.5s ease-out forwards;
        }

        .particle {
            position: absolute;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            animation: particle-explode 2s ease-out forwards;
        }

        .particle-yellow { background: radial-gradient(circle, #ffff00, #ffd700); box-shadow: 0 0 10px #ffff00; }
        .particle-red { background: radial-gradient(circle, #ff4444, #cc0000); box-shadow: 0 0 10px #ff4444; }
        .particle-blue { background: radial-gradient(circle, #4488ff, #0066cc); box-shadow: 0 0 10px #4488ff; }
        .particle-green { background: radial-gradient(circle, #44ff44, #00cc00); box-shadow: 0 0 10px #44ff44; }
        .particle-purple { background: radial-gradient(circle, #ff44ff, #cc00cc); box-shadow: 0 0 10px #ff44ff; }
        .particle-orange { background: radial-gradient(circle, #ff8844, #ff6600); box-shadow: 0 0 10px #ff8844; }
        .particle-cyan { background: radial-gradient(circle, #44ffff, #00cccc); box-shadow: 0 0 10px #44ffff; }
        .particle-white { background: radial-gradient(circle, #ffffff, #cccccc); box-shadow: 0 0 10px #ffffff; }
        </style>

        <script>
        function createParticleExplosion(x, y, color) {
            const particleCount = 25 + Math.random() * 15; // 25-40 partículas
            const colors = color ? [color] : ['yellow', 'red', 'blue', 'green', 'purple', 'orange', 'cyan', 'white'];

            for (let i = 0; i < particleCount; i++) {
                const particle = document.createElement('div');
                const particleColor = color || colors[Math.floor(Math.random() * colors.length)];
                particle.className = `particle particle-${particleColor}`;

                // Posição inicial da explosão
                particle.style.left = `${x}px`;
                particle.style.top = `${y}px`;

                // Direção aleatória para cada partícula
                const angle = (Math.PI * 2 * i) / particleCount + Math.random() * 0.5;
                const velocity = 50 + Math.random() * 150; // Velocidade aleatória
                const dx = Math.cos(angle) * velocity;
                const dy = Math.sin(angle) * velocity;

                particle.style.setProperty('--dx', `${dx}px`);
                particle.style.setProperty('--dy', `${dy}px`);

                // Adiciona variação no tempo de vida
                particle.style.animationDuration = `${1.5 + Math.random() * 1}s`;
                particle.style.animationDelay = `${Math.random() * 0.1}s`;

                document.body.appendChild(particle);

                // Remove a partícula após a animação
                setTimeout(() => {
                    if (particle.parentNode) {
                        particle.remove();
                    }
                }, 3000);
            }
        }

        function launchRocket(targetX, targetY, color) {
            const rocket = document.createElement('div');
            rocket.className = 'rocket';

            // Posição inicial (bottom da tela)
            rocket.style.left = `${targetX}px`;
            rocket.style.bottom = '0px';
            rocket.style.setProperty('--target-y', `${targetY - window.innerHeight}px`);

            document.body.appendChild(rocket);

            // Explosão quando o foguete chega ao destino
            setTimeout(() => {
                createParticleExplosion(targetX, targetY, color);
                rocket.remove();
            }, 1500);
        }

        function createRandomExplosion() {
            const x = Math.random() * (window.innerWidth - 200) + 100;
            const y = Math.random() * (window.innerHeight * 0.6) + window.innerHeight * 0.1;
            const colors = ['yellow', 'red', 'blue', 'green', 'purple', 'orange', 'cyan'];
            const color = colors[Math.floor(Math.random() * colors.length)];

            launchRocket(x, y, color);
        }

        function launchFireworksShow() {
            // Primeira salva - 8 foguetes
            for (let i = 0; i < 8; i++) {
                setTimeout(() => {
                    createRandomExplosion();
                }, i * 300);
            }

            // Segunda salva após 3 segundos - 6 foguetes
            setTimeout(() => {
                for (let i = 0; i < 6; i++) {
                    setTimeout(() => {
                        createRandomExplosion();
                    }, i * 250);
                }
            }, 3000);

            // Grande finale após 6 segundos - 4 explosões simultâneas
            setTimeout(() => {
                for (let i = 0; i < 4; i++) {
                    setTimeout(() => {
                        const x = (window.innerWidth / 5) * (i + 1);
                        const y = window.innerHeight * 0.3;
                        createParticleExplosion(x, y);
                    }, i * 100);
                }
            }, 6000);
        }

        // Inicia o show de fogos
        setTimeout(launchFireworksShow, 500);
        </script>
        """,
        unsafe_allow_html=True
    )


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

def bi_excluir_lixo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parte 1: remove linhas do BI quando CFOP está vazio E as 4 colunas de valores estão todas = 0.
    Observação: só aplica a regra se TODAS as 4 colunas existirem no DF e a coluna CFOP existir.
    """
    if df is None or df.empty or ("CFOP" not in df.columns):
        return df

    # use apenas as colunas que existem; se faltar alguma das 4, não arrisca excluir
    val_cols = [c for c in ["valor_contabil", "vl_icms", "vl_st", "vl_ipi"] if c in df.columns]
    if len(val_cols) < 4:
        return df

    df = df.copy()
    for c in val_cols:
        df[c] = df[c].map(to_number_br)

    # CFOP vazio = sem dígitos após limpeza (None/NaN, '-', espaços => vazio)
    cfop_digits = (
        df["CFOP"].map(clean_code).astype(str).fillna("").str.replace(r"\D+", "", regex=True)
    )
    cfop_empty = cfop_digits.str.len().eq(0)

    # todas as 4 colunas zeradas?
    all_zero = df[val_cols].fillna(0.0).astype(float).abs().sum(axis=1).eq(0.0)

    drop_mask = cfop_empty & all_zero
    return df.loc[~drop_mask].reset_index(drop=True)


def bi_es_excluir_lixo(out: pd.DataFrame, cfop_series: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Parte 2 (Entradas/Saídas): remove linhas quando CFOP vazio E (v_cont, v_icms, v_st, v_ipi) = 0.
    """
    if out is None or out.empty or cfop_series is None:
        return out, cfop_series

    # garante que as colunas existem
    req = ["v_cont", "v_icms", "v_st", "v_ipi"]
    if not all(c in out.columns for c in req):
        return out, cfop_series

    sum_vals = out[req].fillna(0.0).astype(float).abs().sum(axis=1)
    cfop_digits = cfop_series.map(clean_code).astype(str).fillna("").str.replace(r"\D+", "", regex=True)
    cfop_empty = cfop_digits.str.len().eq(0)
    all_zero = sum_vals.eq(0.0)

    drop_mask = cfop_empty & all_zero
    return (
        out.loc[~drop_mask].reset_index(drop=True),
        cfop_series.loc[~drop_mask].reset_index(drop=True),
    )

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
        status = "⚠️ CFOP não cadastrado"
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
            status = "❌ Código de lançamento incorreto"
            det = "; ".join(mismatches + zeros)
            details = f"{det}" + (f"  •  Valores (BI): {resumo_valores}" if resumo_valores else "")
        elif zeros:
            status = "🟡 Ausência de lançamento automático"
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

    # Mapeia para nomes internos usados no restante do app
    for src, dst in INTERNAL_KEYS.items():
        if src in df.columns and dst != src:
            df[dst] = df[src]
    for src, dst in INTERNAL_VALUE_KEYS.items():
        if src in df.columns:
            df[dst] = df[src]

    # ==================== LIMPEZA pedida ====================
    # Regra: excluir somente quando CFOP vazio E todos os 4 valores zerados
    # (linhas com CFOP preenchido permanecem, mesmo com valores = 0)
    # 1) Normaliza os valores para número
    val_cols = [c for c in ["valor_contabil", "vl_icms", "vl_st", "vl_ipi"] if c in df.columns]
    for c in val_cols:
        df[c] = df[c].map(to_number_br)

    # 2) CFOP vazio (após normalização para dígitos)
    cfop_series = df["CFOP"] if "CFOP" in df.columns else pd.Series([""] * len(df), index=df.index)
    cfop_digits = cfop_series.map(clean_code)         # "" para None/NaN/"-"/"nan"/etc.
    cfop_empty = cfop_digits.eq("")

    # 3) Todos os valores = 0? (só entre as colunas que EXISTIREM)
    all_zero = (
        df[val_cols].fillna(0.0).astype(float).abs().sum(axis=1).eq(0.0)
        if val_cols else pd.Series(False, index=df.index)  # se não há colunas de valor, não exclui por isso
    )

    # 4) Excluir: CFOP vazio E todos valores zerados
    drop_mask = cfop_empty & all_zero
    if drop_mask.any():
        st.caption(f"🧹 Removidas do BI (CFOP vazio + valores zerados): {int(drop_mask.sum())}")

    df = df.loc[~drop_mask].reset_index(drop=True)

    # 5) Filtrar pela coluna "Cancelada" se ela existir
    if "cancelada" in df.columns:
        cancelada_empty = (
            df["cancelada"].isna() |
            df["cancelada"].astype(str).str.strip().eq("") |
            df["cancelada"].astype(str).str.lower().isin(["nan", "none", "null"])
        )
        if cancelada_empty.any():
            st.caption(f"🧹 Removidas do BI (coluna Cancelada vazia): {int(cancelada_empty.sum())}")
        df = df.loc[~cancelada_empty].reset_index(drop=True)
    # ================== FIM LIMPEZA pedida ==================

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
    """
    Lê BI de Entradas/Saídas, normaliza campos e remove 'lixo' segundo a regra:
    - manter se CFOP tem valor; OU
    - manter se CFOP vazio e pelo menos um entre v_cont/v_icms/v_st/v_ipi for != 0;
    - remover nos demais casos.
    Retorna: (out_df_normalizado, cfop_series_filtrado)
    """
    df = read_excel_best(file)
    cols = detect_bi_columns(df)

    # --- CFOP: sempre com mesmo comprimento do DF (evita desalinhamento do keep_mask)
    if cols.get("cfop"):
        cfop_raw = df[cols["cfop"]]
    else:
        # planilha sem CFOP: cria série vazia alinhada
        cfop_raw = pd.Series([""] * len(df), index=df.index)

    # Apenas dígitos; vazio para None/nan/"None"/etc.
    cfop_series = cfop_raw.map(clean_code)

    # --- Monta dataframe normalizado
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
    for c in ["la_cont", "la_icms", "la_st", "la_ipi"]:
        out[c] = out[c].map(clean_code)

    # === LIMPEZA DE LIXO DO BI (regra: CFOP vazio E todos os valores zerados) ===
    # out: v_cont, v_icms, v_st, v_ipi; cfop_series: CFOP por linha

    # Normaliza CFOP para apenas dígitos (None/NaN/'-' etc. => vazio)
    cfop_digits = (
        cfop_series.astype(str)
        .fillna("")
        .str.replace(r"\D+", "", regex=True)
    )
    cfop_empty = cfop_digits.str.len().eq(0)

    # Todos os valores = 0?
    all_zero = (
        out[["v_cont", "v_icms", "v_st", "v_ipi"]]
        .fillna(0.0).astype(float).abs().sum(axis=1).eq(0.0)
    )

    # Excluir somente quando CFOP vazio E todos valores zerados
    drop_mask = cfop_empty & all_zero
    out = out.loc[~drop_mask].reset_index(drop=True)
    cfop_series = cfop_series.loc[~drop_mask].reset_index(drop=True)

    # Filtrar pela coluna "Cancelada" se ela existir
    if cols.get("cancelada"):
        out["cancelada"] = df[cols["cancelada"]]
        cancelada_empty = (
            out["cancelada"].isna() |
            out["cancelada"].astype(str).str.strip().eq("") |
            out["cancelada"].astype(str).str.lower().isin(["nan", "none", "null"])
        )
        # Remove linhas onde Cancelada está vazia
        keep_mask = ~cancelada_empty
        out = out.loc[keep_mask].reset_index(drop=True)
        cfop_series = cfop_series.loc[keep_mask].reset_index(drop=True)
    # === FIM DA LIMPEZA ===


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
tab1, tab2, tab3 = st.tabs([
    "① Análise do BI (CFOP × Base CFOP)",
    "② Conferência BI × Razão (TXT)",
    "Livro de ICMS x Lote Contábil",
])


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
        bi_all = bi_excluir_lixo(bi_all)  # 👈 aplica a regra CFOP vazio + valores zerados

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

            # Sempre incluir os valores do BI no Resultado da Validação
            for k, label in (
                ("valor_contabil", "Valor Contábil"),
                ("vl_icms",       "Vl. ICMS"),
                ("vl_st",         "Vl. ST"),
                ("vl_ipi",        "Vl. IPI"),
            ):
                row_out[label] = r.get(k) if k in bi_all.columns else None


            results.append(row_out)

        out_df = pd.DataFrame(results)
                # Deixar as colunas de valor visíveis e ordenadas
        col_order = [
            "origem", "CFOP", "Nome (Base)", "Status", "Detalhes",
            "Esperado Contábil", "Encontrado Contábil","Valor Contábil",
            "Esperado ICMS", "Encontrado ICMS","Vl. ICMS", 
            "Esperado ICMS Subst. Trib.", "Encontrado ICMS Subst. Trib.","Vl. ST", 
            "Esperado IPI", "Encontrado IPI","Vl. IPI"
        ]
        out_df = out_df.reindex(columns=[c for c in col_order if c in out_df.columns])


        # persistir para eventual uso futuro
        st.session_state["p1_bi_all"] = bi_all
        st.session_state["p1_result"] = out_df

        st.subheader("Resultado da Validação")

        ok_count        = int((out_df["Status"] == "OK").sum())
        diff_count      = int((out_df["Status"] == "❌ Código de lançamento incorreto").sum())
        zero_count      = int((out_df["Status"] == "🟡 Ausência de lançamento automático").sum())
        notfound_count  = int((out_df["Status"].str.contains("⚠️ CFOP não cadastrado", na=False)).sum())

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("OK ✅", ok_count, bg="#ECFFF1", border="#C8F3D4", fg="#16A34A")
        with c2:
            kpi_card("Código de lançamento incorreto ❌", diff_count, bg="#FFF1F2", border="#FECDD3", fg="#E11D48")
        with c3:
            kpi_card("Ausência de Lançamento Automático 🟡", zero_count, bg="#FFF1F2", border="#FECDD3", fg="#E11D48")
        with c4:
            kpi_card("⚠️ CFOP não cadastrado", notfound_count, bg="#FFF1F2", border="#FECDD3", fg="#E11D48")

        # Verifica se todas as análises estão OK (sem divergências)
        if diff_count == 0 and zero_count == 0 and notfound_count == 0 and ok_count > 0:
            st.success("🎉 **PARABÉNS!** Todas as análises da Parte 1 estão perfeitas - sem divergências!")
            trigger_fireworks()

        # with c1:
        #     kpi_card("OK ✅", ok_count, bg="#ECFFF1", border="#C8F3D4", fg="#16A34A")
        # with c2:
        #     kpi_card("Código de lançamento incorreto ❌", diff_count, bg="#FFF1F2", border="#FECDD3", fg="#E11D48")
        # with c3:
        #     kpi_card("Ausência de L.A. 🟡", zero_count, bg="#FFF9E6", border="#FDE68A", fg="#EAB308")
        # with c4:
        #     kpi_card("CFOP não cadastrado ⚠️", notfound_count, bg="#FFF9E6", border="#FDE68A", fg="#CA8A04")


        # c1, c2, c3, c4 = st.columns(4)
        # c1.metric("OK", ok_count)
        # c2.metric("Diferente", diff_count)
        # c3.metric("Zerado no BI", zero_count)
        # c4.metric("CFOP ausente na base", notfound_count)

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

    # ==================== Processar BIs (SEM interromper o app) ====================
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

    # BI — Soma por Lançamento (só mostra se houver BI)
    if bi_parts:
        bi_total = (
            pd.concat(bi_parts, ignore_index=True)
              .groupby("lancamento", as_index=False)["valor_bi"].sum()
        )
        st.subheader("📊 BI — Soma por Lançamento")
        st.dataframe(bi_total, use_container_width=True, height=280)
    else:
        bi_total = pd.DataFrame(columns=["lancamento","valor_bi"])
        st.info("Envie ao menos um BI (Entradas, Saídas ou Serviços).")

    # (se quiser voltar a exibir lacunas por CFOP, descomente seu bloco antigo aqui)

    st.divider()

    # ==================== Razões (SEM interromper o app) ====================
    if razao_files:
        razoes = []
        for f in razao_files:
            try:
                rz = read_razao_txt(f); rz["arquivo"] = f.name
                razoes.append(rz)
                with st.expander(f"Prévia TXT: {f.name}"):
                    st.dataframe(rz.head(200), use_container_width=True, height=200)
            except Exception as e:
                st.error(f"Erro lendo TXT {f.name}: {e}")

        if razoes:
            razao_total = (
                pd.concat(razoes, ignore_index=True)
                  .groupby("lancamento", as_index=False)["valor_razao"].sum()
                  .merge(
                      pd.concat(razoes, ignore_index=True)[["lancamento", "descricao"]]
                        .dropna().drop_duplicates("lancamento"),
                      on="lancamento", how="left"
                  )
            )
            st.subheader("📒 Razão consolidado (todos TXT)")
            st.dataframe(razao_total, use_container_width=True, height=240)
        else:
            razao_total = pd.DataFrame(columns=["lancamento","valor_razao","descricao"])
            st.warning("Nenhum TXT de Razão pôde ser lido.")
    else:
        razao_total = pd.DataFrame(columns=["lancamento","valor_razao","descricao"])
        st.info("Envie ao menos um arquivo TXT de Razão.")

    st.divider()

    # ==================== Comparação (só se BI e Razão existirem) ====================
    if not bi_total.empty and not razao_total.empty:
        st.subheader("✅ Comparação BI × Razão por Lançamento")
        comp = compare_bi_vs_razao(bi_total, razao_total)

        # --- KPI cards no estilo da tela ---
        if "kpi_card" not in globals():
            def kpi_card(title: str, value, bg="#ffffff", border="#e5e7eb", fg="#111827"):
                st.markdown(
                    f"""
                    <div style="
                         border-radius:18px;
                         padding:22px 26px;
                         background:{bg};
                         border:2px solid {border};
                         box-shadow:0 6px 18px rgba(0,0,0,.06);
                    ">
                      <div style="font-weight:800;font-size:24px;line-height:1.2;margin-bottom:6px;">
                        {title}
                      </div>
                      <div style="font-size:46px;font-weight:900;color:{fg};">
                        {value}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        bi_count    = int(len(bi_total))
        razao_count = int(len(razao_total))
        ok_count    = int(comp.get("ok", pd.Series([], dtype=bool)).sum())
        div_count   = int((~comp.get("ok", pd.Series([], dtype=bool))).sum())

        kc1, kc2, kc3, kc4 = st.columns(4)
        with kc1: kpi_card("Lançamentos BI", bi_count, bg="#FFFFFF", border="#E5E7EB", fg="#111827")
        with kc2: kpi_card("Lançamentos Razão", razao_count, bg="#F0F7FF", border="#93C5FD", fg="#1D4ED8")
        with kc3: kpi_card("Divergências", div_count, bg="#FEE2E2", border="#FCA5A5", fg="#DC2626")
        with kc4: kpi_card("OK ✅", ok_count, bg="#DCFCE7", border="#86EFAC", fg="#16A34A")

        # Verifica se todas as comparações BI x Razão estão OK (sem divergências)
        if div_count == 0 and ok_count > 0:
            st.success("🎉 **PARABÉNS!** Todas as comparações BI × Razão estão perfeitas - sem divergências!")
            trigger_fireworks()

        styled = (
            comp.style
                .format({"valor_bi": "{:,.2f}", "valor_razao": "{:,.2f}", "dif": "{:,.2f}"})
                .apply(lambda s: pd.Series(np.where(comp["ok"], "color:green", "color:red"), index=comp.index), subset=["dif"])
        )
        st.dataframe(styled, use_container_width=True, height=420)

        # Downloads (CSV/Excel) — só quando há comparação
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
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name=sheet)
            return (buf.getvalue(), f"{sheet.lower().replace(' ','_')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        ex1, nm1, mm1 = make_excel_bytes(bi_total, "BI_Por_Lancamento")
        ex2, nm2, mm2 = make_excel_bytes(razao_total, "Razao_Consolidado")
        ex3, nm3, mm3 = make_excel_bytes(comp, "Comparacao_BI_Razao")

        cex1, cex2, cex3 = st.columns(3)
        with cex1: st.download_button("Baixar BI (Excel)", data=ex1, file_name=nm1, mime=mm1)
        with cex2: st.download_button("Baixar Razão (Excel)", data=ex2, file_name=nm2, mime=mm2)
        with cex3: st.download_button("Baixar Comparação (Excel)", data=ex3, file_name=nm3, mime=mm3)

    else:
        st.info("Para comparar, envie ao menos um BI e ao menos um TXT de Razão.")

# === Aba 3: Livro de ICMS x Lote Contábil ===
with tab3:
    import io, os, re, csv
    import numpy as np

    st.header("Livro de ICMS x Lote Contábil — Livro de Apuração (PDF)")

    cpdf, ctxt = st.columns(2)
    with cpdf:
        pdf_file    = st.file_uploader("📄 PDF: Livro de Apuração (ICMS)", type=["pdf"], key="sn_pdf")
        pdf_file_st = st.file_uploader("📄 PDF: Livro de ICMS ST",         type=["pdf"], key="sn_pdf_st")
    with ctxt:
        txt_file = st.file_uploader("📚 TXT p/ confronto (coluna 2 = lançamento, coluna 4 = valor, col. 8 = descrição)", type=["txt"], key="sn_txt")

    # ===== 0) Verifica base CFOP (mapeia CFOP → lançamentos) =====
    if not base_map:
        st.error("Base de CFOP não carregada na sidebar. O mapeamento CFOP→lançamentos depende desse JSON.")

    # ===== 1) PDF (ICMS) -> ENTRADAS + SAÍDAS (sempre) =====
    cols_ent = ["CFOP", "Valor Contábil", "Imposto Creditado",
                "Valor Contábil (num)", "Imposto Creditado (num)"]
    cols_sai = ["CFOP", "Valor Contábil", "Imposto Debitado",
                "Valor Contábil (num)", "Imposto Debitado (num)"]

    if pdf_file is not None:
        try:
            # Wrappers do sn_pdf.py (já agregam por CFOP dentro do bloco)
            df_ent = parse_livro_icms_pdf_entradas(pdf_file, keep_numeric=True)
            df_sai = parse_livro_icms_pdf_saidas(pdf_file,   keep_numeric=True)
        except Exception as e:
            st.error(f"Falha ao ler o PDF (ICMS): {e}")
            df_ent = pd.DataFrame(columns=cols_ent)
            df_sai = pd.DataFrame(columns=cols_sai)
    else:
        df_ent = pd.DataFrame(columns=cols_ent)
        df_sai = pd.DataFrame(columns=cols_sai)

    # Combina E+S numéricos por CFOP
    e_num = (df_ent[["CFOP","Valor Contábil (num)","Imposto Creditado (num)"]]
             .rename(columns={"Valor Contábil (num)":"vc_num",
                              "Imposto Creditado (num)":"icms_num"})
             if not df_ent.empty else pd.DataFrame(columns=["CFOP","vc_num","icms_num"]))

    s_num = (df_sai[["CFOP","Valor Contábil (num)","Imposto Debitado (num)"]]
             .rename(columns={"Valor Contábil (num)":"vc_num",
                              "Imposto Debitado (num)":"icms_num"})
             if not df_sai.empty else pd.DataFrame(columns=["CFOP","vc_num","icms_num"]))

    # --- agregado de Imposto Debitado (somente SAÍDAS) para o LOG
    s_deb_agg = (df_sai[["CFOP","Imposto Debitado (num)"]]
                 .rename(columns={"Imposto Debitado (num)":"imposto_debitado_num"})
                 .groupby("CFOP", as_index=False)["imposto_debitado_num"].sum()
                 if not df_sai.empty else pd.DataFrame(columns=["CFOP","imposto_debitado_num"]))

    both = pd.concat([e_num, s_num], ignore_index=True)

    def _fmt_br(x: float) -> str:
        try:
            return f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "0,00"

    if both.empty:
        df_pdf_num  = pd.DataFrame(columns=["CFOP","vc_num","icms_num"])
        df_pdf_extr = pd.DataFrame(columns=["CFOP","Valor Contábil","Imposto Creditado"])

        # Log vazio
        with st.expander("🔎 Log — CFOP × Contábil (E+S) × Imposto Debitado (Saídas)", expanded=False):
            st.caption("Nenhum dado para exibir.")
    else:
        # soma E+S por CFOP
        both = both.groupby("CFOP", as_index=False)[["vc_num","icms_num"]].sum()

        # --- LOG: Contábil (E+S) vs Imposto Debitado (S)
        log_df = (both.merge(s_deb_agg, on="CFOP", how="left")
                        .fillna({"imposto_debitado_num": 0.0}))
        log_df["Valor Contábil"]   = log_df["vc_num"].map(_fmt_br)
        log_df["Imposto Debitado"] = log_df["imposto_debitado_num"].map(_fmt_br)

        with st.expander("🔎 Log — CFOP × Contábil (E+S) × Imposto Debitado (Saídas)", expanded=False):
            st.dataframe(
                log_df[["CFOP","Valor Contábil","Imposto Debitado"]],
                use_container_width=True, height=280
            )

        # Saída normal do pipeline (mantém nomes esperados)
        df_pdf_extr = both.assign(
            **{
                "Valor Contábil":    both["vc_num"].map(_fmt_br),
                "Imposto Creditado": both["icms_num"].map(_fmt_br),  # total E+S
            }
        )[["CFOP","Valor Contábil","Imposto Creditado"]].copy()

        df_pdf_num = both[["CFOP","vc_num","icms_num"]].copy()

    # ===== 2) Mapeia CFOP (ICMS) → lançamentos via cfop_base.json =====
    pdf_lanc_tot = pd.DataFrame(columns=["lancamento","valor"])
    comp_map = {}     # lanc -> set(cfops)
    cfop_sem_mapa = []

    if not df_pdf_num.empty and base_map:
        rows = []
        for _, r in df_pdf_num.iterrows():
            cfop = clean_code(r["CFOP"])
            mapa = base_map.get(cfop) or {}
            lc = clean_code(mapa.get("contabil") or "")
            li = clean_code(mapa.get("icms") or "")
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

    if cfop_sem_mapa:
        st.warning(f"CFOP (ICMS) sem mapeamento na base: {', '.join(sorted(set(cfop_sem_mapa)))}")

    comp_cfop_map = (pd.DataFrame([{"lancamento": k, "cfops": ", ".join(sorted(v))} for k, v in comp_map.items()])
                     if comp_map else pd.DataFrame(columns=["lancamento","cfops"]))

    # ===== 3) TXT → valores (col.2 e col.4) + descrição (col.8 até 1º número) =====
    def _parse_txt_lanc_val_desc(txt_file):
        """
        Retorna:
          - df_val : lancamento | valor
          - df_desc: lancamento | descricao
        Lê CSV/TXT com delimitador ',', ';', '\t' ou '|', respeitando aspas.
        """
        import pandas as pd

        def _read_bytes(f):
            if f is None: return b""
            if hasattr(f, "read"):
                b = f.read()
                try: f.seek(0)
                except Exception: pass
                return b
            if isinstance(f, (bytes, bytearray)): return bytes(f)
            if isinstance(f, str) and os.path.exists(f):
                with open(f, "rb") as fh: return fh.read()
            return b""

        raw = _read_bytes(txt_file)
        if not raw:
            return (pd.DataFrame(columns=["lancamento","valor"]),
                    pd.DataFrame(columns=["lancamento","descricao"]))

        text = None
        for enc in ("utf-8-sig","utf-8","latin-1","cp1252"):
            try:
                text = raw.decode(enc); break
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
            if s is None: return 0.0
            s = str(s).strip().strip('"').strip()
            neg = s.startswith("(") and s.endswith(")")
            if neg: s = s[1:-1]
            s = s.replace(".", "").replace("\u00A0", "").replace(" ", "").replace(",", ".")
            m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
            v = float(m.group(0)) if m else 0.0
            return -v if neg and v > 0 else v

        def only_text_until_first_digit(s: str) -> str:
            if s is None: return ""
            s = str(s).strip()
            parts = re.split(r"\d", s, maxsplit=1)
            head = parts[0] if parts else s
            head = head.replace(";", " ").strip(" -–—:•\t").strip()
            return " ".join(head.split())

        vals, descs = [], []
        for row in reader:
            if not row or len(row) < 8:
                continue
            lanc = clean_code(row[1])     # coluna 2
            if lanc == "": 
                continue
            val  = br_to_float(row[3])    # coluna 4
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

    txt_lanc_tot, txt_desc = _parse_txt_lanc_val_desc(txt_file)

    # ===== 4) PDF (ICMS ST) → por lançamento (usa base 'icms_subst') =====
    st_lanc_tot = pd.DataFrame(columns=["lancamento","valor"])
    comp_map_st = {}
    cfop_st_sem_mapa = []

    if pdf_file_st is not None and base_map:
        try:
            df_st = parse_livro_icms_st_pdf(pdf_file_st, keep_numeric=True)  # CFOP | total_st_num (via parser)
            # total_st_num = creditado (Entradas) + debitado (Saídas)
            df_st["total_st_num"] = df_st.get("total_st_num", 0.0)
            rows_st = []
            for _, r in df_st.iterrows():
                cf = clean_code(r["CFOP"])
                mapa = base_map.get(cf) or {}
                lanc_st = clean_code(mapa.get("icms_subst") or "")
                if lanc_st:
                    val = float(r["total_st_num"])
                    if val != 0.0:
                        rows_st.append({"lancamento": lanc_st, "valor": val})
                        comp_map_st.setdefault(lanc_st, set()).add(cf)
                else:
                    cfop_st_sem_mapa.append(cf)
            if rows_st:
                st_lanc_tot = pd.DataFrame(rows_st).groupby("lancamento", as_index=False)["valor"].sum()
        except Exception as e:
            st.error(f"Falha ao ler o PDF de ICMS ST: {e}")

    if cfop_st_sem_mapa:
        st.warning(f"CFOP (ICMS ST) sem mapeamento na base (icms_subst): {', '.join(sorted(set(cfop_st_sem_mapa)))}")

    # ===== 5) COMPOSIÇÃO (CFOP) por lançamento (ICMS normal + ST) =====
    comp_map_union = {}
    for dic in (comp_map, comp_map_st):
        for k, v in (dic or {}).items():
            comp_map_union.setdefault(k, set()).update(v if isinstance(v, set) else set(v))
    comp_cfop_union = (
        pd.DataFrame([{"lancamento": k, "cfops": ", ".join(sorted(v))} for k, v in comp_map_union.items()])
        if comp_map_union else pd.DataFrame(columns=["lancamento","cfops"])
    )

    # ===== 6) Comparação final: Livro ICMS + Livro ICMS ST × Lote Contábil =====
    pdf_icms    = (pdf_lanc_tot.rename(columns={"valor": "Livro ICMS"})
                   if not pdf_lanc_tot.empty else pd.DataFrame(columns=["lancamento","Livro ICMS"]))
    pdf_icms_st = (st_lanc_tot.rename(columns={"valor": "Livro ICMS ST"})
                   if not st_lanc_tot.empty else pd.DataFrame(columns=["lancamento","Livro ICMS ST"]))

    comp = pd.merge(pdf_icms,    pdf_icms_st,                                    on="lancamento", how="outer")
    comp = pd.merge(comp,        txt_lanc_tot.rename(columns={"valor":"Lote Contábil"}), on="lancamento", how="outer")
    comp = pd.merge(comp,        comp_cfop_union,                                 on="lancamento", how="left")
    comp = pd.merge(comp,        txt_desc,                                        on="lancamento", how="left")

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
                         "cfops": "CFOP",
                         "descricao": "Descrição"}, inplace=True)

    cols_final = ["CFOP", "Lançamento", "Descrição",
                  "Livro ICMS", "Livro ICMS ST", "Lote Contábil", "Diferença", "Status"]
    comp = comp.reindex(columns=[c for c in cols_final if c in comp.columns]).sort_values("Lançamento")

    st.divider()
    st.subheader("🔎 Comparação — Livro ICMS & ICMS ST (PDF) × Lote Contábil (TXT)")

    # KPIs
    if "kpi_card" not in globals():
        def kpi_card(title: str, value, bg="#ffffff", border="#e5e7eb", fg="#111827"):
            st.markdown(
                f"""
                <div style="
                     border-radius:18px;
                     padding:22px 26px;
                     background:{bg};
                     border:2px solid {border};
                     box-shadow:0 6px 18px rgba(0,0,0,.06);
                ">
                  <div style="font-weight:800;font-size:20px;line-height:1.2;margin-bottom:6px;">
                    {title}
                  </div>
                  <div style="font-size:38px;font-weight:900;color:{fg};">
                    {value}
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    pdf_lanc_count = int(len(set(pdf_icms.get("lancamento", pd.Series([]))) | set(pdf_icms_st.get("lancamento", pd.Series([])))))
    ok_count  = int((comp["Status"]=="OK ✅").sum())
    div_count = int(len(comp) - ok_count)
    rz_count  = int(txt_lanc_tot.shape[0])

    kc1, kc2, kc3, kc4 = st.columns(4)
    with kc1: kpi_card("Lançamentos (PDF)", pdf_lanc_count, bg="#FFFFFF", border="#E5E7EB", fg="#111827")
    with kc2: kpi_card("Lançamentos (TXT)", rz_count, bg="#F0F7FF", border="#93C5FD", fg="#1D4ED8")
    with kc3: kpi_card("Divergências",      div_count, bg="#FEE2E2", border="#FCA5A5", fg="#DC2626")
    with kc4: kpi_card("OK ✅",              ok_count,  bg="#DCFCE7", border="#86EFAC", fg="#16A34A")

    # Verifica se todas as análises do Livro de ICMS x Lote Contábil estão OK (sem divergências)
    if div_count == 0 and ok_count > 0:
        st.success("🎉 **PARABÉNS!** Todas as análises do Livro de ICMS x Lote Contábil estão perfeitas - sem divergências!")
        trigger_fireworks()

    # Tabela final — ÚNICA
    def _fmt_br_tbl(x):
        try:
            return f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return x

    ok_mask = comp["Status"].astype(str).str.startswith("OK")
    styled = (
        comp.style
           .format({"Livro ICMS": _fmt_br_tbl, "Livro ICMS ST": _fmt_br_tbl,
                    "Lote Contábil": _fmt_br_tbl, "Diferença": _fmt_br_tbl})
           .apply(lambda s: pd.Series(np.where(ok_mask, "color:green", "color:red"),
                                      index=comp.index), subset=["Diferença"])
    )
    st.dataframe(styled, use_container_width=True, height=460, key="sn_comp_icms_icmsst")

    # Downloads
    cdl1, cdl2, cdl3 = st.columns(3)
    with cdl1:
        csv_icms = pdf_icms.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Baixar Livro ICMS por Lançamento (CSV)", data=csv_icms,
                           file_name="sn_pdf_icms_por_lancamento.csv", mime="text/csv")
    with cdl2:
        csv_icms_st = pdf_icms_st.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Baixar Livro ICMS ST por Lançamento (CSV)", data=csv_icms_st,
                           file_name="sn_pdf_icms_st_por_lancamento.csv", mime="text/csv")
    with cdl3:
        csv_comp = comp.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Baixar Comparação (CSV)", data=csv_comp,
                           file_name="sn_comparacao_icms_icmsst_txt.csv", mime="text/csv")


# =============================================================================
# Fim
# =============================================================================
