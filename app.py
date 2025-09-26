"""
Sistema de Conferência Fiscal - Aplicação Principal
Refatorado em módulos para melhor manutenção.
"""

from __future__ import annotations
import pandas as pd
import streamlit as st
from pathlib import Path

# Importações dos módulos locais
from utils import clean_code_main, to_number_br_main
from cfop_analyzer import (
    load_base_json, analyze_bi_against_base,
    calculate_analysis_metrics, is_analysis_perfect
)
from bi_processor import (
    load_bi_strict, bi_excluir_lixo, load_bi_es,
    aggregate_bi_all, load_bi_servico
)
from razao_processor import (
    consolidate_razao_files, compare_bi_vs_razao,
    calculate_comparison_metrics, is_comparison_perfect
)
from simples_nacional import (
    process_icms_pdf, process_icms_st_pdf, parse_txt_lancamento_valor_desc,
    compare_simples_nacional, calculate_simples_nacional_metrics,
    is_simples_nacional_perfect
)
from ui_components import (
    display_analysis_kpis, display_comparison_kpis, display_simples_nacional_kpis,
    show_success_message, create_status_filters, apply_filters,
    create_download_buttons, format_comparison_table
)


# =============================================================================
# Configuração da Página
# =============================================================================
st.set_page_config(page_title="Pipeline Fiscal • BI → CFOP/ Razão", layout="wide")
st.title("📊 Pipeline Fiscal")
st.caption("① Análise do BI (CFOP × Base CFOP)  →  ② Conferência BI (Entradas/Saídas/Serviços) × Razão (TXT)")


# =============================================================================
# Sidebar — Base CFOP
# =============================================================================
st.sidebar.header("Base de CFOP (JSON do disco)")
DEFAULT_BASE_PATH = Path("cfop_base.json")

@st.cache_data(show_spinner=False)
def load_base_json_cached(p: Path):
    return load_base_json(p)

base_path = Path(st.sidebar.text_input("Caminho do arquivo JSON", value=str(DEFAULT_BASE_PATH))).expanduser()
base_map = {}

try:
    if base_path.exists():
        base_map = load_base_json_cached(base_path)
        st.sidebar.success(f"Base carregada: {base_path.name} • {len(base_map)} CFOPs")
    else:
        st.sidebar.error("Arquivo cfop_base.json não encontrado. Informe um caminho válido na sidebar.")
except Exception as e:
    st.sidebar.error(f"Erro ao carregar base: {e}")


# =============================================================================
# Abas Principais
# =============================================================================
tab1, tab2, tab3 = st.tabs([
    "① Análise do BI (CFOP × Base CFOP)",
    "② Conferência BI × Razão (TXT)",
    "Simples Nacional",
])


# =============================================================================
# TAB 1: Análise do BI (CFOP × Base CFOP)
# =============================================================================
with tab1:
    st.header("Parte 1 — Análise do BI (CFOP × Base CFOP)")
    st.write("Cabeçalhos obrigatórios **estritos**:")
    st.code(" | ".join([
        "CFOP", "Lanc. Cont. Vl. Contábil", "Lanc. Cont. Vl. ICMS",
        "Lanc. Cont. Vl. Subst. Trib.", "Lanc. Cont. Vl. IPI"
    ]), language="text")
    st.write("Colunas opcionais de **valores** (se presentes, serão exibidas quando houver diferença/zerado):")
    st.code(" | ".join(["Valor Contábil", "Vl. ICMS", "Vl. ST", "Vl. IPI"]), language="text")

    bi_entrada = st.file_uploader("BI Entrada (obrigatório)", type=["csv", "xlsx", "xls"], key="p1_entrada")
    bi_saida = st.file_uploader("BI Saída (opcional)", type=["csv", "xlsx", "xls"], key="p1_saida")

    dfs = []
    if bi_entrada is not None:
        try:
            df_ent = load_bi_strict(bi_entrada, "BI Entrada")
            if df_ent is not None:
                df_ent["origem"] = "Entrada"
                dfs.append(df_ent)
        except Exception as e:
            st.error(f"Erro no BI Entrada: {e}")

    if bi_saida is not None:
        try:
            df_sai = load_bi_strict(bi_saida, "BI Saída")
            if df_sai is not None:
                df_sai["origem"] = "Saída"
                dfs.append(df_sai)
        except Exception as e:
            st.error(f"Erro no BI Saída: {e}")

    if not base_map:
        st.error("Base de CFOP não carregada. Informe um caminho válido na sidebar.")
    elif len(dfs) == 0:
        st.info("Envie ao menos um arquivo de BI para conferir.")
    else:
        bi_all = pd.concat(dfs, ignore_index=True)
        bi_all = bi_excluir_lixo(bi_all)

        result_df = analyze_bi_against_base(bi_all, base_map)

        # Persistir para eventual uso futuro
        st.session_state["p1_bi_all"] = bi_all
        st.session_state["p1_result"] = result_df

        st.subheader("Resultado da Validação")

        metrics = calculate_analysis_metrics(result_df)
        display_analysis_kpis(
            metrics["ok_count"], metrics["diff_count"],
            metrics["zero_count"], metrics["notfound_count"]
        )

        # Verifica se todas as análises estão OK
        if is_analysis_perfect(metrics):
            show_success_message("Todas as análises da Parte 1 estão perfeitas - sem divergências!")

        status_filter, origem_filter = create_status_filters(result_df)
        filtered = apply_filters(result_df, status_filter, origem_filter)

        st.dataframe(filtered, use_container_width=True)
        create_download_buttons(filtered, "Resultado Validação CFOP")


# =============================================================================
# TAB 2: Conferência BI × Razão (TXT)
# =============================================================================
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
    bi_parts = []

    if bi_ent is not None:
        try:
            bi_df_ent, cfop_ent = load_bi_es(bi_ent)
            agg_ent = aggregate_bi_all(bi_df_ent)
            agg_ent["origem"] = "entradas"
            bi_parts.append(agg_ent)
            st.success("BI Entradas carregado.")
        except Exception as e:
            st.error(f"Erro no BI Entradas: {e}")

    if bi_sai is not None:
        try:
            bi_df_sai, cfop_sai = load_bi_es(bi_sai)
            agg_sai = aggregate_bi_all(bi_df_sai)
            agg_sai["origem"] = "saidas"
            bi_parts.append(agg_sai)
            st.success("BI Saídas carregado.")
        except Exception as e:
            st.error(f"Erro no BI Saídas: {e}")

    if bi_srv is not None:
        try:
            agg_srv, cfop_srv, faltas_srv = load_bi_servico(bi_srv)
            agg_srv["origem"] = "servicos"
            bi_parts.append(agg_srv)
            st.success("BI Serviços carregado.")
        except Exception as e:
            st.error(f"Erro no BI Serviços: {e}")

    # BI — Soma por Lançamento
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

    st.divider()

    # Processar Razões
    try:
        razao_total = consolidate_razao_files(razao_files)
        if not razao_total.empty:
            st.subheader("📒 Razão consolidado (todos TXT)")
            st.dataframe(razao_total, use_container_width=True, height=240)
        else:
            st.info("Envie ao menos um arquivo TXT de Razão.")
    except Exception as e:
        st.error(f"Erro processando razões: {e}")
        razao_total = pd.DataFrame(columns=["lancamento","valor_razao","descricao"])

    st.divider()

    # Comparação
    if not bi_total.empty and not razao_total.empty:
        st.subheader("✅ Comparação BI × Razão por Lançamento")
        comp = compare_bi_vs_razao(bi_total, razao_total)

        metrics = calculate_comparison_metrics(comp, bi_total, razao_total)
        display_comparison_kpis(
            metrics["bi_count"], metrics["razao_count"],
            metrics["div_count"], metrics["ok_count"]
        )

        # Verifica se todas as comparações estão OK
        if is_comparison_perfect(metrics):
            show_success_message("Todas as comparações BI × Razão estão perfeitas - sem divergências!")

        styled = format_comparison_table(comp)
        st.dataframe(styled, use_container_width=True, height=420)

        # Downloads
        cdl1, cdl2, cdl3 = st.columns(3)
        with cdl1:
            create_download_buttons(bi_total, "BI por Lançamento")
        with cdl2:
            create_download_buttons(razao_total, "Razão Consolidado")
        with cdl3:
            create_download_buttons(comp, "Comparação BI Razão")
    else:
        st.info("Para comparar, envie ao menos um BI e ao menos um TXT de Razão.")


# =============================================================================
# TAB 3: Simples Nacional
# =============================================================================
with tab3:
    st.header("Simples Nacional — Livro de Apuração (PDF)")

    cpdf, ctxt = st.columns(2)
    with cpdf:
        pdf_file = st.file_uploader("📄 PDF: Livro de Apuração (ICMS)", type=["pdf"], key="sn_pdf")
        pdf_file_st = st.file_uploader("📄 PDF: Livro de ICMS ST", type=["pdf"], key="sn_pdf_st")
    with ctxt:
        txt_file = st.file_uploader("📚 TXT p/ confronto (coluna 2 = lançamento, coluna 4 = valor, col. 8 = descrição)", type=["txt"], key="sn_txt")

    # Verifica base CFOP
    if not base_map:
        st.error("Base de CFOP não carregada na sidebar. O mapeamento CFOP→lançamentos depende desse JSON.")

    # Processar PDF ICMS
    try:
        pdf_lanc_tot, log_df, cfop_sem_mapa = process_icms_pdf(pdf_file, base_map)
        if cfop_sem_mapa:
            st.warning(f"CFOP (ICMS) sem mapeamento na base: {', '.join(sorted(set(cfop_sem_mapa)))}")

        with st.expander("🔎 Log — CFOP × Contábil (E+S) × Imposto Debitado (Saídas)", expanded=False):
            if not log_df.empty:
                st.dataframe(log_df[["CFOP","Valor Contábil","Imposto Debitado"]], use_container_width=True, height=280)
            else:
                st.caption("Nenhum dado para exibir.")
    except Exception as e:
        st.error(f"Erro processando PDF ICMS: {e}")
        pdf_lanc_tot = pd.DataFrame(columns=["lancamento","valor"])

    # Processar PDF ICMS ST
    try:
        st_lanc_tot, cfop_st_sem_mapa = process_icms_st_pdf(pdf_file_st, base_map)
        if cfop_st_sem_mapa:
            st.warning(f"CFOP (ICMS ST) sem mapeamento na base (icms_subst): {', '.join(sorted(set(cfop_st_sem_mapa)))}")
    except Exception as e:
        st.error(f"Erro processando PDF ICMS ST: {e}")
        st_lanc_tot = pd.DataFrame(columns=["lancamento","valor"])

    # Processar TXT
    try:
        txt_lanc_tot, txt_desc = parse_txt_lancamento_valor_desc(txt_file)
    except Exception as e:
        st.error(f"Erro processando TXT: {e}")
        txt_lanc_tot = pd.DataFrame(columns=["lancamento","valor"])
        txt_desc = pd.DataFrame(columns=["lancamento","descricao"])

    # Composição por lançamento
    comp_map_union = {}
    # Simular composição CFOP (seria necessário refatorar mais código para manter essa funcionalidade)

    st.divider()
    st.subheader("🔎 Comparação — Livro ICMS & ICMS ST (PDF) × Lote Contábil (TXT)")

    # Comparação final
    comp = compare_simples_nacional(pdf_lanc_tot, st_lanc_tot, txt_lanc_tot, txt_desc, comp_map_union)

    metrics = calculate_simples_nacional_metrics(comp, pdf_lanc_tot, st_lanc_tot, txt_lanc_tot)
    display_simples_nacional_kpis(
        metrics["pdf_lanc_count"], metrics["rz_count"],
        metrics["div_count"], metrics["ok_count"]
    )

    # Verifica se todas as análises estão OK
    if is_simples_nacional_perfect(metrics):
        show_success_message("Todas as análises do Simples Nacional estão perfeitas - sem divergências!")

    # Tabela final
    styled = format_comparison_table(comp)
    st.dataframe(styled, use_container_width=True, height=460, key="sn_comp_icms_icmsst")

    # Downloads
    cdl1, cdl2, cdl3 = st.columns(3)
    with cdl1:
        create_download_buttons(pdf_lanc_tot, "Livro ICMS por Lançamento")
    with cdl2:
        create_download_buttons(st_lanc_tot, "Livro ICMS ST por Lançamento")
    with cdl3:
        create_download_buttons(comp, "Comparação ICMS ST TXT")


# =============================================================================
# Fim da Aplicação
# =============================================================================