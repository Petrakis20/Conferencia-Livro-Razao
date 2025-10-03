"""
Módulo de componentes de interface do usuário.
Responsável por elementos visuais, KPIs e animações do Streamlit.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Any


# =============================================================================
# Componentes KPI
# =============================================================================
def kpi_card(title: str, value: Any, bg: str = "#ffffff", border: str = "#e5e7eb", fg: str = "#111827") -> None:
    """Cria um cartão KPI estilizado."""
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


def display_analysis_kpis(ok_count: int, diff_count: int, zero_count: int, notfound_count: int) -> None:
    """Exibe KPIs da análise CFOP."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("OK ✅", ok_count, bg="#ECFFF1", border="#C8F3D4", fg="#16A34A")
    with c2:
        kpi_card("Código de lançamento incorreto ❌", diff_count, bg="#FFF1F2", border="#FECDD3", fg="#E11D48")
    with c3:
        kpi_card("Ausência de Lançamento Automático 🟡", zero_count, bg="#FFF1F2", border="#FECDD3", fg="#E11D48")
    with c4:
        kpi_card("⚠️ CFOP não cadastrado", notfound_count, bg="#FFF1F2", border="#FECDD3", fg="#E11D48")


def display_comparison_kpis(bi_count: int, razao_count: int, div_count: int, ok_count: int) -> None:
    """Exibe KPIs da comparação BI x Razão."""
    kc1, kc2, kc3, kc4 = st.columns(4)
    with kc1:
        kpi_card("Lançamentos BI", bi_count, bg="#FFFFFF", border="#E5E7EB", fg="#111827")
    with kc2:
        kpi_card("Lançamentos Razão", razao_count, bg="#F0F7FF", border="#93C5FD", fg="#1D4ED8")
    with kc3:
        kpi_card("Divergências", div_count, bg="#FEE2E2", border="#FCA5A5", fg="#DC2626")
    with kc4:
        kpi_card("OK ✅", ok_count, bg="#DCFCE7", border="#86EFAC", fg="#16A34A")


def display_simples_nacional_kpis(pdf_lanc_count: int, rz_count: int, div_count: int, ok_count: int) -> None:
    """Exibe KPIs do Livro de ICMS x Lote Contábil."""
    kc1, kc2, kc3, kc4 = st.columns(4)
    with kc1:
        kpi_card("Lançamentos (PDF)", pdf_lanc_count, bg="#FFFFFF", border="#E5E7EB", fg="#111827")
    with kc2:
        kpi_card("Lançamentos (TXT)", rz_count, bg="#F0F7FF", border="#93C5FD", fg="#1D4ED8")
    with kc3:
        kpi_card("Divergências", div_count, bg="#FEE2E2", border="#FCA5A5", fg="#DC2626")
    with kc4:
        kpi_card("OK ✅", ok_count, bg="#DCFCE7", border="#86EFAC", fg="#16A34A")


# =============================================================================
# Animações
# =============================================================================
def trigger_fireworks() -> None:
    """Dispara animação de fogos de artifício com explosões de partículas quando todas as análises estão OK."""
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
# Mensagens de Sucesso
# =============================================================================
def show_success_message(message: str) -> None:
    """Exibe mensagem de sucesso e dispara fogos de artifício."""
    st.success(f"🎉 **PARABÉNS!** {message}")
    trigger_fireworks()


# =============================================================================
# Filtros e Controles
# =============================================================================
def create_status_filters(result_df: pd.DataFrame) -> tuple:
    """Cria filtros de status e origem."""
    status_filter = st.multiselect(
        "Filtrar por Status",
        options=sorted(result_df["Status"].dropna().unique().tolist())
    )

    origem_filter = []
    if "origem" in result_df.columns:
        origem_filter = st.multiselect(
            "Filtrar por Origem",
            options=sorted(result_df["origem"].dropna().unique().tolist())
        )

    return status_filter, origem_filter


def apply_filters(df: pd.DataFrame, status_filter: list, origem_filter: list) -> pd.DataFrame:
    """Aplica filtros ao DataFrame."""
    filtered = df.copy()
    if status_filter:
        filtered = filtered[filtered["Status"].isin(status_filter)]
    if origem_filter and "origem" in df.columns:
        filtered = filtered[filtered["origem"].isin(origem_filter)]
    return filtered


# =============================================================================
# Funções de Download
# =============================================================================
def create_download_buttons(df: pd.DataFrame, base_filename: str) -> None:
    """Cria botões de download para CSV e Excel."""
    col1, col2 = st.columns(2)

    with col1:
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            f"Baixar {base_filename} (.csv)",
            data=csv_bytes,
            file_name=f"{base_filename.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )

    with col2:
        excel_bytes, excel_name, excel_mime = make_excel_bytes(df, base_filename)
        st.download_button(
            f"Baixar {base_filename} (Excel)",
            data=excel_bytes,
            file_name=excel_name,
            mime=excel_mime
        )


def make_excel_bytes(df: pd.DataFrame, sheet_name: str = "Relatorio") -> tuple:
    """Gera bytes do Excel para download."""
    import io
    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlwt") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        return buf.getvalue(), f"{sheet_name.lower().replace(' ','_')}.xls", "application/vnd.ms-excel"
    except Exception:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        return (buf.getvalue(), f"{sheet_name.lower().replace(' ','_')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def make_pdf_bytes(df: pd.DataFrame, title: str = "Relatório") -> bytes:
    """Gera bytes do PDF para download."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import io

    buf = io.BytesIO()
    # Ajustar margens para caber mais conteúdo
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        topMargin=0.8*cm,
        bottomMargin=0.8*cm,
        leftMargin=0.5*cm,
        rightMargin=0.5*cm
    )
    elements = []

    # Preparar dados da tabela - formatar números
    df_formatted = df.copy()

    # Colunas numéricas que precisam de formatação (Parte 2 e Parte 3)
    numeric_cols = ["Livro ICMS", "Livro ICMS ST", "Lote Contábil", "Diferença",
                    "valor_bi", "valor_razao", "dif"]
    for col in numeric_cols:
        if col in df_formatted.columns:
            df_formatted[col] = df_formatted[col].apply(
                lambda x: f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                if pd.notna(x) and x != "" else "0,00"
            )

    # Substituir valores NaN por string vazia
    df_formatted = df_formatted.fillna("")

    # Calcular largura disponível
    available_width = landscape(A4)[0] - 1*cm

    # Definir larguras das colunas em cm (mais controle)
    col_widths_mapping = {
        # Parte 3 (Livro ICMS)
        "CFOP": 4.5*cm,
        "Lançamento": 2.2*cm,
        "Descrição": 6*cm,
        "Livro ICMS": 2.5*cm,
        "Livro ICMS ST": 2.5*cm,
        "Lote Contábil": 2.5*cm,
        "Diferença": 2.2*cm,
        "Status": 2*cm,
        # Parte 2 (BI x Razão)
        "Código de Lançamento": 2.5*cm,
        "Descrição": 7*cm,
        "Valor BI": 3*cm,
        "Valor Razão": 3*cm,
        "Diferença": 3*cm,
        "Status": 2*cm
    }

    col_widths = [col_widths_mapping.get(col, 2*cm) for col in df_formatted.columns]

    # Estilos para Paragraph
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=7,
        alignment=TA_CENTER,
        textColor=colors.whitesmoke,
        fontName='Helvetica-Bold',
        leading=9
    )

    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=6.5,
        alignment=TA_LEFT,
        fontName='Helvetica',
        leading=8
    )

    cell_style_right = ParagraphStyle(
        'CellStyleRight',
        parent=styles['Normal'],
        fontSize=6.5,
        alignment=TA_RIGHT,
        fontName='Helvetica',
        leading=8
    )

    # Construir dados da tabela com Paragraphs para quebra de linha
    data = []

    # Cabeçalho
    header_row = [Paragraph(str(col), header_style) for col in df_formatted.columns]
    data.append(header_row)

    # Colunas numéricas (índices podem variar, vamos identificar por nome)
    numeric_col_indices = [i for i, col in enumerate(df_formatted.columns)
                          if col in numeric_cols]

    # Estilos para células OK (verde) e com erro (vermelho)
    cell_style_green = ParagraphStyle(
        'CellStyleGreen',
        parent=styles['Normal'],
        fontSize=6.5,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
        leading=8,
        textColor=colors.HexColor('#16A34A')  # Verde
    )

    cell_style_red = ParagraphStyle(
        'CellStyleRed',
        parent=styles['Normal'],
        fontSize=6.5,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
        leading=8,
        textColor=colors.HexColor('#DC2626')  # Vermelho
    )

    cell_style_right_green = ParagraphStyle(
        'CellStyleRightGreen',
        parent=styles['Normal'],
        fontSize=6.5,
        alignment=TA_RIGHT,
        fontName='Helvetica-Bold',
        leading=8,
        textColor=colors.HexColor('#16A34A')  # Verde
    )

    cell_style_right_red = ParagraphStyle(
        'CellStyleRightRed',
        parent=styles['Normal'],
        fontSize=6.5,
        alignment=TA_RIGHT,
        fontName='Helvetica-Bold',
        leading=8,
        textColor=colors.HexColor('#DC2626')  # Vermelho
    )

    # Identificar índices das colunas de Status e Diferença/dif/ok
    status_col_idx = None
    diff_col_idx = None
    ok_col_idx = None

    for i, col in enumerate(df_formatted.columns):
        if col == "Status":
            status_col_idx = i
        elif col in ["Diferença", "dif"]:
            diff_col_idx = i
        elif col == "ok":
            ok_col_idx = i

    # Corpo
    for _, row in df_formatted.iterrows():
        row_data = []

        # Determinar se a linha está OK ou tem erro
        is_ok = False
        if status_col_idx is not None:
            # Parte 3: Verificar coluna Status
            is_ok = str(row.iloc[status_col_idx]).startswith("OK")
        elif ok_col_idx is not None:
            # Parte 2: Verificar coluna ok
            is_ok = str(row.iloc[ok_col_idx]).lower() in ["true", "1", "yes"]

        for i, (col_name, value) in enumerate(zip(df_formatted.columns, row)):
            # Determinar o estilo baseado na coluna e no status
            should_color = (i == status_col_idx or i == diff_col_idx or i == ok_col_idx)

            if should_color:
                # Aplicar cor verde ou vermelha
                if is_ok:
                    style = cell_style_right_green if i in numeric_col_indices else cell_style_green
                else:
                    style = cell_style_right_red if i in numeric_col_indices else cell_style_red
            else:
                # Estilo normal
                style = cell_style_right if i in numeric_col_indices else cell_style

            row_data.append(Paragraph(str(value), style))

        data.append(row_data)

    # Criar tabela
    table = Table(data, colWidths=col_widths, repeatRows=1)

    # Estilo da tabela
    table.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),

        # Corpo da tabela
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ('LEFTPADDING', (0, 1), (-1, -1), 3),
        ('RIGHTPADDING', (0, 1), (-1, -1), 3),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

        # Linhas alternadas
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
    ]))

    elements.append(table)
    doc.build(elements)

    return buf.getvalue()


def create_comparison_download_buttons(df: pd.DataFrame, base_filename: str = "Comparação", key_prefix: str = "") -> None:
    """Cria apenas 2 botões de download: Excel e PDF para comparação."""
    col1, col2 = st.columns(2)

    with col1:
        excel_bytes, excel_name, excel_mime = make_excel_bytes(df, base_filename)
        st.download_button(
            "Baixar comparação (Excel)",
            data=excel_bytes,
            file_name=excel_name,
            mime=excel_mime,
            key=f"{key_prefix}_excel_download"
        )

    with col2:
        try:
            pdf_bytes = make_pdf_bytes(df, base_filename)
            st.download_button(
                "Baixar comparação (PDF)",
                data=pdf_bytes,
                file_name=f"{base_filename.lower().replace(' ', '_')}.pdf",
                mime="application/pdf",
                key=f"{key_prefix}_pdf_download"
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}. Instale reportlab: pip install reportlab")


# =============================================================================
# Formatação de Tabelas
# =============================================================================
def format_comparison_table(comp: pd.DataFrame) -> pd.DataFrame:
    """Formata tabela de comparação com cores."""
    ok_mask = comp["Status"].astype(str).str.startswith("OK") if "Status" in comp.columns else pd.Series([False] * len(comp))

    styled = comp.style

    # Formata colunas numéricas se existirem
    numeric_cols = ["valor_bi", "valor_razao", "dif", "Livro ICMS", "Livro ICMS ST", "Lote Contábil", "Diferença"]
    format_dict = {}
    for col in numeric_cols:
        if col in comp.columns:
            format_dict[col] = "{:,.2f}"

    if format_dict:
        styled = styled.format(format_dict)

    # Aplica cores - verde quando diferença é 0, vermelho quando diferente de 0
    diff_cols = ["dif", "Diferença"]
    for col in diff_cols:
        if col in comp.columns:
            # Verifica se a diferença é 0 (considerando valores numéricos)
            diff_zero = comp[col].fillna(0).abs() < 0.01  # Tolerância para erros de ponto flutuante
            styled = styled.apply(
                lambda s: pd.Series(np.where(diff_zero, "color:green", "color:red"), index=comp.index),
                subset=[col]
            )

    return styled