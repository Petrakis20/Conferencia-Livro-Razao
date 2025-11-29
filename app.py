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
    aggregate_bi_all, load_bi_servico, filter_cancelada, load_bi_multisheet,
    load_bi_strict_multisheet
)
from razao_processor import (
    consolidate_razao_files, compare_bi_vs_razao,
    calculate_comparison_metrics, is_comparison_perfect,
    filter_servicos_prestados
)
from simples_nacional import (
    process_icms_pdf, process_icms_st_pdf, parse_txt_lancamento_valor_desc,
    compare_simples_nacional, calculate_simples_nacional_metrics,
    is_simples_nacional_perfect, filter_servicos_prestados_txt
)
from ui_components import (
    display_analysis_kpis, display_comparison_kpis, display_simples_nacional_kpis,
    show_success_message, create_status_filters, apply_filters,
    create_download_buttons, format_comparison_table, create_comparison_download_buttons
)
from alterdata_connector import (
    test_connection_from_env, extract_bi_data_from_env, generate_excel_file,
    get_db_credentials
)
from company_validator import (
    parse_params_file, validate_company_for_period, format_company_info,
    get_all_configured_companies
)
from datetime import datetime, timedelta


# =============================================================================
# Configuração da Página
# =============================================================================
st.set_page_config(page_title="Pipeline Fiscal • BI → CFOP/ Razão", layout="wide")

# CSS para aumentar fonte das tabs
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.3rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Conferência Input Fiscal")

# Botão de download do manual
manual_path = Path("Manual Plataforma Input Fiscal.pdf")
if manual_path.exists():
    with open(manual_path, "rb") as pdf_file:
        pdf_bytes = pdf_file.read()
        st.download_button(
            label="📥 Baixar Manual da Plataforma",
            data=pdf_bytes,
            file_name="Manual_Plataforma_Conferencia_Input_Fiscal.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=False
        )

# st.caption("① Análise do BI (CFOP × Base CFOP)  →  ② Conferência BI (Entradas/Saídas/Serviços) × Razão (TXT)")


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

tab0, tab1, tab2, tab3 = st.tabs([
    "🔄 Extração Alterdata BI",
    "① Análise do BI",
    "② Conferência BI × Razão",
    "Livro de ICMS x Lote Contábil",
])


# =============================================================================
# TAB 0: Extração Alterdata BI
# =============================================================================
with tab0:
    st.header("🔄 Extração de Dados do Alterdata")
    st.caption("Conecte-se ao banco de dados Alterdata e extraia relatórios de BI automaticamente")

    # Carrega configurações do params.txt
    params = parse_params_file()

    # Exibe informações sobre empresas configuradas
    with st.expander("📋 Empresas Configuradas (params.txt)", expanded=False):
        st.markdown(format_company_info(params))

    st.divider()


    # Seleção de período e empresa
    st.subheader("📅 Período e Empresa")

    col1, col2, col3 = st.columns(3)

    with col1:
        start_date = st.date_input(
            "Data Inicial",
            value=datetime(2025, 9, 1),
            help="Data de início do período de extração"
        )

    with col2:
        end_date = st.date_input(
            "Data Final (exclusiva)",
            value=datetime(2025, 10, 1),
            help="Data final do período (não inclusa)"
        )

    with col3:
        company_code = st.text_input(
            "Código da Empresa",
            value="",
            help="Digite o código da empresa (será padronizado para 5 dígitos)",
            max_chars=5
        )

    # Validação da empresa
    validation_result = None
    if company_code:
        is_valid, msg, day_block = validate_company_for_period(
            company_code,
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time()),
            params
        )

        if is_valid:
            st.success(f"✅ {msg}")
            validation_result = True
        else:
            st.error(f"❌ {msg}")
            validation_result = False

    # Município (opcional)
    with st.expander("⚙️ Configurações Avançadas", expanded=False):
        municipio_id = st.number_input(
            "ID Município (opcional)",
            value=None,
            min_value=0,
            help="Deixe vazio para NULL"
        )

    st.divider()

    # Obtém credenciais do .env para validação
    host, database, user, password = get_db_credentials()

    # Botão de extração
    can_extract = (
        company_code and
        all([host, database, user]) and  # Credenciais do .env carregadas
        validation_result is not False  # Pode ser True ou None (não validado ainda)
    )

    if st.button("🚀 Extrair Dados e Gerar BI", type="primary", disabled=not can_extract):
        if not can_extract:
            st.warning("Preencha o código da empresa e verifique se as credenciais estão configuradas no .env")
        else:
            with st.spinner(f"Extraindo dados da empresa {company_code.zfill(5)}..."):
                # Converte datas para datetime
                start_dt = datetime.combine(start_date, datetime.min.time())
                end_dt = datetime.combine(end_date, datetime.min.time())

                # Extrai dados usando credenciais do .env
                df_entrada, df_saida, msg_extract = extract_bi_data_from_env(
                    company_code=company_code,
                    start_date=start_dt,
                    end_date=end_dt,
                    municipio_id=municipio_id if municipio_id else None
                )

                if df_entrada is None or df_saida is None:
                    st.error(msg_extract)
                else:
                    st.success(msg_extract)

                    # Gera arquivo Excel
                    with st.spinner("Gerando arquivo Excel..."):
                        filepath, msg_excel = generate_excel_file(
                            df_entrada=df_entrada,
                            df_saida=df_saida,
                            company_code=company_code,
                            start_date=start_dt,
                            end_date=end_dt
                        )

                        if filepath:
                            st.success(msg_excel)

                            # Salva caminho do arquivo na sessão para uso nas outras abas
                            st.session_state["alterdata_bi_file"] = filepath
                            st.session_state["alterdata_bi_company"] = company_code.zfill(5)

                            # Oferece download
                            with open(filepath, 'rb') as f:
                                st.download_button(
                                    label="📥 Baixar Arquivo Excel Gerado",
                                    data=f.read(),
                                    file_name=Path(filepath).name,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    type="primary"
                                )

                            st.info("✅ Arquivo gerado e salvo! Agora você pode usar nas abas '① Análise do BI' e '② Conferência BI × Razão'.")

                        else:
                            st.error(msg_excel)


# =============================================================================
# TAB 1: Análise do BI (CFOP × Base CFOP)
# =============================================================================
with tab1:
    st.header("Parte 1 — Análise do BI (CFOP × Base CFOP)")
    # st.write("📋 Envie um único arquivo Excel com as abas: **Resumo**, **Saída** e **Entrada**")
    # st.caption("Os dados úteis serão extraídos das abas 'Saída' e 'Entrada'. A aba 'Resumo' não será utilizada.")

    # st.write("Cabeçalhos obrigatórios **estritos**:")
    # st.code(" | ".join([
    #     "CFOP", "Lanc. Cont. Vl. Contábil", "Lanc. Cont. Vl. ICMS",
    #     "Lanc. Cont. Vl. Subst. Trib.", "Lanc. Cont. Vl. IPI"
    # ]), language="text")
    # st.write("Colunas opcionais de **valores** (se presentes, serão exibidas quando houver diferença/zerado):")
    # st.code(" | ".join(["Valor Contábil", "Vl. ICMS", "Vl. ST", "Vl. IPI"]), language="text")

    # Verifica se há arquivo gerado pela aba de extração
    bi_file_source = None
    if "alterdata_bi_file" in st.session_state and Path(st.session_state["alterdata_bi_file"]).exists():
        use_generated = st.checkbox(
            f"✅ Usar arquivo gerado na aba de Extração (Empresa {st.session_state.get('alterdata_bi_company', 'N/A')})",
            value=True,
            key="use_generated_p1"
        )
        if use_generated:
            bi_file_source = st.session_state["alterdata_bi_file"]
            st.info(f"📂 Usando arquivo: {Path(bi_file_source).name}")

    # Upload manual (se não usar arquivo gerado)
    bi_file = None
    if not bi_file_source:
        bi_file = st.file_uploader("📊 Arquivo BI único (.xls/.xlsx)", type=["xlsx", "xls"], key="p1_bi_file")

    bi_all = None
    if bi_file_source:
        # Usa arquivo gerado
        try:
            bi_all = load_bi_strict_multisheet(bi_file_source, "BI")
            if bi_all is not None and not bi_all.empty:
                st.success(f"✅ Arquivo processado com sucesso: {len(bi_all)} registros encontrados")
        except Exception as e:
            st.error(f"Erro ao processar arquivo BI: {e}")
    elif bi_file is not None:
        # Usa arquivo enviado
        try:
            bi_all = load_bi_strict_multisheet(bi_file, "BI")
            if bi_all is not None and not bi_all.empty:
                st.success(f"✅ Arquivo processado com sucesso: {len(bi_all)} registros encontrados")
        except Exception as e:
            st.error(f"Erro ao processar arquivo BI: {e}")

    if not base_map:
        st.error("Base de CFOP não carregada. Informe um caminho válido na sidebar.")
    elif bi_all is None or bi_all.empty:
        st.info("Envie um arquivo de BI para conferir.")
    else:
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
    st.header("Parte 2 — Conferência BI (Entradas/Saídas) × Razão (TXT)")
    # st.write("📋 Envie um único arquivo Excel com as abas: **Resumo**, **Saída** e **Entrada**")
    # st.caption("Os dados úteis serão extraídos das abas 'Saída' e 'Entrada'. A aba 'Resumo' não será utilizada.")

    # Verifica se há arquivo gerado pela aba de extração
    bi_file_source_p2 = None
    if "alterdata_bi_file" in st.session_state and Path(st.session_state["alterdata_bi_file"]).exists():
        use_generated_p2 = st.checkbox(
            f"✅ Usar arquivo gerado na aba de Extração (Empresa {st.session_state.get('alterdata_bi_company', 'N/A')})",
            value=True,
            key="use_generated_p2"
        )
        if use_generated_p2:
            bi_file_source_p2 = st.session_state["alterdata_bi_file"]
            st.info(f"📂 Usando arquivo: {Path(bi_file_source_p2).name}")

    # Upload manual (se não usar arquivo gerado)
    bi_file_p2 = None
    if not bi_file_source_p2:
        bi_file_p2 = st.file_uploader("📊 Arquivo BI único (.xls/.xlsx)", type=["xls","xlsx"], key="bi_file")

    razao_files = st.file_uploader("📚 Razão TXT", type=["txt"], accept_multiple_files=True)

    st.divider()

    # Processar BIs
    bi_parts = []

    # Determina qual fonte de arquivo usar
    bi_file_to_process = bi_file_source_p2 if bi_file_source_p2 else bi_file_p2

    if bi_file_to_process is not None:
        try:
            result_entrada, result_saida = load_bi_multisheet(bi_file_to_process)

            if result_entrada is not None:
                bi_df_ent, cfop_ent = result_entrada
                agg_ent = aggregate_bi_all(bi_df_ent)
                agg_ent["origem"] = "entradas"
                bi_parts.append(agg_ent)
                st.success("✅ Aba 'Entrada' processada com sucesso.")

            if result_saida is not None:
                bi_df_sai, cfop_sai = result_saida
                agg_sai = aggregate_bi_all(bi_df_sai)
                agg_sai["origem"] = "saidas"
                bi_parts.append(agg_sai)
                st.success("✅ Aba 'Saída' processada com sucesso.")

            if result_entrada is None and result_saida is None:
                st.error("Nenhuma aba 'Entrada' ou 'Saída' foi encontrada no arquivo.")
        except Exception as e:
            st.error(f"Erro ao processar arquivo BI: {e}")

    # BI — Soma por Lançamento
    if bi_parts:
        bi_total = (
            pd.concat(bi_parts, ignore_index=True)
              .groupby("lancamento", as_index=False)["valor_bi"].sum()
        )
        with st.expander("📊 BI — Soma por Lançamento", expanded=False):
            st.dataframe(bi_total, use_container_width=True, height=280)
    else:
        bi_total = pd.DataFrame(columns=["lancamento","valor_bi"])
        st.info("Envie ao menos um BI (Entradas, Saídas ou Serviços).")

    # Processar Razões
    razao_servicos = pd.DataFrame()
    try:
        razao_total = consolidate_razao_files(razao_files)
        if not razao_total.empty:
            # Separar serviços prestados
            razao_sem_servicos, razao_servicos = filter_servicos_prestados(razao_total)

            with st.expander("📒 Razão consolidado (todos TXT)", expanded=False):
                st.dataframe(razao_sem_servicos, use_container_width=True, height=240)
        else:
            st.info("Envie ao menos um arquivo TXT de Razão.")
            razao_sem_servicos = razao_total
    except Exception as e:
        st.error(f"Erro processando razões: {e}")
        razao_total = pd.DataFrame(columns=["lancamento","valor_razao","descricao"])
        razao_sem_servicos = razao_total

    st.divider()

    # Comparação (usar razão sem serviços)
    if not bi_total.empty and not razao_sem_servicos.empty:
        st.subheader("✅ Comparação BI × Razão por Lançamento")
        comp = compare_bi_vs_razao(bi_total, razao_sem_servicos)

        metrics = calculate_comparison_metrics(comp, bi_total, razao_sem_servicos)
        display_comparison_kpis(
            metrics["bi_count"], metrics["razao_count"],
            metrics["div_count"], metrics["ok_count"]
        )

        # Verifica se todas as comparações estão OK
        if is_comparison_perfect(metrics):
            show_success_message("Todas as comparações BI × Razão estão perfeitas - sem divergências!")

        # Renomear colunas para exibição
        comp_display = comp.rename(columns={
            "lancamento": "Código de Lançamento",
            "descricao": "Descrição",
            "valor_bi": "Valor BI",
            "valor_razao": "Valor Razão",
            "dif": "Diferença",
            "ok": "Status"
        })
        # Formatar coluna Status
        comp_display["Status"] = comp_display["Status"].apply(lambda x: "OK ✅" if x else "DIVERGÊNCIA ❌")

        styled = format_comparison_table(comp_display)
        st.dataframe(styled, use_container_width=True, height=420)

        # Downloads - Apenas 2 botões para comparação
        create_comparison_download_buttons(comp_display, "Comparação", key_prefix="parte2")

        # Exibir tabela de serviços prestados APÓS o relatório principal
        if not razao_servicos.empty:
            st.divider()
            st.subheader("🔧 Serviços Prestados (TXT)")
            st.info(f"Esses códigos são referentes a serviços prestados e foram removidos do relatório principal: {len(razao_servicos)} registros")
            st.dataframe(razao_servicos, use_container_width=True, height=200)
    else:
        st.info("Para comparar, envie ao menos um BI e ao menos um TXT de Razão.")


# =============================================================================
# TAB 3: Livro de ICMS x Lote Contábil
# =============================================================================
with tab3:
    st.header("Livro de ICMS x Lote Contábil — Livro de Apuração (PDF)")

    cpdf, ctxt = st.columns(2)
    with cpdf:
        pdf_file = st.file_uploader("📄 PDF: Livro de Apuração (ICMS)", type=["pdf"], key="sn_pdf")
        txt_file = st.file_uploader("📚 TXT: Razão", type=["txt"], key="sn_txt")
    with ctxt:
        pdf_file_st = st.file_uploader("📄 PDF: Livro de ICMS ST", type=["pdf"], key="sn_pdf_st")

    # Verifica base CFOP
    if not base_map:
        st.error("Base de CFOP não carregada na sidebar. O mapeamento CFOP→lançamentos depende desse JSON.")

    # Processar PDF ICMS
    try:
        pdf_lanc_tot, log_df, cfop_sem_mapa, comp_map_icms = process_icms_pdf(pdf_file, base_map)
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
        comp_map_icms = {}

    # Processar PDF ICMS ST
    try:
        st_lanc_tot, cfop_st_sem_mapa, comp_map_st = process_icms_st_pdf(pdf_file_st, base_map)
        if cfop_st_sem_mapa:
            st.warning(f"CFOP (ICMS ST) sem mapeamento na base (icms_subst): {', '.join(sorted(set(cfop_st_sem_mapa)))}")
    except Exception as e:
        st.error(f"Erro processando PDF ICMS ST: {e}")
        st_lanc_tot = pd.DataFrame(columns=["lancamento","valor"])
        comp_map_st = {}

    # Processar TXT
    txt_servicos = pd.DataFrame()
    try:
        txt_lanc_tot, txt_desc = parse_txt_lancamento_valor_desc(txt_file)

        # Separar serviços prestados do TXT
        if not txt_lanc_tot.empty:
            txt_sem_servicos, txt_servicos = filter_servicos_prestados_txt(txt_lanc_tot, txt_desc)
        else:
            txt_sem_servicos = txt_lanc_tot
    except Exception as e:
        st.error(f"Erro processando TXT: {e}")
        txt_lanc_tot = pd.DataFrame(columns=["lancamento","valor"])
        txt_desc = pd.DataFrame(columns=["lancamento","descrição"])
        txt_sem_servicos = pd.DataFrame(columns=["lancamento","valor"])

    # Unir composições ICMS + ICMS ST
    comp_map_union = {}
    for lanc, cfops in comp_map_icms.items():
        comp_map_union.setdefault(lanc, set()).update(cfops)
    for lanc, cfops in comp_map_st.items():
        comp_map_union.setdefault(lanc, set()).update(cfops)

    st.divider()
    st.subheader("🔎 Comparação — Livro ICMS & ICMS ST (PDF) × Lote Contábil (TXT)")

    # Comparação final (usar TXT sem serviços)
    comp = compare_simples_nacional(pdf_lanc_tot, st_lanc_tot, txt_sem_servicos, txt_desc, comp_map_union)

    metrics = calculate_simples_nacional_metrics(comp, pdf_lanc_tot, st_lanc_tot, txt_sem_servicos)
    display_simples_nacional_kpis(
        metrics["pdf_lanc_count"], metrics["rz_count"],
        metrics["div_count"], metrics["ok_count"]
    )

    # Verifica se todas as análises estão OK
    if is_simples_nacional_perfect(metrics):
        show_success_message("Todas as análises do Livro de ICMS x Lote Contábil estão perfeitas - sem divergências!")

    # Tabela final
    styled = format_comparison_table(comp)
    st.dataframe(styled, use_container_width=True, height=460, key="sn_comp_icms_icmsst")

    # Downloads - Apenas 2 botões para comparação
    create_comparison_download_buttons(comp, "Comparação", key_prefix="parte3")

    # Exibir tabela de serviços prestados APÓS o relatório principal
    if not txt_servicos.empty:
        st.divider()
        st.subheader("🔧 Serviços Prestados (TXT)")
        st.info(f"Esses códigos são referentes a serviços prestados e foram removidos do relatório principal: {len(txt_servicos)} registros")
        st.dataframe(txt_servicos, use_container_width=True, height=200)


# =============================================================================
# Fim da Aplicação
# =============================================================================